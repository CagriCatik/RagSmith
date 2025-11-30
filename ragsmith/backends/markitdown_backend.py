"""MarkItDown backend implementation."""
from __future__ import annotations

import logging
from importlib import import_module, util
from pathlib import Path

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.markitdown")


class MarkitdownBackend(PdfToMarkdownBackend):
    """Backend using the markitdown package."""

    def __init__(self) -> None:
        if util.find_spec("markitdown") is None:
            raise BackendNotAvailableError("markitdown is not installed")
        self._impl = import_module("markitdown").MarkItDown()

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with markitdown", pdf_path)
            result = self._impl.convert(pdf_path)
            return result.text_content
        except Exception as exc:  # pragma: no cover - depends on external library
            raise BackendConversionError(f"markitdown failed for {pdf_path}") from exc


__all__ = ["MarkitdownBackend"]
