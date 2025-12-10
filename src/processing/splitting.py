"""Utilities for splitting markdown into sections.

This module provides helpers for turning a markdown document into titled
sections, suitable for RAG-style indexing or navigation.

Public API:

- slugify(text: str) -> str
    Produce a URL/path friendly slug from a heading.

- split_by_top_level_headings(markdown_text: str) -> List[Tuple[str, str]]
    Split a document into sections based on top-level headings.

Top-level headings are detected using both:

- ATX H1 headings:    "# Title"
- Setext H1 headings: "Title" followed by a line of "===="
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

# "# Title" with optional leading whitespace, but exactly one "#".
_ATX_H1_PATTERN = re.compile(r"^[ \t]*#\s+(?P<title>.+?)\s*$")

# "====" underline (Setext-style H1). We only check this when a non-empty
# previous line exists.
_SETEXT_H1_UNDERLINE_PATTERN = re.compile(r"^=+$")

_DEFAULT_SECTION_TITLE = "section"
_DEFAULT_DOCUMENT_TITLE = "document"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert heading text into a URL/path friendly slug.

    Steps:
        1. Normalize Unicode and strip accents.
        2. Replace any run of non-alphanumeric characters with "-".
        3. Collapse multiple "-" into one and trim from both ends.
        4. Lowercase the result.
    """
    if not text:
        return ""

    # Normalize and strip accents.
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug.lower()


def split_by_top_level_headings(markdown_text: str) -> List[Tuple[str, str]]:
    """Split markdown into sections keyed by top-level heading titles.

    Each returned tuple is of the form:

        (title, section_text)

    where:

        - title is taken from the heading line (ATX or Setext).
        - section_text includes the heading itself and all lines up to (but not
          including) the next top-level heading.

    If the document has no detectable top-level heading, a single section
    ("document", markdown_text) is returned.
    """
    if not markdown_text:
        return [(_DEFAULT_DOCUMENT_TITLE, "")]

    lines = markdown_text.splitlines()
    sections: List[Tuple[str, str]] = []

    current_title = ""
    current_lines: List[str] = []

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ATX H1: "# Title"
        atx_match = _ATX_H1_PATTERN.match(line)
        if atx_match:
            # Close previous section, if any.
            if current_lines:
                sections.append(
                    (current_title or _DEFAULT_SECTION_TITLE, "\n".join(current_lines).strip())
                )
                current_lines = []

            current_title = atx_match.group("title").strip()
            current_lines.append(line.rstrip())
            i += 1
            continue

        # Setext H1:
        #   Title line
        #   =========
        if (
            stripped
            and i + 1 < n
            and _SETEXT_H1_UNDERLINE_PATTERN.match(lines[i + 1].strip())
        ):
            if current_lines:
                sections.append(
                    (current_title or _DEFAULT_SECTION_TITLE, "\n".join(current_lines).strip())
                )
                current_lines = []

            current_title = stripped
            # Include both title and underline lines in the section text.
            current_lines.append(line.rstrip())
            current_lines.append(lines[i + 1].rstrip())
            i += 2
            continue

        # Regular content line.
        current_lines.append(line.rstrip())
        i += 1

    # Flush trailing section.
    if current_lines:
        sections.append(
            (current_title or _DEFAULT_SECTION_TITLE, "\n".join(current_lines).strip())
        )

    if not sections:
        return [(_DEFAULT_DOCUMENT_TITLE, markdown_text)]

    return sections


__all__ = ["split_by_top_level_headings", "slugify"]
