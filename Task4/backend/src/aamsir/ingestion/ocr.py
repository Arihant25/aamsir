"""
OCR Engines — Strategy Pattern for optical character recognition.

Each engine adapts a different OCR backend to a uniform interface.
The concrete engine is injected into extractors that require OCR, so the
backend (e.g. Tesseract → EasyOCR) can be swapped without touching any
extractor logic.

To add a new OCR backend:
    1. Subclass OcrEngine and implement ``image_to_text``.
    2. Pass an instance to the extractor(s) that need it.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from PIL import Image

logger = logging.getLogger(__name__)


class OcrEngine(ABC):
    """Strategy interface — converts a PIL image to plain text."""

    @abstractmethod
    def image_to_text(self, image: Image.Image) -> str:
        """Extract text from *image* and return it as a string."""
        ...


class TesseractOcrEngine(OcrEngine):
    """OCR strategy backed by Tesseract via pytesseract.

    Requires the Tesseract binary to be installed on the host system:
        macOS:  brew install tesseract
        Ubuntu: apt install tesseract-ocr
    """

    def image_to_text(self, image: Image.Image) -> str:
        try:
            import pytesseract

            return pytesseract.image_to_string(image)
        except Exception as exc:
            logger.warning("Tesseract OCR failed: %s", exc)
            return ""
