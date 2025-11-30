"""Command line interface entrypoint."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ragsmith.app import PdfMarkdownApp
from ragsmith.config import RagSmithConfig
from ragsmith.errors import BackendConversionError, BackendNotAvailableError, OutputWriteError, format_exception_chain
from ragsmith.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert PDFs to RAG-ready Markdown")
    parser.add_argument("pdf_files", nargs="+", type=Path, help="Input PDF files")
    parser.add_argument(
        "--backend",
        choices=["markitdown", "pymupdf4llm", "docling", "ocr"],
        default=RagSmithConfig().backend,
        help="Conversion backend",
    )
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to write markdown files")
    parser.add_argument("--split-sections", dest="split_sections", action="store_true", help="Split output by top-level headings")
    parser.add_argument("--no-split-sections", dest="split_sections", action="store_false")
    parser.set_defaults(split_sections=RagSmithConfig().split_sections)
    parser.add_argument("--no-reflow", dest="reflow", action="store_false", help="Disable paragraph reflow")
    parser.add_argument("--reflow", dest="reflow", action="store_true")
    parser.set_defaults(reflow=RagSmithConfig().reflow)
    parser.add_argument("--overwrite", dest="overwrite", action="store_true", help="Overwrite existing markdown files")
    parser.add_argument("--no-overwrite", dest="overwrite", action="store_false")
    parser.set_defaults(overwrite=RagSmithConfig().overwrite)
    parser.add_argument(
        "--ocr-lang",
        nargs="+",
        default=RagSmithConfig().ocr_languages,
        help="Languages for EasyOCR (e.g. --ocr-lang en de)",
    )
    parser.add_argument(
        "--ocr-device",
        choices=["auto", "cpu", "cuda", "mps"],
        default=RagSmithConfig().ocr_device,
        help="Device for OCR (auto, cpu, cuda, or mps)",
    )
    parser.add_argument(
        "--ocr-dpi",
        type=int,
        default=RagSmithConfig().ocr_dpi,
        help="Render DPI for OCR rasterization (default: 300)",
    )
    parser.add_argument(
        "--ocr-start-page",
        type=int,
        default=RagSmithConfig().ocr_start_page,
        help="1-based first page to OCR (default: 1)",
    )
    parser.add_argument(
        "--ocr-end-page",
        type=int,
        default=RagSmithConfig().ocr_end_page,
        help="1-based last page to OCR (default: last)",
    )
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
        ocr_languages=list(args.ocr_lang),
        ocr_device=args.ocr_device,
        ocr_dpi=args.ocr_dpi,
        ocr_start_page=args.ocr_start_page,
        ocr_end_page=args.ocr_end_page,
    )
    try:
        app = PdfMarkdownApp(config)
        results = app.convert_and_write(args.pdf_files, output_dir=args.output_dir)

        for input_path, outputs in results.items():
            print(f"{input_path} →")
            for output in outputs:
                print(f"  - {output}")
        return 0
    except (BackendConversionError, BackendNotAvailableError, OutputWriteError) as exc:
        print(format_exception_chain(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
