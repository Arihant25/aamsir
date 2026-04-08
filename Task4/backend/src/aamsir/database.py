"""SQLite database setup using SQLAlchemy.

Defines the relational schema for three core tables:

* **documents** — metadata and full text of ingested documents.
* **feedback**  — user ratings on query responses (FR-03).
* **query_logs** — timing and strategy data for every query (analytics).

Usage::

    from aamsir.database import init_db, SessionLocal

    init_db()                       # create tables if needed
    db = SessionLocal()             # obtain a session
    db.query(DocumentRecord).all()  # query
    db.close()                      # release
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import SQLITE_URL


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    """Stores metadata and raw content for each ingested document."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(512), nullable=False)
    original_name = Column(String(512), nullable=False)
    title = Column(String(512), default="")
    content = Column(Text, default="")
    summary = Column(Text, default="")
    file_type = Column(String(32), default="txt")
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_indexed = Column(Boolean, default=False)


class FeedbackRecord(Base):
    """Records user feedback (helpful / not_helpful) on query responses."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(String(16), nullable=False)  # "helpful" or "not_helpful"
    strategy_used = Column(String(128), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryLog(Base):
    """Logs every query for analytics (response time, strategies, result count)."""

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    strategies_used = Column(String(256), default="")
    response_time_ms = Column(Float, default=0.0)
    result_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


engine = create_engine(SQLITE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(engine)


def get_db() -> Session:
    """FastAPI dependency that yields a SQLAlchemy session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
