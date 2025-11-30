"""PyMuPDF4LLM backend implementation."""
from __future__ import annotations

import logging
from importlib import import_module, util
from pathlib import Path

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.pymupdf")


class PyMuPDFBackend(PdfToMarkdownBackend):
    """Backend using ``pymupdf4llm`` with optional layout support."""

    def __init__(self, *, enable_layout: bool = True, fallback_to_markitdown: bool = True) -> None:
        if util.find_spec("pymupdf4llm") is None:
            raise BackendNotAvailableError("pymupdf4llm is not installed")

        self._fallback_to_markitdown = fallback_to_markitdown
        self._layout_enabled = enable_layout and util.find_spec("pymupdf.layout") is not None
        self._impl = import_module("pymupdf4llm")

        if self._layout_enabled:
            import_module("pymupdf.layout").activate()

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with pymupdf4llm", pdf_path)
            return self._impl.to_markdown(pdf_path)
        except ValueError as exc:
            message = str(exc)
            if "min() arg is an empty sequence" in message or "min() iterable argument is empty" in message:
                if self._fallback_to_markitdown:
                    LOGGER.warning(
                        "Encountered layout bug; falling back to markitdown backend",
                    )
                    try:
                        return self._fallback_convert_with_markitdown(pdf_path)
                    except BackendConversionError:
                        raise
                    except Exception as fallback_exc:  # pragma: no cover - fallback failures vary
                        LOGGER.exception(
                            "Fallback to markitdown failed for %s", pdf_path
                        )
                        raise BackendConversionError(
                            f"pymupdf4llm layout bug encountered for {pdf_path}"
                        ) from fallback_exc
                raise BackendConversionError(
                    f"pymupdf4llm layout bug encountered for {pdf_path}"
                ) from exc
            LOGGER.exception("pymupdf4llm failed for %s", pdf_path)
            raise BackendConversionError(f"pymupdf4llm failed for {pdf_path}: {exc}") from exc
        except Exception as exc:  # pragma: no cover - external library behaviour
            LOGGER.exception("pymupdf4llm failed for %s", pdf_path)
            raise BackendConversionError(f"pymupdf4llm failed for {pdf_path}: {exc}") from exc

    def _fallback_convert_with_markitdown(self, pdf_path: Path) -> str:
        try:
            from ragsmith.backends.markitdown_backend import MarkitdownBackend

            return MarkitdownBackend().convert(pdf_path)
        except Exception as exc:  # pragma: no cover - import/runtime errors
            raise BackendConversionError("Fallback to markitdown failed") from exc


__all__ = ["PyMuPDFBackend"]
