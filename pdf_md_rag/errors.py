"""Custom exceptions for pdf_md_rag."""
from __future__ import annotations


class BackendError(Exception):
    """Base exception for backend issues."""


class BackendNotAvailableError(BackendError):
    """Raised when a backend dependency is unavailable."""


class BackendConversionError(BackendError):
    """Raised when a backend fails to convert a document."""


class OutputWriteError(Exception):
    """Raised when writing output files fails."""


__all__ = [
    "BackendError",
    "BackendNotAvailableError",
    "BackendConversionError",
    "OutputWriteError",
]
