"""Docling backend implementation."""
from __future__ import annotations

import logging
from importlib import import_module
from pathlib import Path
from typing import Literal

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.docling")

_DeviceLiteral = Literal["auto", "cpu", "cuda", "mps"]


class DoclingBackend(PdfToMarkdownBackend):
    """Backend using Docling's ``DocumentConverter``."""

    def __init__(self, *, device: _DeviceLiteral = "auto") -> None:
        self.device = device
        self._converter_mod = None
        self._pipeline_mod = None
        self._accelerator_mod = None
        self._base_models_mod = None
        self._load_dependencies()
        self._validate_device()

    def _load_dependencies(self) -> None:
        try:
            self._converter_mod = import_module("docling.document_converter")
            self._pipeline_mod = import_module("docling.datamodel.pipeline_options")
            self._accelerator_mod = import_module("docling.datamodel.accelerator_options")
            self._base_models_mod = import_module("docling.datamodel.base_models")
        except Exception as exc:  # pragma: no cover - depends on environment
            raise BackendNotAvailableError("docling is not installed") from exc

    def _validate_device(self) -> None:
        device_lower = self.device.lower()
        if device_lower in {"auto", "cpu"}:
            return

        try:
            torch = import_module("torch")
        except Exception as exc:  # pragma: no cover - depends on environment
            raise BackendNotAvailableError("torch is required for GPU acceleration") from exc

        if device_lower == "cuda" and not torch.cuda.is_available():
            raise BackendNotAvailableError("CUDA device requested but not available")
        if device_lower == "mps":
            has_mps = getattr(torch.backends, "mps", None)
            if not has_mps or not torch.backends.mps.is_available():
                raise BackendNotAvailableError("MPS device requested but not available")

    def _build_options(self):
        accelerator_device = self._accelerator_mod.AcceleratorDevice
        try:
            device_enum = accelerator_device[self.device.upper()]
        except KeyError:
            device_enum = accelerator_device.AUTO
        accelerator = self._accelerator_mod.AcceleratorOptions(device=device_enum)
        pipeline_opts = self._pipeline_mod.PdfPipelineOptions(accelerator=accelerator)
        return accelerator, pipeline_opts

    def _export_markdown(self, document: object) -> str:
        export = getattr(document, "export_to_markdown", None)
        if callable(export):
            return export()

        pages = getattr(document, "pages", None)
        if pages is None:
            raise BackendConversionError("docling document does not expose pages or markdown export")

        page_iter = pages.values() if isinstance(pages, dict) else pages
        markdown_parts = []
        for page in page_iter:
            export_page = getattr(page, "export_to_markdown", None) or getattr(page, "to_markdown", None)
            if not callable(export_page):
                raise BackendConversionError(
                    "docling returned page items without a markdown export method",
                )
            markdown_parts.append(export_page())
        return "".join(markdown_parts)

    def convert(self, pdf_path: Path) -> str:
        accelerator, pipeline_opts = self._build_options()
        converter = self._converter_mod.DocumentConverter(
            format_options={
                self._base_models_mod.InputFormat.PDF: self._converter_mod.PdfFormatOption(
                    pipeline_options=pipeline_opts
                )
            }
        )
        try:
            LOGGER.info("Converting %s with docling on %s", pdf_path, accelerator.device)
            result = converter.convert(pdf_path)
            document = result.document
            if hasattr(document, "as_markdown"):
                return document.as_markdown()

            return self._export_markdown(document)
        except BackendNotAvailableError:
            raise
        except BackendConversionError:
            raise
        except Exception as exc:  # pragma: no cover - docling runtime issues
            LOGGER.exception("Docling conversion failed for %s", pdf_path)
            raise BackendConversionError(
                f"docling failed for {pdf_path}: {exc}"
            ) from exc


__all__ = ["DoclingBackend"]
