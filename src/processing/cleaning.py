"""Cleaning utilities for RAG-friendly Markdown."""
from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from src.config import CleaningConfig


def find_repeated_lines(
    lines: Iterable[str],
    *,
    min_repeats: int = 3,
    min_len: int = 5,
    max_len: int = 120,
) -> set[str]:
    """Find short lines that repeat at least ``min_repeats`` times."""
    norm_counter: Counter[str] = Counter()

    for line in lines:
        s = line.strip()
        if len(s) < min_len or len(s) > max_len:
            continue
        if s.startswith("#"):
            continue
        norm_counter[s] += 1

    return {text for text, cnt in norm_counter.items() if cnt >= min_repeats}


def strip_noise_lines(markdown_text: str, config: CleaningConfig | None = None) -> str:
    """Remove repeated lines, page numbers, and boilerplate content."""
    cfg = config or CleaningConfig()
    lines = markdown_text.splitlines()
    repeated = find_repeated_lines(lines)

    cleaned_lines: List[str] = []
    for line in lines:
        raw = line.rstrip("\n")
        stripped = raw.strip()

        if not stripped:
            cleaned_lines.append(raw)
            continue

        if stripped in repeated:
            continue

        if any(pattern.match(stripped) for pattern in cfg.page_number_patterns):
            continue

        lowered = stripped.lower()
        if any(token in lowered for token in cfg.boilerplate_substrings):
            continue

        cleaned_lines.append(raw)

    return "\n".join(cleaned_lines)


def normalize_blank_lines(text: str, *, max_consecutive: int = 2) -> str:
    """Normalize blank lines to avoid overly sparse output."""
    lines = text.splitlines()
    cleaned: list[str] = []
    blank_count = 0

    for line in lines:
        if line.strip():
            blank_count = 0
            cleaned.append(line)
        else:
            blank_count += 1
            if blank_count <= max_consecutive:
                cleaned.append("")

    return "\n".join(cleaned)


__all__ = ["strip_noise_lines", "find_repeated_lines", "normalize_blank_lines"]
