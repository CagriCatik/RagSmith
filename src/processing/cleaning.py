"""Markdown cleaning utilities.

This module provides helpers for cleaning noisy Markdown text that often comes
from PDF extraction, OCR passthroughs, or web scraping.

Public API:

- strip_noise_lines(text: str) -> str
- normalize_blank_lines(text: str, max_consecutive: int = 2) -> str
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List


# ---------------------------------------------------------------------------
# Configuration and patterns
# ---------------------------------------------------------------------------

_BOILERPLATE_SNIPPETS = [
    "all rights reserved",
    "no part of this publication",
    "reprinted with permission",
    "copyright",
    "isbn",
    "printed in",
    "distributed by",
    "unauthorized reproduction",
    "duplication prohibited",
]

_PAGE_NUMBER_PATTERNS = [
    re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^(chapter\s+)?\d+$", re.IGNORECASE),
    re.compile(r"^[ivxlcdm]+$", re.IGNORECASE),  # roman numerals
]

# Repetition thresholds for header/footer detection.
_MIN_HEADER_FOOTER_REPETITIONS = 3
_MIN_HEADER_FOOTER_FRACTION = 0.02

# Character sets and thresholds for layout-noise heuristics.
_RULER_CHARS = set("-_.=*~+:#|")
_TOC_PUNCT_CHARS = set(".-|")
_MIN_RULER_PUNCT_RATIO = 0.7
_MIN_TOC_PUNCT_RATIO = 0.5
_MAX_TOC_ALPHA_RATIO = 0.25


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalized_line(line: str) -> str:
    """Canonical representation of a line for counting."""
    return line.strip().lower()


def _is_page_number(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.match(stripped) for pattern in _PAGE_NUMBER_PATTERNS)


def _is_boilerplate(line: str, boilerplate: Iterable[str]) -> bool:
    lowered = line.lower()
    return any(snippet in lowered for snippet in boilerplate)


def _is_fence(line: str) -> bool:
    """True if the line starts a fenced code block."""
    stripped = line.lstrip()
    return stripped.startswith("```")


def _char_stats(line: str) -> tuple[float, float, float]:
    """Return (punct_ratio, alpha_ratio, digit_ratio) for a stripped line."""
    stripped = line.strip()
    if not stripped:
        return 0.0, 0.0, 0.0

    total = len(stripped)
    punct = sum(ch in _RULER_CHARS for ch in stripped)
    alpha = sum(ch.isalpha() for ch in stripped)
    digit = sum(ch.isdigit() for ch in stripped)

    return punct / total, alpha / total, digit / total


def _is_ruler_line(line: str) -> bool:
    """Detect lines that are basically visual rulers.

    Example:
        "------------------------"
        "..... ..... ..... ..... "
        "====*====*===="
    """
    stripped = line.strip()
    if not stripped:
        return False

    punct_ratio, alpha_ratio, _ = _char_stats(stripped)
    if alpha_ratio > 0:
        return False
    return punct_ratio >= _MIN_RULER_PUNCT_RATIO


def _is_layout_toc_border(line: str) -> bool:
    """Detect broken table-of-contents border lines.

    These usually mix spaces with ., -, and | and have almost no text.
    Example:
        "---------------------|.........................|"
    """
    stripped = line.strip()
    if not stripped:
        return False

    punct_ratio, alpha_ratio, _ = _char_stats(stripped)
    if not any(ch in _TOC_PUNCT_CHARS for ch in stripped):
        return False

    # High punctuation, low alpha characters.
    if punct_ratio >= _MIN_TOC_PUNCT_RATIO and alpha_ratio <= _MAX_TOC_ALPHA_RATIO:
        return True

    return False


def _is_toc_noise(line: str) -> bool:
    """Detect lines that look like TOC filler or dangling page numbers.

    We intentionally keep actual section titles, but drop the "...... 3" style
    fillers that are common in PDF exports.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Dot leaders followed by a page number at the end of the line.
    if re.search(r"\.{3,}\s*\d+\s*$", stripped):
        return True

    # A lone number on the line right after dot leaders often appears as a
    # continuation. This is a weaker heuristic, so require no letters.
    if stripped.isdigit() and len(stripped) <= 3:
        return True

    return False


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def strip_noise_lines(text: str) -> str:
    """Remove repeated headers/footers, layout noise, and boilerplate lines.

    The cleaning steps are:

        1. Detect repeated header/footer lines using frequency analysis.
        2. Drop page numbers and boilerplate lines.
        3. Drop layout noise (rulers, TOC borders, dot-leader lines).
        4. Preserve fenced code blocks verbatim.

    The order of lines is preserved for the remaining content.
    """

    if not text:
        return ""

    lines: List[str] = text.splitlines()

    # Header/footer detection based on normalized non-empty lines.
    normalized_nonempty = [_normalized_line(line) for line in lines if line.strip()]
    counts = Counter(normalized_nonempty)
    total_lines = max(len(lines), 1)

    noise_candidates = {
        candidate
        for candidate, count in counts.items()
        if count >= _MIN_HEADER_FOOTER_REPETITIONS
        and (count / total_lines) > _MIN_HEADER_FOOTER_FRACTION
    }

    cleaned: List[str] = []
    in_code_block = False

    for raw in lines:
        line = raw.rstrip("\n\r")
        stripped = line.strip()

        # Track code fences and preserve them.
        if _is_fence(line):
            in_code_block = not in_code_block
            cleaned.append(line.rstrip())
            continue

        if not stripped:
            cleaned.append("")
            continue

        if not in_code_block:
            normalized_line = _normalized_line(line)

            # 1) Repeated headers / footers.
            if normalized_line in noise_candidates:
                continue

            # 2) Explicit patterns: page numbers, boilerplate.
            if _is_page_number(line):
                continue
            if _is_boilerplate(line, _BOILERPLATE_SNIPPETS):
                continue

            # 3) Layout noise: rulers, TOC borders, dot leader junk.
            if _is_ruler_line(line):
                continue
            if _is_layout_toc_border(line):
                continue
            if _is_toc_noise(line):
                continue

        cleaned.append(line.rstrip())

    return "\n".join(cleaned)


def normalize_blank_lines(text: str, max_consecutive: int = 2) -> str:
    """Collapse sequences of blank lines.

    Leading and trailing blank lines are removed from the final result.
    Blank lines inside fenced code blocks are left unchanged.
    """

    if not text:
        return ""

    if max_consecutive < 0:
        max_consecutive = 0

    output: List[str] = []
    blank_count = 0
    in_code_block = False

    for raw in text.splitlines():
        line = raw.rstrip("\n\r")

        if _is_fence(line):
            in_code_block = not in_code_block
            blank_count = 0
            output.append(line.rstrip())
            continue

        if in_code_block:
            output.append(line.rstrip())
            continue

        if line.strip() == "":
            blank_count += 1
            if blank_count <= max_consecutive:
                output.append("")
        else:
            blank_count = 0
            output.append(line.rstrip())

    # Strip leading / trailing empty lines.
    result_lines = output
    start = 0
    end = len(result_lines)

    while start < end and result_lines[start].strip() == "":
        start += 1
    while end > start and result_lines[end - 1].strip() == "":
        end -= 1

    return "\n".join(result_lines[start:end])


__all__ = ["strip_noise_lines", "normalize_blank_lines"]
