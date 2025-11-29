"""Docling backend implementation."""
from __future__ import annotations

import logging
from importlib import import_module, util
from pathlib import Path
from typing import Literal

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.docling")

_DeviceLiteral = Literal["auto", "cpu", "cuda", "mps"]


class DoclingBackend(PdfToMarkdownBackend):
    """Backend using Docling's DocumentConverter."""

    def __init__(self, *, device: _DeviceLiteral = "auto") -> None:
        if util.find_spec("docling") is None and util.find_spec("docling.document_converter") is None:
            raise BackendNotAvailableError("docling is not installed")

        self.device = device
        self._load_dependencies()
        self._validate_device()

    def _load_dependencies(self) -> None:
        self._converter_mod = import_module("docling.document_converter")
        self._pipeline_mod = import_module("docling.datamodel.pipeline_options")
        self._accelerator_mod = import_module("docling.datamodel.accelerator_options")
        self._base_models_mod = import_module("docling.datamodel.base_models")

    def _validate_device(self) -> None:
        device_lower = self.device.lower()
        if device_lower == "auto":
            return
        if device_lower == "cpu":
            return
        try:
            torch = import_module("torch")
        except Exception as exc:  # pragma: no cover - depends on environment
            raise BackendNotAvailableError("torch is required for GPU acceleration") from exc

        if device_lower == "cuda" and not torch.cuda.is_available():
            raise BackendNotAvailableError("CUDA device requested but not available")
        if device_lower == "mps" and not getattr(torch.backends, "mps", None) or not torch.backends.mps.is_available():
            raise BackendNotAvailableError("MPS device requested but not available")

    def _build_options(self):  # type: ignore[override]
        accelerator_device = self._accelerator_mod.AcceleratorDevice
        try:
            device_enum = accelerator_device[self.device.upper()]
        except KeyError:
            device_enum = accelerator_device.AUTO
        accelerator = self._accelerator_mod.AcceleratorOptions(device=device_enum)
        pipeline_opts = self._pipeline_mod.PdfPipelineOptions(accelerator=accelerator)
        return accelerator, pipeline_opts

    def convert(self, pdf_path: Path) -> str:
        accelerator, pipeline_opts = self._build_options()
        converter = self._converter_mod.DocumentConverter(
            format_options={
                self._base_models_mod.InputFormat.PDF:
                    self._converter_mod.PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )
        try:
            LOGGER.info("Converting %s with docling on %s", pdf_path, accelerator.device)
            result = converter.convert(pdf_path)
            document = result.document
            if hasattr(document, "as_markdown"):
                return document.as_markdown()
            return "".join(page.to_markdown() for page in document.pages)
        except Exception as exc:  # pragma: no cover - depends on docling runtime
            raise BackendConversionError(f"docling failed for {pdf_path}") from exc


__all__ = ["DoclingBackend"]
