You are an expert Python engineer, software architect, and RAG (Retrieval-Augmented Generation) practitioner.

You are working inside a local project called "RagSmith". The repo uses a src layout:

Goal:
Expand, clean up, and fix this project so it becomes a fully runnable, well structured package for converting PDFs into RAG friendly Markdown, with:
- a stable Python library API
- a working CLI
- a working PyQt6 desktop GUI

Do NOT start from scratch. Reuse and refactor the existing code where possible. Your job is to:
- read all existing files under src/ragsmith
- identify broken imports, missing modules, or incomplete parts
- improve structure and implementation while preserving the high level design

Core behavior the project must support:

1) Backends for PDF -> Markdown

Under ragsmith.backends implement a common abstraction:

- base.py:

  - Define:

    ```python
    from __future__ import annotations
    from abc import ABC, abstractmethod
    from pathlib import Path

    class PdfToMarkdownBackend(ABC):
        @abstractmethod
        def convert(self, pdf_path: Path) -> str:
            ...
    ```

- markitdown_backend.py:
  - Implement MarkitdownBackend(PdfToMarkdownBackend) using markitdown.MarkItDown.
  - Handle ImportError by raising a BackendNotAvailableError from ragsmith.errors.

- pymupdf_backend.py:
  - Implement PyMuPDFBackend(PdfToMarkdownBackend) using pymupdf4llm.to_markdown.
  - If pymupdf-layout is installed, activate it.
  - Handle known min() empty-sequence issues by either:
    - raising BackendConversionError, or
    - optionally falling back to MarkitdownBackend (configurable).

- docling_backend.py:
  - Implement DoclingBackend(PdfToMarkdownBackend) using docling.DocumentConverter.
  - Configure AcceleratorOptions / PdfPipelineOptions with device "auto" by default (CPU or GPU depending on environment).
  - If docling or torch cannot be imported, raise BackendNotAvailableError.
  - Implement a constructor parameter device: Literal["auto","cpu","cuda","mps"].

2) Processing pipeline for RAG-ready Markdown

Under ragsmith.processing:

- cleaning.py:
  - Implement:
    - strip_noise_lines(text: str) -> str
      - Remove repeated headers/footers using a frequency heuristic.
      - Remove page numbers using regex patterns.
      - Remove common boilerplate substrings (copyright, ISBN, etc.).
    - normalize_blank_lines(text: str, max_consecutive: int = 2) -> str

