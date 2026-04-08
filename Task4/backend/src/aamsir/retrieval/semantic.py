"""
Semantic Retriever — Vector similarity with Chain of Responsibility (FR-04.2).

Uses ChromaDB for vector storage and sentence-transformers for query encoding.
Implements a cascading filter: TitleMatch -> SummarySim -> ContentSim.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod

from sqlalchemy import func, select

from ..database import DocumentRecord, SessionLocal
from ..ingestion.pipeline import get_chroma_collection, get_embedding_model
from .strategy import RetrievalStrategy, RetrievedChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chain of Responsibility — Semantic Filter Handlers
# ---------------------------------------------------------------------------
class SemanticFilterHandler(ABC):
    """Abstract handler in the Chain of Responsibility."""

    def __init__(self):
        self._next: SemanticFilterHandler | None = None

    def set_next(self, handler: SemanticFilterHandler) -> SemanticFilterHandler:
        self._next = handler
        return handler

    def filter(self, candidates: list[dict], query: str, top_k: int) -> list[dict]:
        filtered = self._do_filter(candidates, query, top_k)
        if self._next:
            return self._next.filter(filtered, query, top_k)
        return filtered

    @abstractmethod
    def _do_filter(self, candidates: list[dict], query: str, top_k: int) -> list[dict]:
        ...


class TitleMatchHandler(SemanticFilterHandler):
    """Stage 1: Cheap lexical overlap between query tokens and document titles."""

    def __init__(self, min_overlap: float = 0.0):
        super().__init__()
        self.min_overlap = min_overlap

    def _do_filter(self, candidates: list[dict], query: str, top_k: int) -> list[dict]:
        query_tokens = set(re.findall(r"\w+", query.lower()))
        # Remove stopwords for better matching
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "do", "does",
                      "what", "how", "who", "for", "to", "of", "in", "on", "and",
                      "or", "it", "i", "my", "your", "this", "that", "with"}
        query_tokens -= stopwords
        if not query_tokens:
            return candidates

        scored = []
        for c in candidates:
            title_tokens = set(re.findall(r"\w+", c.get("title", "").lower()))
            title_tokens -= stopwords
            if not title_tokens:
                overlap = 0.0
            else:
                overlap = len(query_tokens & title_tokens) / len(query_tokens)
            scored.append((overlap, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Keep candidates with any title overlap, plus top_k as safety net
        with_overlap = [(s, c) for s, c in scored if s > 0]
        if with_overlap:
            result = [c for _, c in with_overlap]
        else:
            # No title overlap at all — fall through to next handler
            result = [c for _, c in scored[:max(top_k * 2, 5)]]
        logger.info(f"TitleMatch: {len(candidates)} -> {len(result)}")
        return result


class SummarySimHandler(SemanticFilterHandler):
    """Stage 2: Cosine similarity on summary embeddings."""

    def _do_filter(self, candidates: list[dict], query: str, top_k: int) -> list[dict]:
        if not candidates:
            return candidates

        model = get_embedding_model()
        query_emb = model.encode([query])[0]

        scored = []
        for c in candidates:
            summary = c.get("summary", "")
            if not summary.strip():
                summary = c.get("content", "")[:200]
            summary_emb = model.encode([summary])[0]
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_emb, summary_emb))
            norm_q = sum(a * a for a in query_emb) ** 0.5
            norm_s = sum(a * a for a in summary_emb) ** 0.5
            sim = dot / (norm_q * norm_s) if norm_q and norm_s else 0.0
            c["summary_score"] = sim
            scored.append((sim, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        # Keep top_k candidates, or more if scores are close
        cutoff = min(max(top_k, 3), len(scored))
        result = [c for _, c in scored[:cutoff]]
        logger.info(f"SummarySim: {len(candidates)} -> {len(result)}")
        return result


class ContentSimHandler(SemanticFilterHandler):
    """Stage 3: Full vector search via ChromaDB on the filtered candidate set."""

    def _do_filter(self, candidates: list[dict], query: str, top_k: int) -> list[dict]:
        if not candidates:
            return candidates

        # Use ChromaDB to search only within candidate doc_ids
        collection = get_chroma_collection()
        doc_ids = list({str(c["doc_id"]) for c in candidates})

        model = get_embedding_model()
        query_emb = model.encode([query]).tolist()

        try:
            results = collection.query(
                query_embeddings=query_emb,
                n_results=min(top_k * 2, 20),
                where={"doc_id": {"$in": [int(d) for d in doc_ids]}},
            )
        except Exception:
            # Fallback: query without filter
            results = collection.query(
                query_embeddings=query_emb,
                n_results=min(top_k, 10),
            )

        if not results["ids"] or not results["ids"][0]:
            return candidates[:top_k]

        # Build result list with scores
        final = []
        seen_docs = set()
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc_id = meta.get("doc_id", 0)
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)
            distance = results["distances"][0][i] if results["distances"] else 1.0
            score = 1.0 - distance  # ChromaDB cosine distance -> similarity
            content = results["documents"][0][i] if results["documents"] else ""
            final.append({
                "doc_id": doc_id,
                "title": meta.get("title", ""),
                "filename": meta.get("filename", ""),
                "content": content,
                "score": score,
                "chunk_index": meta.get("chunk_index", 0),
            })

        logger.info(f"ContentSim: {len(candidates)} -> {len(final)}")
        return final[:top_k]


# ---------------------------------------------------------------------------
# Semantic Retriever
# ---------------------------------------------------------------------------
class SemanticRetriever(RetrievalStrategy):
    """Vector-similarity retrieval with Chain of Responsibility filtering."""

    def __init__(self):
        # Build chain: TitleMatch -> SummarySim -> ContentSim
        self._title_handler = TitleMatchHandler()
        self._summary_handler = SummarySimHandler()
        self._content_handler = ContentSimHandler()
        self._title_handler.set_next(self._summary_handler)
        self._summary_handler.set_next(self._content_handler)

    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievedChunk]:
        # For small corpora (< 100 docs), skip the Chain of Responsibility
        # filter and query ChromaDB directly — the cascading filter is
        # designed for 10K+ document scale to cut latency.  At small scale
        # it over-filters and mis-ranks because title/summary heuristics
        # lack statistical power.
        db = SessionLocal()
        try:
            doc_count = db.execute(
                select(func.count(DocumentRecord.id)).where(
                    DocumentRecord.is_indexed == True
                )
            ).scalar() or 0
        finally:
            db.close()

        if doc_count < 100:
            return self._direct_vector_search(query, top_k)

        # Large corpus: use the Chain of Responsibility filter pipeline
        return self._chain_filtered_search(query, top_k)

    def _direct_vector_search(
        self, query: str, top_k: int
    ) -> list[RetrievedChunk]:
        """Query ChromaDB directly for small corpora."""
        model = get_embedding_model()
        query_emb = model.encode([query]).tolist()
        collection = get_chroma_collection()

        results = collection.query(
            query_embeddings=query_emb,
            n_results=min(top_k * 3, 30),
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        chunks: list[RetrievedChunk] = []
        seen_docs: set[int] = set()
        top_sim = None
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc_id = meta.get("doc_id", 0)
            if doc_id in seen_docs:
                continue
            seen_docs.add(doc_id)
            distance = (
                results["distances"][0][i] if results["distances"] else 1.0
            )
            score = 1.0 - distance  # cosine distance -> similarity

            if top_sim is None:
                top_sim = score
            # Drop docs whose similarity is less than 60% of the best
            if score < top_sim * 0.6:
                continue

            content = (
                results["documents"][0][i] if results["documents"] else ""
            )
            chunks.append(RetrievedChunk(
                doc_id=doc_id,
                title=meta.get("title", ""),
                filename=meta.get("filename", ""),
                content=content[:500],
                score=score,
                strategy="semantic",
                chunk_index=meta.get("chunk_index", 0),
            ))
            if len(chunks) >= top_k:
                break
        return chunks

    def _chain_filtered_search(
        self, query: str, top_k: int
    ) -> list[RetrievedChunk]:
        """Use Chain of Responsibility for large corpora (10K+ docs)."""
        db = SessionLocal()
        try:
            docs = db.execute(
                select(DocumentRecord).where(
                    DocumentRecord.is_indexed == True
                )
            ).scalars().all()

            candidates = [
                {
                    "doc_id": d.id,
                    "title": d.title or d.original_name,
                    "filename": d.original_name,
                    "content": (d.content or "")[:500],
                    "summary": d.summary or "",
                }
                for d in docs
            ]
        finally:
            db.close()

        if not candidates:
            return []

        filtered = self._title_handler.filter(candidates, query, top_k)

        return [
            RetrievedChunk(
                doc_id=c["doc_id"],
                title=c["title"],
                filename=c["filename"],
                content=c["content"][:500],
                score=c.get("score", c.get("summary_score", 0.0)),
                strategy="semantic",
                chunk_index=c.get("chunk_index", 0),
            )
            for c in filtered[:top_k]
        ]

    def get_name(self) -> str:
        return "semantic"
