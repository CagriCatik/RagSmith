"""Configuration for src."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RagSmithConfig:
    backend: str = "docling"  # or "pymupdf4llm" or "markitdown" or "ocr"
    reflow: bool = True
    split_sections: bool = False
    overwrite: bool = False
    ocr_languages: list[str] = field(default_factory=lambda: ["en"])
    ocr_device: Literal["auto", "cpu", "cuda", "mps"] = "auto"
    ocr_dpi: int = 300
    ocr_start_page: int | None = None
    ocr_end_page: int | None = None


__all__ = ["RagSmithConfig"]
