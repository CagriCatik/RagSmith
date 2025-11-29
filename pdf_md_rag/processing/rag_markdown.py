"""RAG-oriented Markdown processing functions."""
from __future__ import annotations

from pdf_md_rag.config import CleaningConfig
from pdf_md_rag.processing.cleaning import normalize_blank_lines, strip_noise_lines


def _should_preserve_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("#") or stripped.startswith(('-', '*', '+')) or stripped[:2].isdigit()


def reflow_markdown_paragraphs(text: str) -> str:
    """Merge wrapped paragraphs into single lines while respecting Markdown structure."""
    lines = text.splitlines()
    output: list[str] = []
    buffer: list[str] = []
    in_code_block = False

    def flush_buffer():
        if buffer:
            output.append(" ".join(buffer).strip())
            buffer.clear()

    for line in lines:
        if line.strip().startswith("```"):
            flush_buffer()
            in_code_block = not in_code_block
            output.append(line)
            continue

        if in_code_block:
            output.append(line)
            continue

        if not line.strip():
            flush_buffer()
            output.append("")
            continue

        if _should_preserve_line(line) or line.lstrip().startswith(">"):
            flush_buffer()
            output.append(line.rstrip())
            continue

        if line.rstrip().endswith("-"):
            buffer.append(line.rstrip()[:-1])
        else:
            buffer.append(line.strip())

    flush_buffer()
    return "\n".join(output)


def process_for_rag(markdown_text: str, *, reflow: bool = True, cleaning: CleaningConfig | None = None) -> str:
    """Run the full RAG processing pipeline."""
    cleaned = strip_noise_lines(markdown_text, cleaning)
    cleaned = normalize_blank_lines(cleaned)
    if reflow:
        cleaned = reflow_markdown_paragraphs(cleaned)
    return cleaned


__all__ = ["reflow_markdown_paragraphs", "process_for_rag"]
