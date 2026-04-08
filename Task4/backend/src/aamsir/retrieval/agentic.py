"""
Agentic Retriever — Tool-use based retrieval with SLM (FR-04.3).

Uses Ollama (local LLM) to reason about queries and search documents.
Wrapped in a CachingAgenticProxy for performance (Tactic 1).

Falls back gracefully if Ollama is not available.
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict

from sqlalchemy import select

from ..database import DocumentRecord, SessionLocal
from .strategy import RetrievalStrategy, RetrievedChunk

logger = logging.getLogger(__name__)


class AgenticRetriever(RetrievalStrategy):
    """SLM-powered retrieval using Ollama for reasoning.

    The agentic retriever asks an LLM to analyze the query, identify
    key concepts, and determine which documents are most relevant
    by reasoning about document summaries.
    """

    def __init__(self, model: str = "llama3.2:1b", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import ollama
            client = ollama.Client(host=self._base_url)
            client.list()
            self._available = True
        except Exception:
            self._available = False
            logger.warning("Ollama not available — agentic retrieval disabled")
        return self._available

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not self.is_available():
            return []

        import ollama
        client = ollama.Client(host=self._base_url)

        db = SessionLocal()
        try:
            docs = db.execute(
                select(DocumentRecord).where(DocumentRecord.is_indexed == True)
            ).scalars().all()

            if not docs:
                return []

            # Build a document catalog for the LLM
            catalog = "\n".join(
                f"[DOC {d.id}] Title: {d.title} | Summary: {(d.summary or '')[:150]}"
                for d in docs
            )

            prompt = f"""You are a document retrieval assistant. Given a user query and a catalog of documents, identify the most relevant documents.

User Query: {query}

Document Catalog:
{catalog}

Return ONLY a comma-separated list of document IDs (numbers) that are most relevant, ordered by relevance. Return at most {top_k} IDs.
Example: 1,3,7"""

            response = client.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse document IDs from response
            response_text = response["message"]["content"]
            import re
            doc_ids = [int(x) for x in re.findall(r"\d+", response_text)][:top_k]

            doc_map = {d.id: d for d in docs}
            results = []
            for rank, did in enumerate(doc_ids):
                if did in doc_map:
                    d = doc_map[did]
                    results.append(RetrievedChunk(
                        doc_id=d.id,
                        title=d.title or d.original_name,
                        filename=d.original_name,
                        content=(d.content or "")[:500],
                        score=1.0 - (rank * 0.1),
                        strategy="agentic",
                    ))
            return results

        except Exception as e:
            logger.error(f"Agentic retrieval failed: {e}")
            return []
        finally:
            db.close()

    def get_name(self) -> str:
        return "agentic"


class CachingAgenticProxy(RetrievalStrategy):
    """Caching Proxy wrapping the AgenticRetriever (Tactic 1).

    LRU cache keyed on normalized query string. Cache hits return
    in <1ms instead of the 5-30s agentic retrieval time.
    """

    def __init__(self, delegate: AgenticRetriever, max_cache_size: int = 128):
        self._delegate = delegate
        self._cache: OrderedDict[str, list[RetrievedChunk]] = OrderedDict()
        self._max_size = max_cache_size

    def _cache_key(self, query: str) -> str:
        normalized = " ".join(query.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        key = self._cache_key(query)

        if key in self._cache:
            logger.info(f"Agentic cache HIT for query: {query[:50]}...")
            self._cache.move_to_end(key)
            return self._cache[key]

        results = self._delegate.retrieve(query, top_k)

        self._cache[key] = results
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

        return results

    def is_available(self) -> bool:
        return self._delegate.is_available()

    def get_name(self) -> str:
        return "agentic"
