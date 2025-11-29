"""Utilities for splitting Markdown into sections."""
from __future__ import annotations

import re
from typing import List, Tuple

SLUGIFY_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def slugify(text: str) -> str:
    slug = SLUGIFY_PATTERN.sub("-", text.strip().lower())
    return slug.strip("-")


def split_by_top_level_headings(markdown_text: str) -> List[tuple[str, str]]:
    lines = markdown_text.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    current_title = ""
    current_lines: List[str] = []

    for line in lines:
        if line.startswith("# "):
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = line[2:].strip() or "untitled"
            current_lines.append(line)
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return [(title, "\n".join(content).strip()) for title, content in sections if content]


__all__ = ["split_by_top_level_headings", "slugify"]
