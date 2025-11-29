"""Custom exceptions for RagSmith."""

class RagSmithError(Exception):
    """Base exception for RagSmith."""


class BackendNotAvailableError(RagSmithError):
    """Raised when a backend dependency is unavailable."""


class BackendConversionError(RagSmithError):
    """Raised when a backend fails during conversion."""


class OutputWriteError(RagSmithError):
    """Raised when writing output files fails or would overwrite existing content."""


__all__ = [
    "RagSmithError",
    "BackendNotAvailableError",
    "BackendConversionError",
    "OutputWriteError",
]