- rag_markdown.py:
  - Implement:
    - reflow_markdown_paragraphs(text: str) -> str
      - Do not change fenced code blocks (```).
      - Preserve headings, bulleted lists, numbered lists, blockquotes.
      - Merge wrapped paragraph lines into a single line.
      - Keep at most 2 consecutive blank lines.
    - process_for_rag(markdown_text: str, *, reflow: bool = True) -> str
      - Call strip_noise_lines, then reflow_markdown_paragraphs if reflow is True.

- splitting.py:
  - Implement:
    - split_by_top_level_headings(markdown_text: str) -> list[tuple[str, str]]
      - Split at lines starting with "# ".
      - Each section includes its heading.
      - Return (title, section_markdown).
    - slugify(text: str) -> str
      - Lowercase, replace non alphanumerics by hyphens, strip extra hyphens.

3) Errors and logging

- errors.py:
  - Implement:

    ```python
    class RagSmithError(Exception): ...
    class BackendNotAvailableError(RagSmithError): ...
    class BackendConversionError(RagSmithError): ...
    class OutputWriteError(RagSmithError): ...
    ```

- logging_config.py:
  - Configure a logger named "ragsmith".
  - Default level INFO, but allow override by env var RAGSMITH_LOG_LEVEL.
  - Optionally reduce noise from external libraries (huggingface_hub, transformers).

4) Config and high level app facade

- config.py:
  - Define a dataclass RagSmithConfig:

    ```python
    from dataclasses import dataclass

    @dataclass
    class RagSmithConfig:
        backend: str = "docling"          # or "pymupdf4llm" or "markitdown"
        reflow: bool = True
        split_sections: bool = False
        overwrite: bool = False
    ```

- app.py:
  - Implement class PdfMarkdownApp:

    - Constructor: accepts RagSmithConfig and optional logger.
    - Internally instantiates the chosen backend:
      - "markitdown" -> MarkitdownBackend
      - "pymupdf4llm" -> PyMuPDFBackend
      - "docling" -> DoclingBackend
    - Methods:
      - convert_file(pdf_path: Path) -> str
      - convert_files(pdf_paths: list[Path]) -> dict[Path, str]
      - convert_and_write(
            pdf_paths: list[Path],
            output_dir: Path | None = None,
        ) -> dict[Path, list[Path]]
        - For each input PDF:
          - run backend.convert(pdf_path)
          - run process_for_rag
          - if config.split_sections:
              - split into sections; write multiple .md files using slugify.
            else:
              - write a single .md next to PDF or in output_dir.
          - handle existing files depending on config.overwrite.
        - Return a mapping: input PDF -> list of created markdown files.
      - On any backend failure, raise BackendConversionError with details.

5) CLI

Under ragsmith/cli/main.py:

- Implement a CLI using argparse (keep dependencies minimal):

  - Command: `python -m ragsmith.cli.main`
  - Arguments:
    - one or more PDF paths
  - Options:
    - `--backend {markitdown,pymupdf4llm,docling}` (default from RagSmithConfig)
    - `--output-dir PATH`
    - `--split-sections` (default False)
    - `--no-reflow` (default reflow True)
    - `--overwrite`
  - Create RagSmithConfig from args and call PdfMarkdownApp.convert_and_write.
  - Print a simple summary of output paths.
  - Add:

    ```python
    def main() -> None:
        # parse args and run

    if __name__ == "__main__":
        main()
    ```

6) PyQt6 GUI

Under ragsmith/ui:

- main_window.py:
  - Implement MainWindow(QMainWindow) that:
    - Lets user select multiple PDFs (QFileDialog).
    - Lets user select an output directory.
    - Has combobox for backend.
    - Checkboxes:
      - Overwrite existing .md
      - Reflow paragraphs
      - Split by top-level headings
    - Progress bar and status label.
    - On "Convert" click:
      - Build RagSmithConfig from UI state.
      - Create PdfMarkdownApp.
      - Call convert_and_write synchronously (ok for now).
      - Show success / error messages in a QMessageBox.

- application.py:
  - Implement:

    ```python
    import sys
    from PyQt6.QtWidgets import QApplication
    from .main_window import MainWindow

    def run() -> None:
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        sys.exit(app.exec())

    if __name__ == "__main__":
        run()
    ```

7) Package init and entry points

- src/ragsmith/__init__.py:
  - Expose the main API:

    ```python
    from .app import PdfMarkdownApp
    from .config import RagSmithConfig

    __all__ = ["PdfMarkdownApp", "RagSmithConfig"]
    ```

- Ensure imports inside the package are absolute, not fragile relatives, e.g.:

  - `from ragsmith.processing.rag_markdown import process_for_rag`
  - `from ragsmith.backends.markitdown_backend import MarkitdownBackend`

8) Make the project runnable from the repo root

Update or create pyproject.toml or setup.cfg as needed (you can generate a minimal pyproject.toml) so that after:

```bash
pip install -e .
````

the following work correctly:

* `python -m ragsmith.cli.main some.pdf`
* `python -m ragsmith.ui.application`
* import from REPL:

  ```python
  from ragsmith import PdfMarkdownApp, RagSmithConfig
  ```

Finally:

* Fix all imports and missing pieces so the project runs end to end.
* Keep the code Python 3.10+ compatible with type hints.
* Make sure there are no circular imports.
* When you modify files, overwrite them completely with clean, consistent implementations.
