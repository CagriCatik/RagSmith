"""OCR backend implementation using Tesseract and pdf2image."""
from __future__ import annotations

import logging
from importlib import import_module
from pathlib import Path

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.ocr")


class OCRBackend(PdfToMarkdownBackend):
    """Backend that rasterizes PDF pages then extracts text via OCR."""

    def __init__(self, *, lang: str = "eng", dpi: int = 300) -> None:
        self.lang = lang
        self.dpi = dpi
        self._tesseract = None
        self._pdf2image = None
        self._load_dependencies()

    def _load_dependencies(self) -> None:
        try:
            self._tesseract = import_module("pytesseract")
            self._pdf2image = import_module("pdf2image")
        except Exception as exc:  # pragma: no cover - depends on runtime deps
            raise BackendNotAvailableError(
                "OCR dependencies missing; install pytesseract and pdf2image",
            ) from exc

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with OCR (dpi=%s, lang=%s)", pdf_path, self.dpi, self.lang)
            images = self._pdf2image.convert_from_path(str(pdf_path), dpi=self.dpi)
        except Exception as exc:  # pragma: no cover - external runtime details
            LOGGER.exception("Failed to rasterize %s for OCR", pdf_path)
            raise BackendConversionError(f"Failed to rasterize {pdf_path}: {exc}") from exc

        if not images:
            raise BackendConversionError(f"No pages rendered for {pdf_path}")

        markdown_parts = []
        for index, image in enumerate(images, start=1):
            try:
                text = self._tesseract.image_to_string(image, lang=self.lang)
            except Exception as exc:  # pragma: no cover - OCR errors vary
                LOGGER.exception("OCR failed on page %s of %s", index, pdf_path)
                raise BackendConversionError(
                    f"OCR failed for page {index} of {pdf_path}: {exc}",
                ) from exc

            cleaned = text.strip()
            markdown_parts.append(f"# Page {index}\n\n{cleaned}\n")

        if not any(part.strip() for part in markdown_parts):
            raise BackendConversionError(f"OCR produced no text for {pdf_path}")

        return "\n".join(markdown_parts)


__all__ = ["OCRBackend"]
