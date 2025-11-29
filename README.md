# RagSmith

RagSmith converts PDFs to RAG-ready Markdown with a Python API, CLI, and PyQt6 GUI. It bundles multiple PDF→Markdown backends and a cleaning pipeline so you can prepare documents for retrieval workflows quickly.

## Project layout

```
RagSmith/
  ragsmith/            # package (app, backends, processing, cli, ui)
  README.md
  requirements.txt
  pyproject.toml
```

There is no extra `src/` nesting—the `ragsmith` package at the repository root is the code you import, run, and ship.

## Installation

Create a virtual environment and install the project in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Docling GPU acceleration requires a CUDA-capable `torch` build; otherwise Docling will fall back to CPU.

## Running the CLI

Convert one or more PDFs from the command line:

```bash
python -m ragsmith.cli.main \
  --backend docling \
  --output-dir ./output \
  --split-sections \
  --reflow \
  path/to/file1.pdf path/to/file2.pdf
```

After installation you can also use the entry point:

```bash
ragsmith-cli --backend pymupdf4llm --output-dir ./out my.pdf
```

Key options:

- `--backend {markitdown,pymupdf4llm,docling}`: choose the conversion backend.
- `--output-dir PATH`: directory where Markdown files are written.
- `--split-sections` / `--no-split-sections`: emit one Markdown file per top-level heading.
- `--reflow` / `--no-reflow`: toggle paragraph reflow.
- `--overwrite`: allow replacing existing Markdown files.

## Running the GUI

Launch the PyQt6 application:

```bash
python -m ragsmith.ui.application
```

or via the entry point:

```bash
ragsmith-gui
```

The GUI lets you add PDFs, choose an output directory, pick a backend, and toggle overwrite, reflow, and splitting options. Progress is shown while conversions run.

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
- Logging is configured via `ragsmith.logging_config.configure_logging` and honors the `RAGSMITH_LOG_LEVEL` environment variable when set.
- Custom exceptions (`BackendNotAvailableError`, `BackendConversionError`, `OutputWriteError`) describe dependency or I/O issues.
