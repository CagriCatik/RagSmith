"""High-level facade for converting PDFs to RAG-ready Markdown."""
from __future__ import annotations

from dataclasses import asdict
import logging
from pathlib import Path
from typing import Dict, Iterable

from pdf_md_rag.backends.docling_backend import DoclingBackend
from pdf_md_rag.backends.markitdown_backend import MarkitdownBackend
from pdf_md_rag.backends.pymupdf_backend import PyMuPDFBackend
from pdf_md_rag.config import AppConfig
from pdf_md_rag.errors import BackendConversionError, BackendError, BackendNotAvailableError, OutputWriteError
from pdf_md_rag.processing.rag_markdown import process_for_rag
from pdf_md_rag.processing.splitting import split_by_top_level_headings, slugify

LOGGER = logging.getLogger("pdf_md_rag.app")


BACKEND_FACTORIES = {
    "markitdown": lambda cfg: MarkitdownBackend(),
    "pymupdf4llm": lambda cfg: PyMuPDFBackend(),
    "docling": lambda cfg: DoclingBackend(device=cfg.backend.docling_device),
}


class PdfMarkdownApp:
    def __init__(self, config: AppConfig | None = None):
        self.config = config or AppConfig()
        self._backend = self._create_backend()
        LOGGER.debug("Initialized with config: %s", asdict(self.config))

    def _create_backend(self):
        name = self.config.backend.name
        if name not in BACKEND_FACTORIES:
            raise BackendConversionError(f"Unsupported backend: {name}")
        try:
            return BACKEND_FACTORIES[name](self.config)
        except BackendNotAvailableError:
            if name == "pymupdf4llm" and self.config.backend.enable_pymupdf_fallback:
                LOGGER.warning("pymupdf4llm unavailable, falling back to markitdown")
                return MarkitdownBackend()
            if name == "docling" and self.config.backend.enable_docling_fallback:
                LOGGER.warning("docling unavailable, falling back to markitdown")
                return MarkitdownBackend()
            raise

    def convert_file(self, pdf_path: Path, *, reflow: bool | None = None) -> str:
        reflow_enabled = self.config.default_reflow if reflow is None else reflow
        raw_markdown = self._backend.convert(pdf_path)
        return process_for_rag(raw_markdown, reflow=reflow_enabled, cleaning=self.config.cleaning)

    def convert_files(self, pdf_paths: Iterable[Path], *, reflow: bool | None = None) -> Dict[Path, str]:
        results: Dict[Path, str] = {}
        for path in pdf_paths:
            try:
                results[path] = self.convert_file(path, reflow=reflow)
            except BackendError as exc:
                LOGGER.error("Conversion failed for %s: %s", path, exc)
        return results

    def convert_and_write(
        self,
        pdf_paths: Iterable[Path],
        output_dir: Path,
        *,
        split_sections: bool | None = None,
        reflow: bool | None = None,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        split_enabled = self.config.default_split_sections if split_sections is None else split_sections
        for path, markdown in self.convert_files(pdf_paths, reflow=reflow).items():
            if split_enabled:
                sections = split_by_top_level_headings(markdown)
                for title, section_markdown in sections:
                    filename = f"{slugify(title) or path.stem}.md"
                    self._write_output(output_dir / filename, section_markdown)
            else:
                target = output_dir / f"{path.stem}.md"
                self._write_output(target, markdown)

    def _write_output(self, target: Path, markdown: str) -> None:
        if target.exists() and not self.config.overwrite:
            raise OutputWriteError(f"Refusing to overwrite existing file: {target}")
        try:
            target.write_text(markdown, encoding="utf-8")
            LOGGER.info("Wrote %s", target)
        except Exception as exc:  # pragma: no cover - filesystem errors vary
            raise OutputWriteError(f"Failed to write {target}") from exc


__all__ = ["PdfMarkdownApp"]
