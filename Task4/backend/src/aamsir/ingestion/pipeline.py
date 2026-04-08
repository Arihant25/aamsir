"""
Document Ingestion Pipeline — Pipe-and-Filter Architecture (ADR-002).

Each filter is a stateless function that transforms a DocumentEnvelope:

    RawFile -> TextExtractor -> Summarizer -> Chunker -> Embedder -> Indexer

The TextExtractor filter uses the Adapter pattern (see ``extractors.py``)
to dynamically resolve the correct extractor at runtime based on the file
extension.  New formats can be added by registering an adapter — no
pipeline code needs to change.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from ..config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL
from ..database import DocumentRecord
from .extractors import default_registry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document Envelope — travels through the pipeline
# ---------------------------------------------------------------------------
@dataclass
class DocumentEnvelope:
    """Self-contained data object flowing through pipeline filters.

    Attributes:
        filepath:      Path to the source file on disk.
        original_name: User-facing filename (may differ from filepath.name).
        raw_text:      Full plain-text content after extraction.
        title:         Document title derived from content or filename.
        summary:       Short extractive summary.
        chunks:        List of text chunks for embedding.
        chunk_ids:     Deterministic IDs for each chunk (used by ChromaDB).
        embeddings:    Vector embeddings corresponding to each chunk.
        file_type:     Lowercase file extension without dot (e.g. "pdf").
        db_id:         Primary key assigned after SQLite insertion.
    """

    filepath: Path
    original_name: str
    raw_text: str = ""
    title: str = ""
    summary: str = ""
    chunks: list[str] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    file_type: str = "txt"
    db_id: int | None = None


# ---------------------------------------------------------------------------
# Filter 1: Text Extractor  (uses Adapter pattern via ExtractorRegistry)
# ---------------------------------------------------------------------------
def extract_text(envelope: DocumentEnvelope) -> DocumentEnvelope:
    """Extract raw text using the dynamically-resolved format adapter.

    The correct extractor is selected at runtime from the
    ``ExtractorRegistry`` based on the file's extension.  If no adapter
    is registered for the extension, a warning is logged and the file is
    skipped gracefully.
    """
    suffix = envelope.filepath.suffix.lower()
    envelope.file_type = suffix.lstrip(".")

    extractor = default_registry.get(suffix)
    if extractor is None:
        supported = ", ".join(default_registry.supported())
        logger.warning(
            f"Unsupported file format '{suffix}' for {envelope.original_name}. "
            f"Supported formats: {supported}. Skipping extraction."
        )
        envelope.raw_text = ""
        envelope.title = envelope.original_name
        return envelope

    envelope.raw_text = extractor.extract(envelope.filepath)

    # Derive title from first non-empty line or filename
    lines = [line.strip() for line in envelope.raw_text.split("\n") if line.strip()]
    if lines:
        candidate = re.sub(r"^#+\s*", "", lines[0])  # strip markdown heading
        envelope.title = candidate[:200]
    else:
        envelope.title = envelope.original_name

    logger.info(f"Extracted {len(envelope.raw_text)} chars from {envelope.original_name}")
    return envelope


# ---------------------------------------------------------------------------
# Filter 2: Summarizer (extractive — first ~300 chars as summary)
# ---------------------------------------------------------------------------
def summarize(envelope: DocumentEnvelope) -> DocumentEnvelope:
    """Generate an extractive summary (first paragraph / ~300 chars).

    A full abstractive summarizer would use an LLM, but for the prototype
    we use an extractive approach to stay fully local without GPU requirements.
    """
    text = envelope.raw_text.strip()
    # Take first meaningful paragraph
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 40]
    if paragraphs:
        envelope.summary = paragraphs[0][:500]
    else:
        envelope.summary = text[:500]
    return envelope


# ---------------------------------------------------------------------------
# Filter 3: Chunker
# ---------------------------------------------------------------------------
def chunk_text(envelope: DocumentEnvelope) -> DocumentEnvelope:
    """Split text into overlapping chunks for embedding."""
    text = envelope.raw_text
    if not text.strip():
        envelope.chunks = []
        envelope.chunk_ids = []
        return envelope

    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP

    envelope.chunks = chunks
    # Create deterministic IDs: doc_hash + chunk_index
    doc_hash = hashlib.md5(envelope.original_name.encode()).hexdigest()[:8]
    envelope.chunk_ids = [f"{doc_hash}_chunk_{i}" for i in range(len(chunks))]
    logger.info(f"Chunked into {len(chunks)} chunks")
    return envelope


# ---------------------------------------------------------------------------
# Filter 4: Embedder
# ---------------------------------------------------------------------------
_model_cache: dict[str, SentenceTransformer] = {}


def get_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def embed_chunks(envelope: DocumentEnvelope) -> DocumentEnvelope:
    """Compute embeddings for each chunk using sentence-transformers."""
    if not envelope.chunks:
        return envelope
    model = get_embedding_model()
    embeddings = model.encode(envelope.chunks, show_progress_bar=False)
    envelope.embeddings = embeddings.tolist()
    logger.info(f"Embedded {len(envelope.embeddings)} chunks")
    return envelope


# ---------------------------------------------------------------------------
# Filter 5: Indexer (persist to ChromaDB + SQLite)
# ---------------------------------------------------------------------------
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_chroma_collection(client: chromadb.PersistentClient | None = None):
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name="aamsir_documents",
        metadata={"hnsw:space": "cosine"},
    )


def index_document(envelope: DocumentEnvelope, db: Session) -> DocumentEnvelope:
    """Persist document metadata to SQLite and embeddings to ChromaDB."""
    # Save to SQLite
    record = DocumentRecord(
        filename=envelope.filepath.name,
        original_name=envelope.original_name,
        title=envelope.title,
        content=envelope.raw_text,
        summary=envelope.summary,
        file_type=envelope.file_type,
        chunk_count=len(envelope.chunks),
        is_indexed=True,
    )
    db.add(record)
    db.flush()
    envelope.db_id = record.id

    # Save to ChromaDB
    if envelope.chunks and envelope.embeddings:
        collection = get_chroma_collection()
        metadatas = [
            {
                "doc_id": record.id,
                "title": envelope.title,
                "filename": envelope.original_name,
                "chunk_index": i,
            }
            for i in range(len(envelope.chunks))
        ]
        collection.add(
            ids=envelope.chunk_ids,
            embeddings=envelope.embeddings,
            documents=envelope.chunks,
            metadatas=metadatas,
        )
    logger.info(f"Indexed document id={record.id} with {len(envelope.chunks)} chunks")
    return envelope


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(filepath: Path, original_name: str, db: Session) -> DocumentEnvelope:
    """Run the complete ingestion pipeline on a single document."""
    envelope = DocumentEnvelope(filepath=filepath, original_name=original_name)

    # Pipe-and-Filter: each filter transforms the envelope
    envelope = extract_text(envelope)
    envelope = summarize(envelope)
    envelope = chunk_text(envelope)
    envelope = embed_chunks(envelope)
    envelope = index_document(envelope, db)

    db.commit()
    return envelope
