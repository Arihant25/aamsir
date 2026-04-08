"""
Retrieval Strategy Interface — Strategy Pattern (ADR-003).

All retrieval implementations conform to this interface so the
Orchestrator can invoke them polymorphically.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with metadata."""
    doc_id: int
    title: str
    filename: str
    content: str
    score: float = 0.0
    strategy: str = ""
    chunk_index: int = 0


class RetrievalStrategy(ABC):
    """Abstract base for all retrieval strategies."""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievedChunk]:
        """Return ranked chunks relevant to the query."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return human-readable strategy name."""
        ...

    def is_available(self) -> bool:
        """Check if this strategy is ready to use."""
        return True
