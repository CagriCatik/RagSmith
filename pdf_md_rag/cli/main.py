"""Command line interface for pdf_md_rag."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pdf_md_rag.app import PdfMarkdownApp
from pdf_md_rag.config import AppConfig, BackendConfig
from pdf_md_rag.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert PDFs to RAG-ready Markdown")
    parser.add_argument("pdfs", nargs="+", type=Path, help="Input PDF files")
    parser.add_argument("--backend", choices=["markitdown", "pymupdf4llm", "docling"], default="docling")
    parser.add_argument("--output-dir", type=Path, default=Path("./output"))
    parser.add_argument("--split-sections", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--reflow", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging()
    backend_cfg = BackendConfig(name=args.backend)
    app_cfg = AppConfig(
        backend=backend_cfg,
        default_output_dir=args.output_dir,
        default_reflow=args.reflow,
        default_split_sections=args.split_sections,
        overwrite=args.overwrite,
    )
    app = PdfMarkdownApp(app_cfg)
    app.convert_and_write(args.pdfs, args.output_dir, split_sections=args.split_sections, reflow=args.reflow)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
