"""
Orchestrator — Microkernel Host (ADR-001).

Coordinates retrieval strategies, aggregates results, and generates
the final answer. Implements fault isolation (Tactic 3).
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import DocumentRecord, QueryLog, SessionLocal
from .strategy import RetrievalStrategy, RetrievedChunk

logger = logging.getLogger(__name__)


class ContextAggregator:
    """Merges and deduplicates results from multiple retrieval strategies."""

    @staticmethod
    def merge(strategy_results: dict[str, list[RetrievedChunk]], top_k: int = 10) -> list[RetrievedChunk]:
        """Merge results using Reciprocal Rank Fusion (RRF)."""
        doc_scores: dict[int, float] = {}
        doc_best: dict[int, RetrievedChunk] = {}
        k = 60  # RRF constant

        for strategy_name, chunks in strategy_results.items():
            for rank, chunk in enumerate(chunks):
                rrf_score = 1.0 / (k + rank + 1)
                doc_scores[chunk.doc_id] = doc_scores.get(chunk.doc_id, 0.0) + rrf_score

                # Keep the chunk with the highest individual score per doc
                if chunk.doc_id not in doc_best or chunk.score > doc_best[chunk.doc_id].score:
                    doc_best[chunk.doc_id] = chunk

        # Sort by aggregated RRF score
        ranked_ids = sorted(doc_scores, key=lambda d: doc_scores[d], reverse=True)[:top_k]

        results = []
        for doc_id in ranked_ids:
            chunk = doc_best[doc_id]
            chunk.score = doc_scores[doc_id]
            # Combine strategy names
            strategies = [
                s for s, chunks in strategy_results.items()
                if any(c.doc_id == doc_id for c in chunks)
            ]
            chunk.strategy = "+".join(strategies)
            results.append(chunk)

        return results


class Orchestrator:
    """Microkernel host that manages retrieval plugins and orchestrates queries."""

    def __init__(self):
        self._strategies: dict[str, RetrievalStrategy] = {}
        self._enabled_strategies: set[str] = {"syntactic", "semantic"}
        self._aggregator = ContextAggregator()

    def rewrite_query(self, query: str, history: list[dict[str, str]]) -> str:
        """Rewrite a conversational follow-up into a standalone search query.

        If there is no history the original query is returned unchanged.
        """
        if not history:
            return query

        history_text = "\n".join(
            f"{msg['role'].title()}: {msg['content']}"
            for msg in history[-6:]
        )

        prompt = (
            "Given the conversation history and a follow-up question, "
            "rewrite the follow-up question as a standalone search query that "
            "captures the full intent. Output ONLY the rewritten query, nothing else.\n\n"
            f"Conversation History:\n{history_text}\n\n"
            f"Follow-up Question: {query}\n\n"
            "Standalone Query:"
        )

        try:
            import ollama
            from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL
            client = ollama.Client(host=OLLAMA_BASE_URL)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            rewritten = response["message"]["content"].strip()
            logger.info(f"Query rewritten: '{query}' → '{rewritten}'")
            return rewritten if rewritten else query
        except Exception as e:
            logger.warning(f"Query rewrite failed ({e}), using original query")
            return query

    def register(self, strategy: RetrievalStrategy):
        """Register a retrieval plugin."""
        self._strategies[strategy.get_name()] = strategy
        logger.info(f"Registered strategy: {strategy.get_name()}")

    def set_enabled(self, strategy_names: list[str]):
        """Set which strategies are enabled."""
        self._enabled_strategies = set(strategy_names)

    def get_enabled(self) -> list[str]:
        return list(self._enabled_strategies)

    def get_available(self) -> list[str]:
        return [
            name for name, s in self._strategies.items()
            if s.is_available()
        ]

    def query(
        self,
        query_text: str,
        strategies: list[str] | None = None,
        top_k: int = 10,
    ) -> tuple[list[RetrievedChunk], dict[str, list[RetrievedChunk]], float]:
        """Execute query across enabled strategies with fault isolation.

        Returns (merged_results, per_strategy_results, elapsed_ms).
        """
        start = time.time()
        active = strategies or list(self._enabled_strategies)
        strategy_results: dict[str, list[RetrievedChunk]] = {}

        for name in active:
            strategy = self._strategies.get(name)
            if not strategy:
                logger.warning(f"Strategy '{name}' not registered, skipping")
                continue
            if not strategy.is_available():
                logger.warning(f"Strategy '{name}' not available, skipping")
                continue

            # Fault isolation: wrap each plugin in exception boundary (Tactic 3)
            try:
                results = strategy.retrieve(query_text, top_k)
                strategy_results[name] = results
                logger.info(f"Strategy '{name}' returned {len(results)} results")
            except Exception as e:
                logger.error(f"Strategy '{name}' failed: {e}", exc_info=True)
                strategy_results[name] = []

        merged = self._aggregator.merge(strategy_results, top_k)
        elapsed_ms = (time.time() - start) * 1000

        # Log query
        try:
            db = SessionLocal()
            log = QueryLog(
                query=query_text,
                strategies_used=",".join(active),
                response_time_ms=elapsed_ms,
                result_count=len(merged),
            )
            db.add(log)
            db.commit()
            db.close()
        except Exception:
            pass

        return merged, strategy_results, elapsed_ms

    def _build_enriched_context(self, chunks: list[RetrievedChunk]) -> list[tuple[RetrievedChunk, str]]:
        """Filter to relevant chunks and enrich with full DB content."""
        top_score = chunks[0].score if chunks else 0
        relevant = [c for c in chunks if c.score >= top_score * 0.7] or chunks[:1]

        enriched = []
        try:
            db = SessionLocal()
            for c in relevant:
                doc = db.query(DocumentRecord).get(c.doc_id)
                text = doc.content[:2000] if doc and doc.content else c.content
                enriched.append((c, text))
            db.close()
        except Exception:
            enriched = [(c, c.content) for c in relevant]

        return enriched

    def _build_prompt(
        self,
        query: str,
        enriched: list[tuple[RetrievedChunk, str]],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        context = "\n\n".join(
            f"[Source {c.doc_id}: {c.title}]\n{text}"
            for c, text in enriched
        )

        history_section = ""
        if history:
            history_text = "\n".join(
                f"{msg['role'].title()}: {msg['content']}"
                for msg in history[-6:]
            )
            history_section = f"\nConversation History:\n{history_text}\n"

        return (
            f"Answer the question using ONLY the source documents below. "
            f"Do not use information that is not in the sources. "
            f"When citing a source, use exactly this format: [[doc:ID|Title]] where ID is the source number. "
            f"For example: [[doc:3|Employee Leave Policy]]."
            f"{history_section}\n\n"
            f"Question: {query}\n\n"
            f"Source Documents:\n{context}\n\nAnswer:"
        )

    def generate_answer(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a synthesized answer from retrieved chunks."""
        if not chunks:
            return "No relevant documents were found for your query. Please try rephrasing or uploading more documents."

        enriched = self._build_enriched_context(chunks)

        try:
            import ollama
            from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL
            client = ollama.Client(host=OLLAMA_BASE_URL)
            prompt = self._build_prompt(query, enriched, history)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return response["message"]["content"]

        except Exception:
            top_chunk, top_text = enriched[0]
            parts = [f"From **[[doc:{top_chunk.doc_id}|{top_chunk.title}]]**:\n\n{top_text}"]
            if len(enriched) > 1:
                others = ", ".join(f"[[doc:{c.doc_id}|{c.title}]]" for c, _ in enriched[1:])
                parts.append(f"\nAlso see: {others}")
            return "\n".join(parts)

    def generate_answer_stream(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        history: list[dict[str, str]] | None = None,
    ):
        """Yield answer tokens one at a time (generator).

        Falls back to yielding the full answer as a single token if streaming
        is unavailable (e.g. Ollama not running).
        """
        if not chunks:
            yield "No relevant documents were found for your query. Please try rephrasing or uploading more documents."
            return

        enriched = self._build_enriched_context(chunks)

        try:
            import ollama
            from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL
            client = ollama.Client(host=OLLAMA_BASE_URL)
            prompt = self._build_prompt(query, enriched, history)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in response:
                token = chunk["message"]["content"]
                if token:
                    yield token

        except Exception:
            top_chunk, top_text = enriched[0]
            yield f"From **[[doc:{top_chunk.doc_id}|{top_chunk.title}]]**:\n\n{top_text}"
            if len(enriched) > 1:
                others = ", ".join(f"[[doc:{c.doc_id}|{c.title}]]" for c, _ in enriched[1:])
                yield f"\nAlso see: {others}"
