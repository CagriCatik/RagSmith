"""PDF to Markdown backends."""
from src.backends.base import PdfToMarkdownBackend
from src.backends.docling_backend import DoclingBackend
from src.backends.markitdown_backend import MarkitdownBackend
from src.backends.ocr_backend import OCRBackend
from src.backends.pymupdf_backend import PyMuPDFBackend

__all__ = [
    "PdfToMarkdownBackend",
    "DoclingBackend",
    "MarkitdownBackend",
    "OCRBackend",
    "PyMuPDFBackend",
]
