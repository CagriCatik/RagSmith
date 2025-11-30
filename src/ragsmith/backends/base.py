"""Backend abstractions for converting PDFs to Markdown."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PdfToMarkdownBackend(ABC):
    """Abstract base class for conversion backends."""

    @abstractmethod
    def convert(self, pdf_path: Path) -> str:
        """Convert the given PDF to Markdown."""


__all__ = ["PdfToMarkdownBackend"]
