"""Configuration for RagSmith."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RagSmithConfig:
    backend: str = "docling"  # or "pymupdf4llm" or "markitdown"
    reflow: bool = True
    split_sections: bool = False
    overwrite: bool = False


__all__ = ["RagSmithConfig"]
