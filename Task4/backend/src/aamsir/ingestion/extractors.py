"""
Text Extractors — Adapter Pattern for document format support.

Each extractor adapts a specific file format into a uniform plain-text
representation.  The ExtractorRegistry dynamically selects the correct
extractor at runtime based on file extension, making it trivial to add
support for new formats: implement TextExtractor and register it.

Extractors that need OCR accept an OcrEngine (Strategy) at construction
time.  This keeps the OCR backend swappable independently of the adapter.

Supported formats:
    .pdf              — PDF documents (text layer + per-page OCR)
    .txt              — Plain-text files
    .md               — Markdown files
    .png .jpg .jpeg   — Raster images (OCR only)
    .bmp .tiff .tif   — Raster images (OCR only)
    .webp .gif        — Raster images (OCR only)

To add a new format (e.g. .docx):
    1. Create a class implementing TextExtractor.
    2. Register it:  registry.register(".docx", DocxExtractor())
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from .ocr import OcrEngine, TesseractOcrEngine

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
    """Handles .pdf files using pdfplumber + OCR (Strategy).

    Per-page extraction strategy:
      1. Attempt text-layer extraction via pdfplumber.
      2. Fall back to table extraction if the text layer is sparse.
      3. Always also render the page to an image and run OCR via the
         injected OcrEngine — OCR output is appended to whatever text
         was found above, so content in embedded images / scanned pages
         is never lost.
    """

    def __init__(self, ocr_engine: OcrEngine) -> None:
        self._ocr = ocr_engine

    def extract(self, filepath: Path) -> str:
        import pdfplumber

        text_parts: list[str] = []

        with pdfplumber.open(filepath) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_texts: list[str] = []

                # --- text / table layer ---
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 20:
                    page_texts.append(page_text)
                else:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            rows = [
                                " | ".join(cell or "" for cell in row)
                                for row in table
                                if row
                            ]
                            page_texts.append("\n".join(rows))

                # --- OCR layer (always runs, appended) ---
                try:
                    pil_image = page.to_image(resolution=150).original
                    ocr_text = self._ocr.image_to_text(pil_image).strip()
                    if ocr_text:
                        page_texts.append(ocr_text)
                except Exception as exc:
                    logger.warning("OCR failed for page %d of %s: %s", page_num, filepath.name, exc)

                if page_texts:
                    text_parts.append("\n".join(page_texts))

        return "\n\n".join(text_parts)

    def supported_extensions(self) -> list[str]:
        return [".pdf"]


class ImageExtractor(TextExtractor):
    """Handles raster image files by running OCR via the injected OcrEngine.

    The image is opened with Pillow and passed directly to the OCR engine —
    no text layer exists, so OCR is the only extraction strategy available.
    """

    def __init__(self, ocr_engine: OcrEngine) -> None:
        self._ocr = ocr_engine

    def extract(self, filepath: Path) -> str:
        from PIL import Image

        image = Image.open(filepath)
        return self._ocr.image_to_text(image).strip()

    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"]


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
    ocr_engine = TesseractOcrEngine()

    for extractor in [
        PlainTextExtractor(),
        MarkdownExtractor(),
        PdfExtractor(ocr_engine),
        ImageExtractor(ocr_engine),
    ]:
        for ext in extractor.supported_extensions():
            registry.register(ext, extractor)

    return registry


# Module-level singleton
default_registry = build_default_registry()
