"""Backend package with available converters."""
from src.backends.base import PdfToMarkdownBackend, registry
from src.backends.markitdown_backend import MarkitdownBackend
from src.backends.pymupdf_backend import PyMuPDFBackend
from src.backends.docling_backend import DoclingBackend

__all__ = [
    "PdfToMarkdownBackend",
    "registry",
    "MarkitdownBackend",
    "PyMuPDFBackend",
    "DoclingBackend",
]
