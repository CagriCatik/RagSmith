"""Application configuration for pdf_md_rag."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import List


@dataclass
class BackendConfig:
    """Configuration for selecting and tuning backends."""

    name: str = "docling"
    enable_pymupdf_fallback: bool = True
    enable_docling_fallback: bool = True
    docling_device: str = "auto"  # auto, cpu, cuda, mps


@dataclass
class CleaningConfig:
    """Configuration for noise removal and regexes."""

    page_number_patterns: List[re.Pattern[str]] = field(
        default_factory=lambda: [
            re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
            re.compile(r"^\d+\s*/\s*\d+$"),
            re.compile(r"^\d+$"),
        ]
    )
    boilerplate_substrings: List[str] = field(
        default_factory=lambda: [
            "all rights reserved",
            "no part of this publication",
            "reprinted with permission",
            "copyright",
            "isbn",
            "printed in",
        ]
    )


@dataclass
class AppConfig:
    """Top-level configuration shared across the app."""

    backend: BackendConfig = field(default_factory=BackendConfig)
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    default_output_dir: Path | None = None
    default_reflow: bool = True
    default_split_sections: bool = False
    overwrite: bool = False


DEFAULT_CONFIG = AppConfig()
