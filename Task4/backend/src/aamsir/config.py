"""Application configuration.

Centralises all runtime settings — file paths, database URLs, model
names, and retrieval hyper-parameters — in one importable module.
Values can be overridden via environment variables where noted.

Directory layout (created automatically on import)::

    Task4/backend/data/
    ├── uploads/        # User-uploaded documents
    ├── sample_docs/    # Bundled sample corpus
    ├── db/             # SQLite database (aamsir.db)
    └── chroma/         # ChromaDB persistent vector store
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SAMPLE_DIR = DATA_DIR / "sample_docs"
DB_DIR = DATA_DIR / "db"
CHROMA_DIR = DATA_DIR / "chroma"

# Ensure directories exist
for d in [UPLOAD_DIR, DB_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

SQLITE_URL = f"sqlite:///{DB_DIR / 'aamsir.db'}"
EMBEDDING_MODEL = os.getenv("AAMSIR_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
OLLAMA_MODEL = os.getenv("AAMSIR_OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("AAMSIR_OLLAMA_URL", "http://localhost:11434")

# Retrieval defaults
BM25_TOP_K = 10
SEMANTIC_TOP_K = 10
AGENTIC_TOP_K = 5
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
