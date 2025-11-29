"""MarkItDown backend implementation."""
from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
import logging

from pdf_md_rag.backends.base import PdfToMarkdownBackend, registry
from pdf_md_rag.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("pdf_md_rag.backends.markitdown")


class MarkitdownBackend(PdfToMarkdownBackend):
    name = "markitdown"

    def __init__(self) -> None:
        if util.find_spec("markitdown") is None:
            raise BackendNotAvailableError("markitdown is not installed")
        self._impl = import_module("markitdown").MarkItDown()

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with markitdown", pdf_path)
            result = self._impl.convert(pdf_path)
            return result.text_content
        except Exception as exc:  # pragma: no cover - depends on lib errors
            raise BackendConversionError(f"markitdown failed for {pdf_path}") from exc


registry.register(MarkitdownBackend.name, MarkitdownBackend)

__all__ = ["MarkitdownBackend"]
