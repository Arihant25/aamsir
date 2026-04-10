"""Pydantic models for API request/response schemas.

These models define the JSON contract between the Next.js frontend and the
FastAPI backend.  FastAPI uses them for automatic request validation,
serialization, and OpenAPI documentation.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ── Request Models ──────────────────────────────────────────────────────────


class HistoryMessage(BaseModel):
    """A single message in the conversation history."""

    role: str  # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    """Payload for ``POST /api/query``."""

    query: str
    strategies: list[str] = ["syntactic", "semantic"]
    top_k: int = 10
    history: list[HistoryMessage] = []


class FeedbackRequest(BaseModel):
    """Payload for ``POST /api/feedback``."""

    query: str
    answer: str
    rating: str  # "helpful" | "not_helpful"
    strategy_used: str = ""


class ConfigUpdate(BaseModel):
    """Payload for ``PUT /api/config``."""

    enabled_strategies: list[str] | None = None
    embedding_model: str | None = None
    bm25_top_k: int | None = None
    semantic_top_k: int | None = None


# ── Response Models ─────────────────────────────────────────────────────────


class SourceDocument(BaseModel):
    """A single source citation returned alongside a query answer."""

    doc_id: int
    title: str
    filename: str
    snippet: str
    score: float = 0.0
    strategy: str = ""


class QueryResponse(BaseModel):
    """Complete response for a user query, including answer and sources."""

    answer: str
    sources: list[SourceDocument]
    strategies_used: list[str]
    retrieval_time_ms: float
    generation_time_ms: float
    query: str


class DocumentInfo(BaseModel):
    """Metadata for an ingested document."""

    id: int
    filename: str
    original_name: str
    title: str
    summary: str
    file_type: str
    chunk_count: int
    uploaded_at: datetime
    is_indexed: bool

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Response after a successful document upload and ingestion."""

    message: str
    document: DocumentInfo


class ConfigResponse(BaseModel):
    """Current system configuration snapshot."""

    enabled_strategies: list[str]
    available_strategies: list[str]
    embedding_model: str
    bm25_top_k: int
    semantic_top_k: int


class StatsResponse(BaseModel):
    """Aggregate system analytics and usage statistics."""

    total_documents: int
    total_queries: int
    total_feedback: int
    avg_response_time_ms: float
    helpful_count: int
    not_helpful_count: int
