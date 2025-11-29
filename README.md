# RagSmith

RagSmith is a production-oriented toolkit for converting technical PDFs into RAG-ready Markdown. It ships with a PyQt6 desktop app, a small CLI, and a clean Python API that wrap multiple conversion backends (Docling, PyMuPDF4LLM, MarkItDown) and a RAG-focused post-processing pipeline.

## Features

- Multiple PDF ➜ Markdown backends: **Docling** (GPU-aware), **PyMuPDF4LLM** (with optional layout analysis), and **MarkItDown**.
- RAG-oriented cleaning pipeline that removes boilerplate, page numbers, and repeated headers/footers, with paragraph reflow that preserves Markdown structure.
- Optional splitting of Markdown into files by top-level headings for chunked retrieval workflows.
- PyQt6 GUI with background conversion worker, backend selection, output directory chooser, and configurable options.
- Simple CLI and Python API for batch processing.
- Configurable logging and safe output writing with overwrite protection.

## Installation

1. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) For Docling GPU acceleration, install a CUDA-enabled `torch` build and set the Docling device to `cuda`.

## CLI usage

Convert one or more PDFs from the command line:

```bash
python -m pdf_md_rag.cli --backend docling --output-dir ./output --split-sections --reflow path/to/file1.pdf path/to/file2.pdf
```

Key options:
- `--backend {markitdown,pymupdf4llm,docling}`: Choose conversion backend.
- `--output-dir PATH`: Destination directory for Markdown (created if missing).
- `--split-sections / --no-split-sections`: Write one Markdown file per top-level heading.
- `--reflow / --no-reflow`: Enable or disable paragraph reflow.
- `--overwrite / --no-overwrite`: Allow replacing existing Markdown files.

## GUI usage

Launch the desktop app:

```bash
python -m pdf_md_rag.ui.application
```

The GUI lets you pick multiple PDFs, choose an output directory, select a backend, and toggle reflow/splitting/overwrite options. Conversions run on a background thread and report progress.

## Library usage

Programmatically convert PDFs:

```python
from pathlib import Path
from pdf_md_rag import PdfMarkdownApp, AppConfig, BackendConfig

config = AppConfig(
    backend=BackendConfig(name="docling", docling_device="auto"),
    default_output_dir=Path("./output"),
    default_split_sections=True,
)
app = PdfMarkdownApp(config)
app.convert_and_write([Path("paper.pdf")], Path("./output"), split_sections=True)
```

## Configuration reference

- **Backends**: Controlled via `BackendConfig` (`name`, `enable_*_fallback`, `docling_device`).
- **Cleaning**: `CleaningConfig` defines regexes for page numbers and boilerplate detection.
- **App defaults**: `AppConfig` stores output directory, reflow and splitting defaults, and overwrite behavior.

## Development notes

- Logging is configured through `pdf_md_rag.logging_config.configure_logging`, honoring the `PDF_MD_RAG_LOG_LEVEL` environment variable.
- Custom exceptions (`BackendNotAvailableError`, `BackendConversionError`, `OutputWriteError`) help surface dependency or I/O issues cleanly.
- The package layout keeps backends, processing logic, CLI, and GUI decoupled for extensibility.

