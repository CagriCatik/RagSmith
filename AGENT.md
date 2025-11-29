You are an expert Python engineer, software architect, and RAG (Retrieval-Augmented Generation) practitioner.

Goal:
Design and implement a well-structured, production-quality Python application that provides a GUI and programmatic API to convert technical PDFs into high-quality Markdown optimized for RAG. The existing prototype is a single-file PyQt6 app with multiple backends (markitdown, pymupdf4llm, docling), some cleaning heuristics, and options for splitting Markdown. Your job is to redesign and reimplement this as a clean, extensible codebase.

High level requirements:

1) Core capabilities

- Convert one or more PDF files into Markdown.
- Support multiple backends:
  - markitdown
  - pymupdf4llm (with pymupdf-layout if available)
  - docling (with GPU acceleration when available)
- Provide a RAG-oriented postprocessing pipeline:
  - Remove repeated headers and footers.
  - Remove page numbers and boilerplate lines.
  - Reflow paragraphs into single lines (without breaking code blocks, lists, headings, or blockquotes).
  - Optionally split Markdown into sections by top-level headings (# ...).
- Provide:
  - A PyQt6 GUI for interactive use.
  - A clean Python library API (importable module).
  - A small CLI entry point for batch conversions.

2) Architecture and structure

Use a package-based layout similar to:

pdf_md_rag/
    __init__.py
    config.py
    logging_config.py
    backends/
        __init__.py
        base.py
        markitdown_backend.py
        pymupdf_backend.py
        docling_backend.py
    processing/
        __init__.py
        cleaning.py
        rag_markdown.py
        splitting.py
    ui/
        __init__.py
        main_window.py
        application.py
    cli/
        __init__.py
        main.py
    app.py  (high-level facade)

Implement the following design principles:

- backends.base:
  - Define an abstract base class PdfToMarkdownBackend with a method:
    - convert(pdf_path: Path) -> str
  - Each backend implementation is responsible only for:
    - Invoking its library (markitdown, pymupdf4llm, docling).
    - Handling specific errors and fallbacks.
    - Not doing any RAG-oriented cleaning (that belongs to processing).

- backends.markitdown_backend:
  - Concrete implementation using MarkItDown().
  - Implement convert() with robust error handling.

- backends.pymupdf_backend:
  - Concrete implementation using pymupdf4llm.to_markdown().
  - Use pymupdf-layout if installed (activate layout analyzer).
  - Handle the known min() empty-sequence bug by raising a custom BackendError or falling back to markitdown (configurable).

- backends.docling_backend:
  - Concrete implementation using Docling DocumentConverter.
  - Encapsulate configuration of AcceleratorOptions and PdfPipelineOptions.
  - Default to AUTO device; allow configuration for CUDA, CPU, or MPS.
  - Cleanly handle missing torch / GPU; if docling cannot load, raise a specific BackendNotAvailableError.

1) Processing pipeline for RAG markdown

- processing.cleaning:
  - Implement functions:
    - strip_noise_lines(markdown_text: str) -> str
      - Remove repeated short lines (headers/footers) using a global frequency heuristic.
      - Remove page numbers via regexes.
      - Remove known boilerplate phrases (copyright, ISBN, etc.).
    - normalize_blank_lines(text: str, max_consecutive: int = 2) -> str
  - All functions should be pure and easily testable.

- processing.rag_markdown:
  - Implement:
    - reflow_markdown_paragraphs(text: str) -> str
      - Preserve code blocks fenced by ```.
      - Preserve headings, lists, numbered lists, and blockquotes.
      - Merge wrapped paragraphs into single lines.
      - Use clean heuristics for hyphenation and whitespace.
    - process_for_rag(markdown_text: str, *, reflow: bool = True) -> str
      - Call strip_noise_lines, then reflow_markdown_paragraphs if enabled.

- processing.splitting:
  - Implement:
    - split_by_top_level_headings(markdown_text: str) -> list[tuple[str, str]]
      - Split on lines starting with "# ".
      - Include the heading in each section.
      - Return (title, section_markdown) tuples.
    - slugify(text: str) -> str
      - Safe for file names.

4) Configuration and logging

- config.py:
  - Central place for default settings:
    - Default backend name (e.g., "docling", "pymupdf4llm", "markitdown").
    - Regex patterns for page numbers.
    - Boilerplate substrings list.
    - Whether to enable fallbacks (pymupdf -> markitdown, docling -> markitdown).
  - Provide typed dataclasses or Pydantic models for configuration objects.

- logging_config.py:
  - Set up a standard logging configuration:
    - Named loggers: "pdf_md_rag", "pdf_md_rag.backends", "pdf_md_rag.processing".
    - INFO level by default, with easy override via environment variable.
  - Optionally reduce external library noise (e.g. huggingface_hub Xet warnings).

5) Application and APIs

- app.py:
  - Implement a high-level facade class PdfMarkdownApp that:
    - Accepts configuration.
    - Selects and instantiates the backend.
    - Exposes methods:
      - convert_file(pdf_path: Path) -> str
      - convert_files(pdf_paths: list[Path]) -> dict[Path, str]
      - convert_and_write(pdf_paths: list[Path], output_dir: Path, split_sections: bool) -> None
    - Internally:
      - Uses the backend to get raw markdown.
      - Passes it through process_for_rag.
      - Optionally splits into sections and writes multiple files.

6) CLI

- cli/main.py:
  - Implement a click or argparse based CLI, e.g. python -m pdf_md_rag.cli:
    - Options:
      - --backend {markitdown,pymupdf4llm,docling}
      - --output-dir PATH
      - --split-sections / --no-split-sections
      - --reflow / --no-reflow
      - --overwrite / --no-overwrite
    - Arguments:
      - One or more PDF file paths
    - Uses PdfMarkdownApp under the hood.

7) PyQt6 GUI

- ui/main_window.py:
  - Implement a MainWindow class that:
    - Allows selecting multiple PDFs.
    - Allows selecting an output directory.
    - Provides a combo box to choose backend.
    - Provides checkboxes:
      - Overwrite existing .md
      - Reflow paragraphs
      - Split by top-level headings
    - Shows a progress bar and status messages.
    - Uses PdfMarkdownApp for the actual work.
    - Runs conversions in a background worker (QThread or QRunnable) to avoid blocking the UI thread.

- ui/application.py:
  - Implement a function run() that:
    - Creates QApplication.
    - Instantiates MainWindow.
    - Starts the event loop.

8) Error handling and UX

- Define custom exceptions in a dedicated module (e.g. errors.py):
  - BackendNotAvailableError
  - BackendConversionError
  - OutputWriteError
- Gracefully handle:
  - Missing backend libraries (pymupdf4llm, docling).
  - Torch / GPU issues in docling.
  - Individual file failures (log error, continue with others).

- In the GUI:
  - Show explanatory QMessageBox messages for errors (missing backend, conversion failure, write failure).
  - Still allow partial success when some files succeed and others fail.

9) GPU support for Docling

- In backends.docling_backend:
  - Accept a configuration specifying device:
    - "auto", "cpu", "cuda", "mps"
  - Use Docling AcceleratorOptions and PdfPipelineOptions to set this.
  - Document clearly how to use CUDA:
    - install torch with CUDA;
    - set device to "cuda" or leave "auto" with CUDA available.


Task:
Implement this full application and package layout. Generate the code for all modules described above, including:

Focus on clean architecture, extensibility, and correctness of the RAG-oriented Markdown processing pipeline.
