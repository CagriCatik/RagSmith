"""Markdown cleaning utilities."""
from __future__ import annotations

import re
from collections import Counter
from typing import Iterable


_DEFAULT_BOILERPLATE = [
    "all rights reserved",
    "no part of this publication",
    "reprinted with permission",
    "copyright",
    "isbn",
    "printed in",
]

_PAGE_NUMBER_PATTERNS = [
    re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^\d+$"),
]


def _is_page_number(line: str) -> bool:
    return any(pattern.match(line.strip()) for pattern in _PAGE_NUMBER_PATTERNS)


def _is_boilerplate(line: str, boilerplate: Iterable[str]) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in boilerplate)


def strip_noise_lines(markdown_text: str) -> str:
    """Remove common headers/footers, page numbers, and boilerplate."""
    lines = markdown_text.splitlines()
    normalized = [line.strip().lower() for line in lines if line.strip()]
    counts = Counter(normalized)
    noise_candidates = {text for text, count in counts.items() if count >= 3 and count / max(len(lines), 1) > 0.02}

    cleaned_lines: list[str] = []
    for line in lines:
        normalized_line = line.strip().lower()
        if not line.strip():
            cleaned_lines.append("")
            continue
        if normalized_line in noise_candidates:
            continue
        if _is_page_number(line):
            continue
        if _is_boilerplate(line, _DEFAULT_BOILERPLATE):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def normalize_blank_lines(text: str, max_consecutive: int = 2) -> str:
    """Collapse blank lines to a maximum number of consecutive occurrences."""
    output: list[str] = []
    blank_count = 0
    for line in text.splitlines():
        if line.strip() == "":
            blank_count += 1
            if blank_count <= max_consecutive:
                output.append("")
        else:
            blank_count = 0
            output.append(line.rstrip())
    return "\n".join(output).strip() + "\n"


__all__ = ["strip_noise_lines", "normalize_blank_lines"]
