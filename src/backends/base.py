"""Backend abstractions for converting PDFs to Markdown."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.errors import BackendConversionError


class PdfToMarkdownBackend(ABC):
    """Abstract base class for conversion backends."""

    name: str

    @abstractmethod
    def convert(self, pdf_path: Path) -> str:
        """Convert the given PDF to Markdown."""


class BackendRegistry:
    """Registry to map backend names to classes."""

    def __init__(self) -> None:
        self._registry: dict[str, type[PdfToMarkdownBackend]] = {}

    def register(self, name: str, cls: type[PdfToMarkdownBackend]) -> None:
        self._registry[name] = cls

    def get(self, name: str) -> type[PdfToMarkdownBackend]:
        try:
            return self._registry[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise BackendConversionError(f"Unknown backend '{name}'") from exc

    def names(self) -> list[str]:
        return sorted(self._registry)


registry = BackendRegistry()


__all__ = ["PdfToMarkdownBackend", "BackendRegistry", "registry"]
