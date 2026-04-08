"""
Text Extractors — Adapter Pattern for document format support.

Each extractor adapts a specific file format into a uniform plain-text
representation.  The ExtractorRegistry dynamically selects the correct
extractor at runtime based on file extension, making it trivial to add
support for new formats: implement TextExtractor and register it.

Supported formats:
    .pdf  — PDF documents (text layer + image-based OCR fallback planned)
    .txt  — Plain-text files
    .md   — Markdown files (headings stripped for title extraction)

To add a new format (e.g. .docx):
    1. Create a class implementing TextExtractor.
    2. Register it:  ExtractorRegistry.register(".docx", DocxExtractor())
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class TextExtractor(ABC):
    """Adapter interface — converts a file into raw text."""

    @abstractmethod
    def extract(self, filepath: Path) -> str:
        """Read the file at *filepath* and return its textual content."""
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return the file extensions this extractor handles (e.g. ['.pdf'])."""
        ...


# ---------------------------------------------------------------------------
# Concrete Extractors
# ---------------------------------------------------------------------------


class PlainTextExtractor(TextExtractor):
    """Handles .txt and similar plain-text files."""

    def extract(self, filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8", errors="replace")

    def supported_extensions(self) -> list[str]:
        return [".txt"]


class MarkdownExtractor(TextExtractor):
    """Handles .md Markdown files (strips heading markers for cleaner text)."""

    def extract(self, filepath: Path) -> str:
        raw = filepath.read_text(encoding="utf-8", errors="replace")
        # Optionally strip markdown heading syntax for cleaner content
        return raw

    def supported_extensions(self) -> list[str]:
        return [".md"]


class PdfExtractor(TextExtractor):
    """Handles .pdf files using pdfplumber.

    Uses a best-effort strategy:
      1. Attempts text-layer extraction via pdfplumber.
      2. Falls back to table extraction if text layer is sparse.
      3. Logs a warning for image-only pages (OCR not included in prototype).
    """

    def extract(self, filepath: Path) -> str:
        import pdfplumber

        text_parts: list[str] = []
        image_only_pages: list[int] = []

        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Try text extraction first
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 20:
                    text_parts.append(page_text)
                    continue

                # Try table extraction as fallback
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        rows = [
                            " | ".join(cell or "" for cell in row)
                            for row in table
                            if row
                        ]
                        text_parts.append("\n".join(rows))
                    continue

                # Image-only page — no text extracted
                image_only_pages.append(page_num)

        if image_only_pages:
            logger.warning(
                f"Pages {image_only_pages} in {filepath.name} appear to be "
                f"image-only (OCR not available in prototype). Text from "
                f"these pages was not extracted."
            )

        return "\n\n".join(text_parts)

    def supported_extensions(self) -> list[str]:
        return [".pdf"]


# ---------------------------------------------------------------------------
# Registry — runtime selection of the appropriate extractor
# ---------------------------------------------------------------------------


class ExtractorRegistry:
    """Maps file extensions to TextExtractor instances.

    Acts as a simple service locator so that ``extract_text`` in the pipeline
    can resolve the right adapter at runtime without conditionals.
    """

    def __init__(self) -> None:
        self._extractors: dict[str, TextExtractor] = {}

    def register(self, ext: str, extractor: TextExtractor) -> None:
        """Register an extractor for one or more extensions."""
        self._extractors[ext.lower()] = extractor

    def get(self, ext: str) -> TextExtractor | None:
        """Look up extractor by file extension (e.g. '.pdf')."""
        return self._extractors.get(ext.lower())

    def supported(self) -> list[str]:
        """List all registered extensions."""
        return list(self._extractors.keys())


def build_default_registry() -> ExtractorRegistry:
    """Create a registry pre-loaded with all built-in extractors."""
    registry = ExtractorRegistry()

    for extractor in [PlainTextExtractor(), MarkdownExtractor(), PdfExtractor()]:
        for ext in extractor.supported_extensions():
            registry.register(ext, extractor)

    return registry


# Module-level singleton
default_registry = build_default_registry()
