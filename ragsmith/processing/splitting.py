"""Utilities for splitting markdown into sections."""
from __future__ import annotations

import re
from typing import List, Tuple


_HEADING_PATTERN = re.compile(r"^#\s+(?P<title>.+)")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return slug.lower()


def split_by_top_level_headings(markdown_text: str) -> List[Tuple[str, str]]:
    sections: List[Tuple[str, str]] = []
    current_title = ""
    current_lines: List[str] = []

    for line in markdown_text.splitlines():
        match = _HEADING_PATTERN.match(line)
        if match:
            if current_lines:
                sections.append((current_title or "section", "\n".join(current_lines).strip() + "\n"))
                current_lines = []
            current_title = match.group("title").strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title or "section", "\n".join(current_lines).strip() + "\n"))

    if not sections:
        return [("document", markdown_text)]

    return sections


__all__ = ["split_by_top_level_headings", "slugify"]
