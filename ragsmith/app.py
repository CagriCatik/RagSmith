"""High-level facade for converting PDFs to RAG-ready Markdown."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Sequence

from ragsmith.backends.docling_backend import DoclingBackend
from ragsmith.backends.markitdown_backend import MarkitdownBackend
from ragsmith.backends.pymupdf_backend import PyMuPDFBackend
from ragsmith.config import RagSmithConfig
from ragsmith.errors import BackendConversionError, BackendNotAvailableError, OutputWriteError
from ragsmith.logging_config import get_logger
from ragsmith.processing.rag_markdown import process_for_rag
from ragsmith.processing.splitting import split_by_top_level_headings, slugify

BackendName = Literal["markitdown", "pymupdf4llm", "docling"]


class PdfMarkdownApp:
    """Main application orchestrating backend selection and processing."""

    def __init__(
        self,
        config: RagSmithConfig | None = None,
        *,
        logger: logging.Logger | None = None,
        pymupdf_fallback_to_markitdown: bool = True,
        docling_device: Literal["auto", "cpu", "cuda", "mps"] = "auto",
    ) -> None:
        self.config = config or RagSmithConfig()
        self.logger = logger or get_logger("ragsmith")
        self._backend = self._create_backend(
            self.config.backend,
            pymupdf_fallback_to_markitdown=pymupdf_fallback_to_markitdown,
            docling_device=docling_device,
        )
        self.logger.debug("Initialized PdfMarkdownApp with config: %s", self.config)

    def _create_backend(
        self,
        name: BackendName,
        *,
        pymupdf_fallback_to_markitdown: bool,
        docling_device: Literal["auto", "cpu", "cuda", "mps"],
    ):
        factories = {
            "markitdown": lambda: MarkitdownBackend(),
            "pymupdf4llm": lambda: PyMuPDFBackend(
                fallback_to_markitdown=pymupdf_fallback_to_markitdown
            ),
            "docling": lambda: DoclingBackend(device=docling_device),
        }
        factory = factories.get(name)
        if factory is None:
            raise BackendConversionError(f"Unsupported backend: {name}")
        try:
            return factory()
        except BackendNotAvailableError:
            raise
        except Exception as exc:  # pragma: no cover - safety net
            raise BackendConversionError(f"Failed to initialize backend {name}") from exc

    def convert_file(self, pdf_path: Path) -> str:
        try:
            raw_markdown = self._backend.convert(pdf_path)
        except BackendConversionError:
            raise
        except Exception as exc:  # pragma: no cover - backend specific errors
            self.logger.exception("Unexpected backend failure for %s", pdf_path)
            raise BackendConversionError(f"Conversion failed for {pdf_path}: {exc}") from exc
        return process_for_rag(raw_markdown, reflow=self.config.reflow)

    def convert_files(self, pdf_paths: Iterable[Path]) -> Dict[Path, str]:
        results: Dict[Path, str] = {}
        for path in pdf_paths:
            results[path] = self.convert_file(path)
        return results

    def convert_and_write(
        self,
        pdf_paths: Sequence[Path],
        output_dir: Path | None = None,
    ) -> Dict[Path, List[Path]]:
        paths: List[Path] = list(pdf_paths)
        if not paths:
            return {}

        for path in paths:
            if not path.exists():
                raise OutputWriteError(f"Input file does not exist: {path}")

        created: Dict[Path, List[Path]] = {}
        for path, markdown in self.convert_files(paths).items():
            target_dir = output_dir or path.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            created[path] = []

            if self.config.split_sections:
                sections = split_by_top_level_headings(markdown)
                for index, (title, section_markdown) in enumerate(sections, start=1):
                    slug = slugify(title) or path.stem
                    filename = f"{path.stem}-{slug}.md" if self.config.split_sections else f"{slug}.md"
                    # Ensure unique filenames when headings repeat
                    if any(existing.name == filename for existing in created[path]):
                        filename = f"{path.stem}-{index:02d}-{slug}.md"
                    target = target_dir / filename
                    self._write_output(target, section_markdown)
                    created[path].append(target)
            else:
                target = target_dir / f"{path.stem}.md"
                self._write_output(target, markdown)
                created[path].append(target)

        return created

    def _write_output(self, target: Path, markdown: str) -> None:
        if target.exists() and not self.config.overwrite:
            raise OutputWriteError(f"Refusing to overwrite existing file: {target}")
        try:
            target.write_text(markdown, encoding="utf-8")
            self.logger.info("Wrote %s", target)
        except Exception as exc:  # pragma: no cover - filesystem errors vary
            self.logger.exception("Failed to write %s", target)
            raise OutputWriteError(f"Failed to write {target}: {exc}") from exc


__all__ = ["PdfMarkdownApp"]