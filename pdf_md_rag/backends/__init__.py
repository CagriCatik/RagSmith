"""Backend package with available converters."""
from pdf_md_rag.backends.base import PdfToMarkdownBackend, registry
from pdf_md_rag.backends.markitdown_backend import MarkitdownBackend
from pdf_md_rag.backends.pymupdf_backend import PyMuPDFBackend
from pdf_md_rag.backends.docling_backend import DoclingBackend

__all__ = [
    "PdfToMarkdownBackend",
    "registry",
    "MarkitdownBackend",
    "PyMuPDFBackend",
    "DoclingBackend",
]
