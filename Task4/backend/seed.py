"""Seed script to ingest sample documents into the system."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aamsir.config import SAMPLE_DIR
from aamsir.database import SessionLocal, init_db, DocumentRecord
from aamsir.ingestion.pipeline import run_pipeline


def seed():
    """Ingest all sample documents from data/sample_docs/."""
    init_db()
    db = SessionLocal()

    # Check if already seeded
    existing = db.query(DocumentRecord).count()
    if existing > 0:
        print(f"Database already has {existing} documents. Skipping seed.")
        db.close()
        return

    sample_files = list(SAMPLE_DIR.glob("*"))
    sample_files = [f for f in sample_files if f.suffix in (".txt", ".md", ".pdf")]

    if not sample_files:
        print("No sample documents found.")
        db.close()
        return

    print(f"Ingesting {len(sample_files)} sample documents...")
    for filepath in sample_files:
        print(f"  Processing: {filepath.name}")
        try:
            run_pipeline(filepath, filepath.name, db)
            print(f"    Done ({filepath.name})")
        except Exception as e:
            print(f"    FAILED: {e}")
            db.rollback()

    db.close()
    print("Seed complete!")


if __name__ == "__main__":
    seed()
