"""
Syntactic Retriever — BM25 keyword-based search (FR-04.1).

Uses rank_bm25 over document chunks stored in SQLite.
"""

from __future__ import annotations

import logging
import re

from rank_bm25 import BM25Okapi
from sqlalchemy import select

from ..database import DocumentRecord, SessionLocal
from .strategy import RetrievalStrategy, RetrievedChunk

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"\w+", text.lower())


class SyntacticRetriever(RetrievalStrategy):
    """BM25-based keyword retrieval over document content."""

    def __init__(self):
        self._corpus_tokens: list[list[str]] = []
        self._chunk_meta: list[dict] = []
        self._bm25: BM25Okapi | None = None
        self._doc_count = 0

    def _build_index(self):
        """Rebuild BM25 index from all indexed documents."""
        db = SessionLocal()
        try:
            docs = db.execute(
                select(DocumentRecord).where(DocumentRecord.is_indexed == True)
            ).scalars().all()

            self._corpus_tokens = []
            self._chunk_meta = []

            for doc in docs:
                content = doc.content or ""
                # Split into paragraph-level chunks for BM25
                paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 20]
                if not paragraphs:
                    paragraphs = [content[:1000]] if content.strip() else []

                for i, para in enumerate(paragraphs):
                    tokens = _tokenize(para)
                    if tokens:
                        self._corpus_tokens.append(tokens)
                        self._chunk_meta.append({
                            "doc_id": doc.id,
                            "title": doc.title or doc.original_name,
                            "filename": doc.original_name,
                            "content": para,
                            "chunk_index": i,
                        })

            if self._corpus_tokens:
                self._bm25 = BM25Okapi(self._corpus_tokens)
            else:
                self._bm25 = None
            self._doc_count = len(docs)
            logger.info(f"BM25 index built: {len(self._corpus_tokens)} chunks from {len(docs)} docs")
        finally:
            db.close()

    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievedChunk]:
        # Rebuild index (in production, this would be event-driven)
        self._build_index()

        if not self._bm25 or not self._corpus_tokens:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)

        # Get top-k indices, sorted by score descending
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

        # Relative score threshold: keep results scoring at least 50% of the
        # top score.  With a small corpus, common words ("policy",
        # "employees") produce low-but-positive BM25 scores across many
        # documents.  A 50% cutoff retains genuinely relevant docs while
        # filtering noise.
        top_score = scores[ranked_indices[0]] if ranked_indices else 0
        min_threshold = top_score * 0.5

        results = []
        seen_docs = set()
        for idx in ranked_indices:
            if scores[idx] <= 0 or scores[idx] < min_threshold:
                continue
            meta = self._chunk_meta[idx]
            # Deduplicate by doc_id (take best chunk per doc)
            if meta["doc_id"] in seen_docs:
                continue
            seen_docs.add(meta["doc_id"])
            results.append(RetrievedChunk(
                doc_id=meta["doc_id"],
                title=meta["title"],
                filename=meta["filename"],
                content=meta["content"][:500],
                score=float(scores[idx]),
                strategy="syntactic",
                chunk_index=meta["chunk_index"],
            ))
            if len(results) >= top_k:
                break
        return results

    def get_name(self) -> str:
        return "syntactic"
