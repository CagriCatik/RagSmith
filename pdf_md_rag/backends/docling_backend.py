"""Docling backend implementation."""
from __future__ import annotations

from importlib import import_module, util
from pathlib import Path
import logging

from pdf_md_rag.backends.base import PdfToMarkdownBackend, registry
from pdf_md_rag.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("pdf_md_rag.backends.docling")


class DoclingBackend(PdfToMarkdownBackend):
    name = "docling"

    def __init__(self, *, device: str = "auto") -> None:
        if util.find_spec("docling") is None and util.find_spec("docling.document_converter") is None:
            raise BackendNotAvailableError("docling is not installed")

        converter_mod = import_module("docling.document_converter")
        pipeline_mod = import_module("docling.datamodel.pipeline_options")
        accelerator_mod = import_module("docling.datamodel.accelerator_options")
        base_models = import_module("docling.datamodel.base_models")

        self._accelerator_device = accelerator_mod.AcceleratorDevice
        self._accelerator_options_cls = accelerator_mod.AcceleratorOptions
        self._pipeline_options_cls = pipeline_mod.PdfPipelineOptions
        self._input_format = base_models.InputFormat
        self._pdf_format_option = converter_mod.PdfFormatOption
        self._converter_cls = converter_mod.DocumentConverter
        self.device = device

    def _build_options(self):  # type: ignore[override]
        device_name = self.device.lower()
        try:
            device_enum = self._accelerator_device[device_name.upper()]
        except KeyError:
            device_enum = self._accelerator_device.AUTO
        accel = self._accelerator_options_cls(device=device_enum)
        pipeline_opts = self._pipeline_options_cls(accelerator=accel)
        return accel, pipeline_opts

    def convert(self, pdf_path: Path) -> str:
        accel, pipeline_opts = self._build_options()
        converter = self._converter_cls(
            format_options={self._input_format.PDF: self._pdf_format_option(pipeline_options=pipeline_opts)}
        )
        try:
            LOGGER.info("Converting %s with docling on %s", pdf_path, accel.device)
            result = converter.convert(pdf_path)
            doc = result.document
            if hasattr(doc, "as_markdown"):
                return doc.as_markdown()
            return "".join(page.to_markdown() for page in doc.pages)
        except Exception as exc:  # pragma: no cover - depends on docling runtime
            raise BackendConversionError(f"docling failed for {pdf_path}") from exc


registry.register(DoclingBackend.name, DoclingBackend)

__all__ = ["DoclingBackend"]
