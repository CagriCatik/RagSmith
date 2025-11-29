# RagSmith

RagSmith converts PDFs to RAG-ready Markdown with a simple Python API, a CLI, and a PyQt6 desktop app. It bundles multiple conversion backends and post-processing tools for cleaning, reflowing, and optionally splitting Markdown into sections.

## Project layout

```
RagSmith/
  ragsmith/             # package (app, backends, processing, cli, ui)
  requirements.txt
  pyproject.toml
  README.md
```

## Features

- Multiple PDF → Markdown backends: Docling (GPU-aware), PyMuPDF4LLM, and MarkItDown.
- Cleaning pipeline that removes repeated headers/footers, page numbers, and boilerplate noise.
- Optional paragraph reflow that preserves Markdown structure.
- Optional splitting by top-level headings for chunked retrieval workflows.
- CLI and PyQt6 GUI built on the same `PdfMarkdownApp` orchestration layer.

## Installation

Create and activate a virtual environment, then install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For Docling GPU acceleration, install a CUDA-capable `torch` build and choose the `cuda` device when configuring the Docling backend.

## CLI usage

Convert one or more PDFs from the command line:

```bash
python -m ragsmith.cli.main \
  --backend docling \
  --output-dir ./output \
  --split-sections \
  --reflow \
  path/to/file1.pdf path/to/file2.pdf
```

Key options:

- `--backend {markitdown,pymupdf4llm,docling}`: choose the conversion backend.
- `--output-dir PATH`: destination directory for Markdown (created if missing).
- `--split-sections` / `--no-split-sections`: write one Markdown file per top-level heading.
- `--reflow` / `--no-reflow`: enable or disable paragraph reflow.
- `--overwrite`: allow replacing existing Markdown files.

After installation you can also use the entry point:

```bash
ragsmith-cli ...
```

## GUI usage

Launch the PyQt6 application:

```bash
python -m ragsmith.ui.application
```

or via the entry point:

```bash
ragsmith-gui
```

The GUI lets you pick PDFs, choose an output directory, select a backend, and toggle overwrite, reflow, and split options.

## Library usage

Use the orchestration layer directly:

```python
from pathlib import Path
from ragsmith import PdfMarkdownApp, RagSmithConfig

config = RagSmithConfig(backend="docling", reflow=True, split_sections=True, overwrite=False)
app = PdfMarkdownApp(config)
app.convert_and_write([Path("paper.pdf")], output_dir=Path("./output"))
```

- `convert_file(path)` returns Markdown for a single PDF.
- `convert_files(paths)` returns a mapping of `Path` to Markdown string.
- `convert_and_write(paths, output_dir=None)` writes `.md` files next to the PDFs or to `output_dir`.

## Development

- Run `python -m compileall ragsmith` to verify syntax.
- Logging is configured via `ragsmith.logging_config.configure_logging` and uses the `RAGSMITH_LOG_LEVEL` environment variable when set.
- Custom exceptions (`BackendNotAvailableError`, `BackendConversionError`, `OutputWriteError`) describe dependency or I/O issues.
