"""Command line interface entrypoint."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from ragsmith.app import PdfMarkdownApp
from ragsmith.config import RagSmithConfig
from ragsmith.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert PDFs to RAG-ready Markdown")
    parser.add_argument("pdf_files", nargs="+", type=Path, help="Input PDF files")
    parser.add_argument("--backend", choices=["markitdown", "pymupdf4llm", "docling"], default="docling")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to write markdown files")
    parser.add_argument("--split-sections", dest="split_sections", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--reflow", dest="reflow", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--overwrite", dest="overwrite", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging()
    config = RagSmithConfig(
        backend=args.backend,
        reflow=args.reflow,
        split_sections=args.split_sections,
        overwrite=args.overwrite,
    )
    app = PdfMarkdownApp(config)
    app.convert_and_write(args.pdf_files, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
