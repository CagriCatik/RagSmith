"""High-level facade for converting PDFs to RAG-ready Markdown."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List

from ragsmith.backends.docling_backend import DoclingBackend
from ragsmith.backends.markitdown_backend import MarkitdownBackend
from ragsmith.backends.pymupdf_backend import PyMuPDFBackend
from ragsmith.config import RagSmithConfig
from ragsmith.errors import BackendConversionError, BackendNotAvailableError, OutputWriteError
from ragsmith.processing.rag_markdown import process_for_rag
from ragsmith.processing.splitting import split_by_top_level_headings, slugify

LOGGER = logging.getLogger("ragsmith.app")


class PdfMarkdownApp:
    """Main application orchestrating backend selection and processing."""

    def __init__(self, config: RagSmithConfig | None = None):
        self.config = config or RagSmithConfig.from_env()
        self._backend = self._create_backend(self.config.backend)
        LOGGER.debug("Initialized PdfMarkdownApp with config: %s", self.config)

    def _create_backend(self, name: str):
        factory = {
            "markitdown": lambda: MarkitdownBackend(),
            "pymupdf4llm": lambda: PyMuPDFBackend(),
            "docling": lambda: DoclingBackend(),
        }.get(name)
        if factory is None:
            raise BackendConversionError(f"Unsupported backend: {name}")
        try:
            return factory()
        except BackendNotAvailableError:
            raise

    def convert_file(self, pdf_path: Path) -> str:
        raw_markdown = self._backend.convert(pdf_path)
        return process_for_rag(raw_markdown, reflow=self.config.reflow)

    def convert_files(self, pdf_paths: Iterable[Path]) -> Dict[Path, str]:
        results: Dict[Path, str] = {}
        for path in pdf_paths:
            results[path] = self.convert_file(path)
        return results

    def convert_and_write(self, pdf_paths: Iterable[Path], output_dir: Path | None = None) -> None:
        paths: List[Path] = list(pdf_paths)
        if not paths:
            return
        for path in paths:
            if not path.exists():
                raise OutputWriteError(f"Input file does not exist: {path}")

        for path, markdown in self.convert_files(paths).items():
            if self.config.split_sections:
                sections = split_by_top_level_headings(markdown)
                for title, section_markdown in sections:
                    filename = f"{slugify(title) or path.stem}.md"
                    target_dir = output_dir or path.parent
                    self._write_output(target_dir / filename, section_markdown)
            else:
                target_dir = output_dir or path.parent
                target = target_dir / f"{path.stem}.md"
                self._write_output(target, markdown)

    def _write_output(self, target: Path, markdown: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not self.config.overwrite:
            raise OutputWriteError(f"Refusing to overwrite existing file: {target}")
        try:
            target.write_text(markdown, encoding="utf-8")
            LOGGER.info("Wrote %s", target)
        except Exception as exc:  # pragma: no cover - filesystem errors vary
            raise OutputWriteError(f"Failed to write {target}") from exc


__all__ = ["PdfMarkdownApp"]
