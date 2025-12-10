"""High-level facade for converting PDFs to RAG-ready Markdown."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Sequence

from src.backends.docling_backend import DoclingBackend
from src.backends.markitdown_backend import MarkitdownBackend
from src.backends.ocr_backend import OCRBackend
from src.backends.pymupdf_backend import PyMuPDFBackend
from src.config import RagSmithConfig
from src.errors import BackendConversionError, BackendNotAvailableError, OutputWriteError
from src.logging_config import get_logger
from src.processing.rag_markdown import process_for_rag
from src.processing.splitting import split_by_top_level_headings, slugify

BackendName = Literal["markitdown", "pymupdf4llm", "docling", "ocr"]


class PdfMarkdownApp:
    """Main application orchestrating backend selection and processing."""

    def __init__(
        self,
        config: RagSmithConfig | None = None,
        *,
        logger: logging.Logger | None = None,
        pymupdf_fallback_to_markitdown: bool = True,
        docling_device: Literal["auto", "cpu", "cuda", "mps"] = "auto",
        ocr_languages: Sequence[str] | None = None,
        ocr_device: Literal["auto", "cpu", "cuda", "mps"] | None = None,
        ocr_dpi: int | None = None,
        ocr_start_page: int | None = None,
        ocr_end_page: int | None = None,
    ) -> None:
        self.config = config or RagSmithConfig()
        if ocr_languages is not None:
            self.config.ocr_languages = list(ocr_languages)
        if ocr_device is not None:
            self.config.ocr_device = ocr_device
        if ocr_dpi is not None:
            self.config.ocr_dpi = ocr_dpi
        if ocr_start_page is not None:
            self.config.ocr_start_page = ocr_start_page
        if ocr_end_page is not None:
            self.config.ocr_end_page = ocr_end_page
        self.logger = logger or get_logger("ragsmith")
        self._backend = self._create_backend(
            self.config.backend,
            pymupdf_fallback_to_markitdown=pymupdf_fallback_to_markitdown,
            docling_device=docling_device,
            ocr_languages=self.config.ocr_languages,
            ocr_device=self.config.ocr_device,
            ocr_dpi=self.config.ocr_dpi,
            ocr_start_page=self.config.ocr_start_page,
            ocr_end_page=self.config.ocr_end_page,
        )
        self.logger.debug("Initialized PdfMarkdownApp with config: %s", self.config)

    def _create_backend(
        self,
        name: BackendName,
        *,
        pymupdf_fallback_to_markitdown: bool,
        docling_device: Literal["auto", "cpu", "cuda", "mps"],
        ocr_languages: Sequence[str],
        ocr_device: Literal["auto", "cpu", "cuda", "mps"],
        ocr_dpi: int,
        ocr_start_page: int | None,
        ocr_end_page: int | None,
    ):
        factories = {
            "markitdown": lambda: MarkitdownBackend(),
            "pymupdf4llm": lambda: PyMuPDFBackend(
                fallback_to_markitdown=pymupdf_fallback_to_markitdown
            ),
            "docling": lambda: DoclingBackend(device=docling_device),
            "ocr": lambda: OCRBackend(
                languages=ocr_languages,
                device=ocr_device,
                dpi=ocr_dpi,
                start_page=ocr_start_page,
                end_page=ocr_end_page,
            ),
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
