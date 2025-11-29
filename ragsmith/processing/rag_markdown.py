"""RAG-oriented Markdown processing."""
from __future__ import annotations

import re
from typing import List

from ragsmith.processing.cleaning import normalize_blank_lines, strip_noise_lines


def _is_special_line(line: str) -> bool:
    stripped = line.lstrip()
    return (
        stripped.startswith("#")
        or stripped.startswith("- ")
        or stripped.startswith("* ")
        or stripped.startswith("+ ")
        or re.match(r"\d+\.\s", stripped) is not None
        or stripped.startswith(">")
    )


def reflow_markdown_paragraphs(text: str) -> str:
    """Merge wrapped paragraphs while preserving block structures and code fences."""
    lines = text.splitlines()
    output: List[str] = []
    paragraph: List[str] = []
    in_code_block = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            merged = " ".join(part.strip() for part in paragraph if part.strip())
            output.append(merged)
            paragraph = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            in_code_block = not in_code_block
            output.append(line)
            continue

        if in_code_block:
            output.append(line)
            continue

        if stripped == "":
            flush_paragraph()
            if output and output[-1] != "":
                output.append("")
            continue

        if _is_special_line(line):
            flush_paragraph()
            output.append(line.rstrip())
            continue

        paragraph.append(line)

    flush_paragraph()
    cleaned = []
    blank_count = 0
    for line in output:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip() + "\n"


def process_for_rag(markdown_text: str, *, reflow: bool = True) -> str:
    cleaned = strip_noise_lines(markdown_text)
    if reflow:
        cleaned = reflow_markdown_paragraphs(cleaned)
    else:
        cleaned = normalize_blank_lines(cleaned)
    return cleaned


__all__ = ["reflow_markdown_paragraphs", "process_for_rag"]
