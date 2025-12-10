"""MarkItDown backend implementation."""
from __future__ import annotations

import logging
from importlib import import_module, util
from pathlib import Path

from src.backends.base import PdfToMarkdownBackend
from src.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("src.backends.markitdown")


class MarkitdownBackend(PdfToMarkdownBackend):
    """Backend using the ``markitdown`` package."""

    def __init__(self) -> None:
        if util.find_spec("markitdown") is None:
            raise BackendNotAvailableError("markitdown is not installed")

        self._markitdown_mod = import_module("markitdown")
        self._exceptions_mod = import_module("markitdown._exceptions")
        self._missing_dependency_exc = getattr(
            self._exceptions_mod, "MissingDependencyException", RuntimeError
        )
        self._file_conversion_exc = getattr(
            self._exceptions_mod, "FileConversionException", RuntimeError
        )
        self._impl = self._markitdown_mod.MarkItDown()

    def convert(self, pdf_path: Path) -> str:
        try:
            LOGGER.info("Converting %s with markitdown", pdf_path)
            result = self._impl.convert(pdf_path)
            return result.text_content
        except self._missing_dependency_exc as exc:  # pragma: no cover - env specific
            raise BackendNotAvailableError(
                "markitdown PDF support is not installed; install with markitdown[pdf]"
            ) from exc
        except self._file_conversion_exc as exc:  # pragma: no cover - library behavior
            LOGGER.exception("markitdown failed for %s", pdf_path)
            raise BackendConversionError(
                f"markitdown failed for {pdf_path}: {exc}"
            ) from exc
        except Exception as exc:  # pragma: no cover - external library behavior
            LOGGER.exception("markitdown failed for %s", pdf_path)
            raise BackendConversionError(
                f"markitdown failed for {pdf_path}: {exc}"
            ) from exc


__all__ = ["MarkitdownBackend"]
