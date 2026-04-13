"""FastAPI routes — REST API layer implementing the Facade pattern.

This module is the single entry point for all external HTTP interactions.
It hides the complexity of the retrieval engine, ingestion pipeline, and
persistence layers behind a clean set of JSON endpoints.

Endpoints:
    GET  /api/health             — Health check and strategy availability
    POST /api/query              — Submit a natural-language query
    POST /api/documents/upload   — Upload and ingest a document
    GET  /api/documents          — List all ingested documents
    GET  /api/documents/{id}     — Get full document content
    DELETE /api/documents/{id}   — Remove a document
    POST /api/feedback           — Submit user feedback
    GET  /api/config             — Current configuration
    PUT  /api/config             — Update enabled strategies
    GET  /api/stats              — Usage analytics
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import mimetypes

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import SAMPLE_DIR, UPLOAD_DIR
from ..database import DocumentRecord, FeedbackRecord, QueryLog, SessionLocal, get_db
from ..ingestion.pipeline import run_pipeline
from ..models import (
    ConfigResponse,
    ConfigUpdate,
    DocumentInfo,
    FeedbackRequest,
    QueryRequest,
    QueryResponse,
    SourceDocument,
    StatsResponse,
    UploadResponse,
)
from ..retrieval.orchestrator import Orchestrator

router = APIRouter()

# Orchestrator singleton — initialized in main.py and injected here
_orchestrator: Orchestrator | None = None


def set_orchestrator(orch: Orchestrator):
    global _orchestrator
    _orchestrator = orch


def get_orchestrator() -> Orchestrator:
    if _orchestrator is None:
        raise HTTPException(500, "Orchestrator not initialized")
    return _orchestrator


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@router.get("/health")
def health_check():
    orch = get_orchestrator()
    return {
        "status": "healthy",
        "available_strategies": orch.get_available(),
        "enabled_strategies": orch.get_enabled(),
    }


# ---------------------------------------------------------------------------
# Query Endpoint
# ---------------------------------------------------------------------------
@router.post("/query", response_model=QueryResponse)
def query_documents(req: QueryRequest):
    orch = get_orchestrator()
    history = [{"role": m.role, "content": m.content} for m in req.history]

    # Step 1: rewrite query using conversation context
    search_query = orch.rewrite_query(req.query, history)

    # Step 2: retrieve with the rewritten query
    merged, per_strategy, elapsed_ms = orch.query(
        query_text=search_query,
        strategies=req.strategies if req.strategies else None,
        top_k=req.top_k,
    )

    # Step 3: generate answer with full history context
    gen_start = time.time()
    answer = orch.generate_answer(req.query, merged, history)
    gen_ms = (time.time() - gen_start) * 1000

    sources = [
        SourceDocument(
            doc_id=c.doc_id,
            title=c.title,
            filename=c.filename,
            snippet=c.content[:400],
            score=round(c.score, 4),
            strategy=c.strategy,
        )
        for c in merged
    ]

    return QueryResponse(
        answer=answer,
        sources=sources,
        strategies_used=list(per_strategy.keys()),
        retrieval_time_ms=round(elapsed_ms, 2),
        generation_time_ms=round(gen_ms, 2),
        query=req.query,
    )


# ---------------------------------------------------------------------------
# Streaming Query Endpoint
# ---------------------------------------------------------------------------
@router.post("/query/stream")
def query_stream(req: QueryRequest):
    """SSE endpoint that emits sources immediately, then streams answer tokens.

    Events:
        {"type": "rewrite", "rewritten_query": "...", "rewrite_time_ms": ...}
        {"type": "sources", "sources": [...], "strategies_used": [...], "retrieval_time_ms": ...}
        {"type": "token",   "token": "..."}   (one per LLM token)
        {"type": "done", "generation_time_ms": ...}
    """
    orch = get_orchestrator()
    history = [{"role": m.role, "content": m.content} for m in req.history]

    def generate():
        # Phase 1: rewrite query using conversation context
        rw_start = time.time()
        search_query = orch.rewrite_query(req.query, history)
        rw_ms = (time.time() - rw_start) * 1000

        if history:
            yield (
                "data: "
                + json.dumps({
                    "type": "rewrite",
                    "rewritten_query": search_query,
                    "rewrite_time_ms": round(rw_ms, 2),
                })
                + "\n\n"
            )

        # Phase 2: retrieval — emit sources as soon as they are ready
        merged, per_strategy, elapsed_ms = orch.query(
            query_text=search_query,
            strategies=req.strategies if req.strategies else None,
            top_k=req.top_k,
        )

        sources = [
            SourceDocument(
                doc_id=c.doc_id,
                title=c.title,
                filename=c.filename,
                snippet=c.content[:400],
                score=round(c.score, 4),
                strategy=c.strategy,
            ).model_dump()
            for c in merged
        ]

        # Collect agentic tool calls if the strategy was used
        agentic_tool_calls: list[dict] = []
        agentic_strategy = orch._strategies.get("agentic")
        if agentic_strategy and hasattr(agentic_strategy, "_last_tool_calls"):
            agentic_tool_calls = agentic_strategy._last_tool_calls

        yield (
            "data: "
            + json.dumps({
                "type": "sources",
                "sources": sources,
                "strategies_used": list(per_strategy.keys()),
                "retrieval_time_ms": round(elapsed_ms, 2),
                "tool_calls": agentic_tool_calls,
            })
            + "\n\n"
        )

        # Phase 3: stream answer tokens with history context
        gen_start = time.time()
        for token in orch.generate_answer_stream(
            req.query, merged, history
        ):
            yield "data: " + json.dumps({"type": "token", "token": token}) + "\n\n"
        gen_ms = (time.time() - gen_start) * 1000

        yield "data: " + json.dumps({"type": "done", "generation_time_ms": round(gen_ms, 2)}) + "\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Document Management
# ---------------------------------------------------------------------------
@router.post("/documents/upload", response_model=UploadResponse)
def upload_document(file: UploadFile = File(...)):
    """Upload a document for ingestion and indexing.

    The file format is validated against the extractor registry.
    Supported formats are determined dynamically at runtime via the
    Adapter pattern (see ``ingestion/extractors.py``).
    """
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    # Validate format against extractor registry
    from ..ingestion.extractors import default_registry
    suffix = Path(file.filename).suffix.lower()
    if not default_registry.get(suffix):
        supported = ", ".join(default_registry.supported())
        raise HTTPException(
            400,
            f"Unsupported file format '{suffix}'. "
            f"Supported formats: {supported}",
        )

    # Save uploaded file
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run ingestion pipeline
    db = SessionLocal()
    try:
        envelope = run_pipeline(dest, file.filename, db)
        doc = db.query(DocumentRecord).get(envelope.db_id)
        info = DocumentInfo.model_validate(doc)
        return UploadResponse(message=f"Document '{file.filename}' ingested successfully", document=info)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ingestion failed: {e}")
    finally:
        db.close()


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents():
    db = SessionLocal()
    try:
        docs = db.query(DocumentRecord).order_by(DocumentRecord.uploaded_at.desc()).all()
        return [DocumentInfo.model_validate(d) for d in docs]
    finally:
        db.close()


@router.get("/documents/{doc_id}")
def get_document(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(DocumentRecord).get(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")
        return {
            "id": doc.id,
            "filename": doc.original_name,
            "title": doc.title,
            "content": doc.content,
            "summary": doc.summary,
            "file_type": doc.file_type,
            "chunk_count": doc.chunk_count,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        }
    finally:
        db.close()


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: int):
    """Serve the original uploaded file for viewing/download."""
    db = SessionLocal()
    try:
        doc = db.query(DocumentRecord).get(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")
        file_path = UPLOAD_DIR / doc.filename
        if not file_path.exists():
            file_path = SAMPLE_DIR / doc.filename
        if not file_path.exists():
            raise HTTPException(404, "File not found on disk")
        content_type = mimetypes.guess_type(str(file_path))[0] or "text/plain"
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            headers={"Content-Disposition": "inline"},
        )
    finally:
        db.close()


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(DocumentRecord).get(doc_id)
        if not doc:
            raise HTTPException(404, "Document not found")

        # Remove from ChromaDB
        try:
            from ..ingestion.pipeline import get_chroma_collection
            collection = get_chroma_collection()
            # Delete chunks belonging to this document
            results = collection.get(where={"doc_id": doc_id})
            if results["ids"]:
                collection.delete(ids=results["ids"])
        except Exception:
            pass

        # Remove file from uploads
        upload_path = UPLOAD_DIR / doc.filename
        if upload_path.exists():
            upload_path.unlink()

        db.delete(doc)
        db.commit()
        return {"message": f"Document '{doc.original_name}' deleted"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    db = SessionLocal()
    try:
        record = FeedbackRecord(
            query=req.query,
            answer=req.answer,
            rating=req.rating,
            strategy_used=req.strategy_used,
        )
        db.add(record)
        db.commit()
        return {"message": "Feedback recorded"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@router.get("/config", response_model=ConfigResponse)
def get_config():
    orch = get_orchestrator()
    from ..config import BM25_TOP_K, EMBEDDING_MODEL, SEMANTIC_TOP_K
    return ConfigResponse(
        enabled_strategies=orch.get_enabled(),
        available_strategies=orch.get_available(),
        embedding_model=EMBEDDING_MODEL,
        bm25_top_k=BM25_TOP_K,
        semantic_top_k=SEMANTIC_TOP_K,
    )


@router.put("/config")
def update_config(req: ConfigUpdate):
    orch = get_orchestrator()
    if req.enabled_strategies is not None:
        orch.set_enabled(req.enabled_strategies)
    return {"message": "Configuration updated", "enabled_strategies": orch.get_enabled()}


# ---------------------------------------------------------------------------
# Stats / Analytics
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=StatsResponse)
def get_stats():
    db = SessionLocal()
    try:
        total_docs = db.query(func.count(DocumentRecord.id)).scalar() or 0
        total_queries = db.query(func.count(QueryLog.id)).scalar() or 0
        total_feedback = db.query(func.count(FeedbackRecord.id)).scalar() or 0
        avg_time = db.query(func.avg(QueryLog.response_time_ms)).scalar() or 0.0
        helpful = db.query(func.count(FeedbackRecord.id)).filter(
            FeedbackRecord.rating == "helpful"
        ).scalar() or 0
        not_helpful = db.query(func.count(FeedbackRecord.id)).filter(
            FeedbackRecord.rating == "not_helpful"
        ).scalar() or 0
        return StatsResponse(
            total_documents=total_docs,
            total_queries=total_queries,
            total_feedback=total_feedback,
            avg_response_time_ms=round(avg_time, 2),
            helpful_count=helpful,
            not_helpful_count=not_helpful,
        )
    finally:
        db.close()
