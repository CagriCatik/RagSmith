"""RAG-oriented Markdown processing.

This module provides utilities to post-process Markdown for retrieval-augmented
generation (RAG) use cases.

The main goals are:

- Remove layout and boilerplate noise via strip_noise_lines.
- Reflow hard-wrapped paragraphs into single logical lines to improve chunking.
- Preserve structural Markdown constructs (headings, lists, blockquotes,
  tables, horizontal rules, and fenced code blocks).
"""

from __future__ import annotations

import re
from typing import Iterable, List

from ragsmith.processing.cleaning import normalize_blank_lines, strip_noise_lines


# ---------------------------------------------------------------------------
# Line classification helpers
# ---------------------------------------------------------------------------


def _is_fence(line: str) -> bool:
    """Return True if the line starts or ends a fenced code block."""
    stripped = line.lstrip()
    return stripped.startswith("```")


def _is_list_line(line: str) -> bool:
    """Return True if the line looks like a Markdown list item.

    Supported forms:
        - "- item"
        - "* item"
        - "+ item"
        - "1. item"
        - "1) item"
    Nested list items (with leading spaces) are also detected.
    """
    stripped = line.lstrip()

    if stripped.startswith(("- ", "* ", "+ ")):
        return True

    if re.match(r"\d+\.\s", stripped):
        return True

    if re.match(r"\d+\)\s", stripped):
        return True

    return False


def _is_horizontal_rule(line: str) -> bool:
    """Return True if the line is a Markdown horizontal rule.

    Examples:
        ---
        ***
        ___
    with optional surrounding whitespace.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # A simple heuristic: only a small set of rule characters,
    # length at least 3, and at least 3 of the main rule chars.
    if not set(stripped) <= {"-", "*", "_"}:
        return False

    return len(stripped) >= 3


def _is_table_line(line: str) -> bool:
    """Return True if the line looks like part of a Markdown table.

    Heuristics:
        - Contains at least one '|' character.
        - Not a fenced code line.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if _is_fence(stripped):
        return False
    return "|" in stripped


def _is_special_line(line: str) -> bool:
    """Return True if the line should not be merged into a paragraph.

    This covers:
        - Headings (# ...)
        - List items (-, *, +, numbered)
        - Blockquotes (> ...)
        - Horizontal rules (---, ***, ___)
        - Table rows / separators (lines with '|')
    """
    stripped = line.lstrip()
    if not stripped:
        return False

    if stripped.startswith("#"):
        return True

    if _is_list_line(line):
        return True

    if stripped.startswith(">"):
        return True

    if _is_horizontal_rule(stripped):
        return True

    if _is_table_line(stripped):
        return True

    return False


# ---------------------------------------------------------------------------
# Paragraph merging
# ---------------------------------------------------------------------------


def _merge_paragraph(lines: Iterable[str]) -> str:
    """Merge a sequence of wrapped lines into a single logical paragraph.

    - Leading and trailing whitespace on each line is stripped.
    - Empty lines are ignored.
    - Hyphenated line breaks are merged without inserting an extra space,
      but only when the hyphen appears directly after a non-space character.
    """
    parts = [part.strip() for part in lines if part.strip()]
    merged = ""

    for part in parts:
        if not merged:
            merged = part
            continue

        # Handle hyphenated line-breaks ("inter-\nnational").
        if merged.endswith("-") and not merged.endswith(" -") and re.match(
            r"^[A-Za-z0-9]", part
        ):
            merged = merged[:-1] + part
        else:
            merged = f"{merged} {part}"

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def reflow_markdown_paragraphs(text: str) -> str:
    """Merge wrapped paragraphs while preserving block structures and code fences.

    The algorithm:

        1. Scan line-by-line.
        2. Outside fenced code blocks:
            - Accumulate "plain text" lines into a paragraph buffer.
            - Flush the buffer whenever encountering:
                * an empty line,
                * a structural Markdown line (headings, lists, blockquotes,
                  horizontal rules, tables),
                * a fenced code block fence.
        3. Inside fenced code blocks:
            - Emit lines verbatim.
        4. After processing, collapse blank lines using normalize_blank_lines
           with max_consecutive == 2.

    This gives RAG-friendly text where logical paragraphs are on single lines,
    but document structure is intact.
    """
    if not text:
        return ""

    lines = text.splitlines()
    output: List[str] = []
    paragraph: List[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        if paragraph:
            output.append(_merge_paragraph(paragraph))
            paragraph.clear()

    for raw in lines:
        line = raw.rstrip("\n\r")
        stripped = line.strip()

        # Fenced code block boundaries.
        if _is_fence(line):
            flush_paragraph()
            in_code_block = not in_code_block
            output.append(line.rstrip())
            continue

        if in_code_block:
            # Preserve code verbatim.
            output.append(line.rstrip())
            continue

        # Blank line: paragraph boundary.
        if stripped == "":
            flush_paragraph()
            # Keep a single blank marker; later normalization will cap runs.
            if output and output[-1] != "":
                output.append("")
            continue

        # Structural lines: do not merge with neighbors.
        if _is_special_line(line):
            flush_paragraph()
            output.append(line.rstrip())
            continue

        # Part of a running paragraph.
        paragraph.append(line)

    flush_paragraph()

    # Normalize blank lines to a maximum of two in a row.
    reflowed = "\n".join(output)
    return normalize_blank_lines(reflowed, max_consecutive=2)


def process_for_rag(markdown_text: str, *, reflow: bool = True) -> str:
    """Clean and normalize Markdown for RAG ingestion.

    Steps:
        1. strip_noise_lines removes boilerplate, headers/footers, and layout noise.
        2. If reflow is True, reflow_markdown_paragraphs merges wrapped prose lines.
           Otherwise, only blank-line normalization is applied.
        3. normalize_blank_lines is run at the end to ensure consistent spacing.
    """
    cleaned = strip_noise_lines(markdown_text)

    if reflow:
        cleaned = reflow_markdown_paragraphs(cleaned)
    else:
        cleaned = normalize_blank_lines(cleaned)

    return normalize_blank_lines(cleaned)


__all__ = ["reflow_markdown_paragraphs", "process_for_rag"]
