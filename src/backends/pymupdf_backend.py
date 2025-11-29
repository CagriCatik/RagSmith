"""PyMuPDF4LLM backend implementation."""
from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
import logging

from src.backends.base import PdfToMarkdownBackend, registry
from src.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("src.backends.pymupdf")


class PyMuPDFBackend(PdfToMarkdownBackend):
    name = "pymupdf4llm"

    def __init__(self, *, enable_layout: bool = True) -> None:
        if util.find_spec("pymupdf4llm") is None:
            raise BackendNotAvailableError("pymupdf4llm is not installed")

        self._layout_enabled = enable_layout and util.find_spec("pymupdf.layout") is not None
        self._impl = import_module("pymupdf4llm")

        if self._layout_enabled:
            import_module("pymupdf.layout").activate()

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with pymupdf4llm", pdf_path)
            content = self._impl.to_markdown(pdf_path)
            return content
        except ValueError as exc:
            if "min() arg is an empty sequence" in str(exc):
                raise BackendConversionError("pymupdf4llm layout bug encountered") from exc
            raise
        except Exception as exc:  # pragma: no cover - library errors vary
            raise BackendConversionError(f"pymupdf4llm failed for {pdf_path}") from exc


registry.register(PyMuPDFBackend.name, PyMuPDFBackend)

__all__ = ["PyMuPDFBackend"]
