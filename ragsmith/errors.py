"""Custom exceptions for RagSmith."""

from __future__ import annotations

from typing import List

class RagSmithError(Exception):
    """Base exception for RagSmith."""


class BackendNotAvailableError(RagSmithError):
    """Raised when a backend dependency is unavailable."""


class BackendConversionError(RagSmithError):
    """Raised when a backend fails during conversion."""


class OutputWriteError(RagSmithError):
    """Raised when writing output files fails or would overwrite existing content."""


def format_exception_chain(exc: BaseException) -> str:
    """Return a compact representation of an exception and its causes.

    This keeps error dialogs and CLI output informative without needing to
    display a full traceback. Each link in the chain includes the exception
    type and message, joined by ``" -> "`` for readability.
    """

    parts: List[str] = []
    current: BaseException | None = exc
    while current is not None:
        label = current.__class__.__name__
        message = str(current)
        parts.append(f"{label}: {message}" if message else label)
        if current.__cause__ is not None:
            current = current.__cause__
        elif current.__context__ is not None and not current.__suppress_context__:
            current = current.__context__
        else:
            current = None
    return " -> ".join(parts)


__all__ = [
    "RagSmithError",
    "BackendNotAvailableError",
    "BackendConversionError",
    "OutputWriteError",
    "format_exception_chain",
]
