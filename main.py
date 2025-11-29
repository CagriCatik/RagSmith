#!/usr/bin/env python3
"""
PyQt6 GUI to convert one or more technical PDFs to high quality Markdown
for RAG pipelines using markitdown, pymupdf4llm, or docling.

Features:
- Multiple PDF selection.
- Optional output directory.
- Backend selection: markitdown / pymupdf4llm / docling.
- pymupdf-layout support (better layout for PyMuPDF4LLM).
- Optional GPU acceleration for Docling via AcceleratorOptions (AUTO / CUDA).
- Suppressed noisy pydub / ffmpeg RuntimeWarning.
- Suppressed PyMuPDF "suggest layout analyzer" notice.
- Xet warnings from huggingface_hub disabled.
- Robust fallback: if backend fails, falls back to markitdown for that file.
- Removal of repeated headers/footers, page numbers, boilerplate.
- Paragraph reflow that preserves code blocks and markdown structure.
- Optional splitting into multiple markdown files by top level headings (# ...).
"""

import os
import warnings
import logging

# ---------------------------------------------------------------------------
# Global warning / env configuration
# ---------------------------------------------------------------------------

# Suppress the pydub ffmpeg RuntimeWarning
warnings.filterwarnings(
    "ignore",
    message="Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
    category=RuntimeWarning,
    module="pydub.utils",
)

# Disable PyMuPDF layout suggestion message
os.environ.setdefault("PYMUPDF_SUGGEST_LAYOUT_ANALYZER", "0")

# Disable HuggingFace Xet warnings (still installs hf_xet via requirements)
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

# Basic logging configuration (keep errors, reduce noise)
logging.basicConfig(level=logging.INFO)
logging.getLogger("huggingface_hub.file_download").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils._xet").setLevel(logging.ERROR)

import re
import contextlib
from pathlib import Path
from collections import Counter
from typing import List, Tuple, Iterable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QLabel,
    QProgressBar,
    QMessageBox,
    QCheckBox,
    QComboBox,
)

from markitdown import MarkItDown

# Optional backend: pymupdf4llm
try:
    import pymupdf4llm  # noqa: F401
    HAS_PYMUPDF4LLM = True
except ImportError:
    pymupdf4llm = None
    HAS_PYMUPDF4LLM = False

# Optional: pymupdf_layout activation (if installed)
HAS_PYMUPDF_LAYOUT = False
try:
    import pymupdf.layout as pymupdf_layout  # type: ignore[attr-defined]

    pymupdf_layout.activate()
    HAS_PYMUPDF_LAYOUT = True
except ImportError:
    HAS_PYMUPDF_LAYOUT = False

# Optional backend: docling (catch any exception, not only ImportError)
HAS_DOCLING = False
DoclingDocumentConverter = None
DoclingAcceleratorOptions = None
DoclingAcceleratorDevice = None
DoclingPdfPipelineOptions = None
DoclingInputFormat = None
DoclingPdfFormatOption = None

try:
    from docling.document_converter import (
        DocumentConverter as DoclingDocumentConverter,
        PdfFormatOption as DoclingPdfFormatOption,
    )
    from docling.datamodel.base_models import InputFormat as DoclingInputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions as DoclingPdfPipelineOptions,
    )
    from docling.datamodel.accelerator_options import (
        AcceleratorOptions as DoclingAcceleratorOptions,
        AcceleratorDevice as DoclingAcceleratorDevice,
    )

    HAS_DOCLING = True
except Exception:
    HAS_DOCLING = False


# ---------------------------------------------------------------------------
# Heuristics for cleaning technical book PDFs for RAG
# ---------------------------------------------------------------------------

NOISE_SUBSTRINGS = [
    "all rights reserved",
    "no part of this publication",
    "reprinted with permission",
    "copyright",
    "isbn",
    "printed in",
]

PAGE_NUMBER_PATTERNS = [
    re.compile(r"^page\s+\d+(\s+of\s+\d+)?$", re.IGNORECASE),
    re.compile(r"^\d+\s*/\s*\d+$"),
    re.compile(r"^\d+$"),
]


def is_page_number_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    for pat in PAGE_NUMBER_PATTERNS:
        if pat.match(s):
            return True
    return False


def is_boilerplate_line(line: str) -> bool:
    s = line.lower()
    for token in NOISE_SUBSTRINGS:
        if token in s:
            return True
    return False


def find_repeated_lines(
    lines: Iterable[str],
    min_repeats: int = 3,
    min_len: int = 5,
    max_len: int = 120,
) -> set[str]:
    """
    Find short lines that repeat at least min_repeats times.
    These are often headers or footers in technical PDFs.
    """
    norm_counter: Counter[str] = Counter()

    for line in lines:
        s = line.strip()
        if len(s) < min_len or len(s) > max_len:
            continue
        if s.startswith("#"):
            continue
        norm_counter[s] += 1

    return {text for text, cnt in norm_counter.items() if cnt >= min_repeats}


def strip_noise_lines(markdown_text: str) -> str:
    """
    Remove:
      - globally repeated short lines (likely headers/footers),
      - page number lines,
      - known boilerplate lines.
    """
    lines = markdown_text.splitlines()

    repeated = find_repeated_lines(lines)

    cleaned_lines: List[str] = []
    for line in lines:
        raw = line.rstrip("\n")
        stripped = raw.strip()

        if not stripped:
            cleaned_lines.append(raw)
            continue

        if stripped in repeated:
            continue

        if is_page_number_line(raw):
            continue

        if is_boilerplate_line(raw):
            continue

        cleaned_lines.append(raw)

    final_lines: List[str] = []
    blank_count = 0
    for l in cleaned_lines:
        if l.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                final_lines.append("")
        else:
            blank_count = 0
            final_lines.append(l)

    return "\n".join(final_lines).strip() + "\n"


def reflow_markdown_paragraphs(text: str) -> str:
    """
    Reflow paragraphs in markdown to improve text quality for RAG.

    Heuristics:
    - Do not touch code blocks (``` fences).
    - Do not touch headings, list items, or blockquotes.
    - Collapse multi line paragraphs into a single line.
    - Keep at most 2 consecutive blank lines.
    """
    lines = text.splitlines()
    result_lines: List[str] = []

    in_code = False
    para_buffer: List[str] = []

    def is_structural_line(l: str) -> bool:
        ls = l.lstrip()
        if not ls:
            return False
        if ls.startswith("#"):
            return True
        if ls.startswith(("-", "*", "+")):
            return True
        if ls.startswith(">"):
            return True
        if re.match(r"^\d+\.\s+", ls):
            return True
        return False

    def flush_paragraph() -> None:
        nonlocal para_buffer
        if not para_buffer:
            return

        joined = para_buffer[0].strip()
        for part in para_buffer[1:]:
            part_s = part.strip()
            if not part_s:
                continue
            if joined.endswith("-") and not joined.endswith("--"):
                joined = joined[:-1] + part_s
            else:
                joined = f"{joined} {part_s}"
        result_lines.append(joined)
        para_buffer = []

    for line in lines:
        stripped = line.rstrip("\n")

        if stripped.strip().startswith("```"):
            flush_paragraph()
            in_code = not in_code
            result_lines.append(stripped)
            continue

        if in_code:
            result_lines.append(stripped)
            continue

        if stripped.strip() == "":
            flush_paragraph()
            if not result_lines or result_lines[-1] != "":
                result_lines.append("")
            continue

        if is_structural_line(stripped):
            flush_paragraph()
            if stripped.lstrip().startswith("#"):
                if result_lines and result_lines[-1] != "":
                    result_lines.append("")
            result_lines.append(stripped)
            continue

        para_buffer.append(stripped)

    flush_paragraph()

    cleaned: List[str] = []
    blank_count = 0
    for l in result_lines:
        if l == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(l)

    return "\n".join(cleaned).strip() + "\n"


def split_markdown_by_top_level_headings(
    markdown_text: str,
) -> List[Tuple[str, str]]:
    """
    Split markdown into sections by top level headings ("# ").

    Returns list of (title, section_markdown).
    Sections include their heading line.
    """
    lines = markdown_text.splitlines()
    sections: List[Tuple[str, List[str]]] = []
    current_title = "intro"
    current_lines: List[str] = []

    def flush_section(title: str, section_lines: List[str]) -> None:
        if not section_lines:
            return
        section_body = "\n".join(section_lines).strip()
        if not section_body:
            return
        sections.append((title, section_lines.copy()))

    for line in lines:
        if line.startswith("# "):
            if current_lines:
                flush_section(current_title, current_lines)
            current_title = line[2:].strip() or "section"
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        flush_section(current_title, current_lines)

    result: List[Tuple[str, str]] = []
    for title, section_lines in sections:
        section_text = "\n".join(section_lines).strip() + "\n"
        result.append((title, section_text))

    return result


def slugify(text: str) -> str:
    """
    Slugify a title for file names.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "section"


def process_markdown_for_rag(
    markdown_text: str,
    reflow: bool = True,
) -> str:
    """
    Apply all postprocessing steps to markdown, in a safe order.
    """
    markdown_text = strip_noise_lines(markdown_text)

    if reflow:
        markdown_text = reflow_markdown_paragraphs(markdown_text)
    else:
        markdown_text = "\n".join(
            line.rstrip() for line in markdown_text.splitlines()
        ) + "\n"

    return markdown_text


# ---------------------------------------------------------------------------
# Docling GPU / accelerator configuration helper
# ---------------------------------------------------------------------------

def make_docling_converter() -> Optional[object]:
    """
    Create a Docling DocumentConverter with accelerator options.

    Uses AcceleratorDevice.AUTO so Docling will choose CPU / CUDA / MPS
    based on environment and installed Torch. To force CUDA, set
    DOCLING_DEVICE=cuda before running the app.
    """
    if not HAS_DOCLING:
        return None

    accel = DoclingAcceleratorOptions(
        device=DoclingAcceleratorDevice.AUTO,
        num_threads=None,
    )
    pdf_opts = DoclingPdfPipelineOptions(
        accelerator_options=accel,
    )

    format_options = {
        DoclingInputFormat.PDF: DoclingPdfFormatOption(
            pipeline_options=pdf_opts
        )
    }

    return DoclingDocumentConverter(format_options=format_options)


# ---------------------------------------------------------------------------
# PyQt6 GUI
# ---------------------------------------------------------------------------

class PdfToMarkdownWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        title = "PDF to Markdown for RAG (markitdown / pymupdf4llm / docling"
        if HAS_PYMUPDF_LAYOUT:
            title += " + pymupdf-layout"
        title += ")"
        self.setWindowTitle(title)

        self.pdf_paths: List[Path] = []
        self.output_dir: Optional[Path] = None

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        central.setLayout(layout)

        files_label = QLabel("Selected PDF files:")
        layout.addWidget(files_label)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add PDFs")
        self.btn_remove_selected = QPushButton("Remove selected")
        self.btn_clear = QPushButton("Clear all")

        self.btn_add.clicked.connect(self.add_pdfs)
        self.btn_remove_selected.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_all)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove_selected)
        btn_row.addWidget(self.btn_clear)
        layout.addLayout(btn_row)

        out_row = QHBoxLayout()
        self.output_label = QLabel("Output directory: [Same as each input file]")
        self.btn_select_output = QPushButton("Select output directory")
        self.btn_clear_output = QPushButton("Use input directories")

        self.btn_select_output.clicked.connect(self.select_output_directory)
        self.btn_clear_output.clicked.connect(self.clear_output_directory)

        out_row.addWidget(self.output_label, stretch=1)
        out_row.addWidget(self.btn_select_output)
        out_row.addWidget(self.btn_clear_output)
        layout.addLayout(out_row)

        backend_row = QHBoxLayout()
        backend_label = QLabel("Backend:")
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("markitdown")
        self.backend_combo.addItem("pymupdf4llm")
        self.backend_combo.addItem("docling")
        backend_row.addWidget(backend_label)
        backend_row.addWidget(self.backend_combo)
        backend_row.addStretch(1)
        layout.addLayout(backend_row)

        self.chk_overwrite = QCheckBox("Overwrite existing .md files")
        layout.addWidget(self.chk_overwrite)

        self.chk_reflow = QCheckBox(
            "Reflow paragraphs and clean markdown (recommended)"
        )
        self.chk_reflow.setChecked(True)
        layout.addWidget(self.chk_reflow)

        self.chk_split_sections = QCheckBox(
            "Split into multiple markdown files by top level headings (# ...)"
        )
        self.chk_split_sections.setChecked(False)
        layout.addWidget(self.chk_split_sections)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.btn_convert = QPushButton("Convert to Markdown")
        self.btn_convert.clicked.connect(self.convert_all)
        layout.addWidget(self.btn_convert)

        self.resize(950, 580)

    # file selection

    def add_pdfs(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF files",
            "",
            "PDF files (*.pdf);;All files (*)",
        )
        if not files:
            return

        for f in files:
            path = Path(f)
            if path.suffix.lower() != ".pdf":
                continue
            if path not in self.pdf_paths:
                self.pdf_paths.append(path)
                item = QListWidgetItem(str(path))
                self.list_widget.addItem(item)

    def remove_selected(self) -> None:
        selected_items = self.list_widget.selectedItems()
        for item in selected_items:
            idx = self.list_widget.row(item)
            self.list_widget.takeItem(idx)
        self.pdf_paths = [
            Path(self.list_widget.item(i).text())
            for i in range(self.list_widget.count())
        ]

    def clear_all(self) -> None:
        self.list_widget.clear()
        self.pdf_paths.clear()

    def select_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select output directory",
            "",
        )
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(f"Output directory: {self.output_dir}")

    def clear_output_directory(self) -> None:
        self.output_dir = None
        self.output_label.setText("Output directory: [Same as each input file]")

    # core conversion for a single PDF, with robust fallback

    def _convert_pdf_to_markdown(
        self,
        pdf_path: Path,
        backend: str,
        md_converter: Optional[MarkItDown],
        docling_converter: Optional[object],
    ) -> str:
        """
        Convert a single PDF to markdown using the selected backend.

        If backend fails, fall back to markitdown for this file.
        """
        with open(os.devnull, "w") as devnull, contextlib.redirect_stderr(devnull):
            if backend == "markitdown":
                assert md_converter is not None
                result = md_converter.convert(str(pdf_path))
                return result.text_content

            if backend == "pymupdf4llm":
                if not HAS_PYMUPDF4LLM:
                    raise RuntimeError("pymupdf4llm backend not available")
                try:
                    return pymupdf4llm.to_markdown(str(pdf_path))
                except Exception as e:
                    msg = str(e)
                    if "min()" in msg and "empty" in msg:
                        fallback = MarkItDown()
                        result = fallback.convert(str(pdf_path))
                        return result.text_content
                    raise

            if backend == "docling":
                if not HAS_DOCLING or docling_converter is None:
                    raise RuntimeError("Docling backend not available")
                try:
                    conv_result = docling_converter.convert(str(pdf_path))
                    doc = conv_result.document
                    return doc.export_to_markdown()
                except Exception:
                    fallback = MarkItDown()
                    result = fallback.convert(str(pdf_path))
                    return result.text_content

            # Fallback catch-all
            fallback = MarkItDown()
            result = fallback.convert(str(pdf_path))
            return result.text_content

    # conversion loop

    def convert_all(self) -> None:
        if not self.pdf_paths:
            QMessageBox.warning(self, "No PDFs", "No PDF files selected.")
            return

        backend = self.backend_combo.currentText()
        if backend == "pymupdf4llm" and not HAS_PYMUPDF4LLM:
            QMessageBox.critical(
                self,
                "Backend error",
                "pymupdf4llm is not installed. Install it with:\n\npip install pymupdf4llm",
            )
            return
        if backend == "docling" and not HAS_DOCLING:
            QMessageBox.critical(
                self,
                "Backend error",
                "docling (or its dependencies like torch) are not available.\n"
                "Fix the installation or choose another backend.",
            )
            return

        self._set_controls_enabled(False)

        md_converter = MarkItDown() if backend == "markitdown" else None
        docling_converter = (
            make_docling_converter() if backend == "docling" and HAS_DOCLING else None
        )

        total = len(self.pdf_paths)
        self.progress.setRange(0, total)
        self.progress.setValue(0)

        errors: List[str] = []

        for i, pdf_path in enumerate(self.pdf_paths, start=1):
            try:
                markdown_text = self._convert_pdf_to_markdown(
                    pdf_path, backend, md_converter, docling_converter
                )

                markdown_text = process_markdown_for_rag(
                    markdown_text,
                    reflow=self.chk_reflow.isChecked(),
                )

                if self.output_dir is not None:
                    out_dir = self.output_dir
                else:
                    out_dir = pdf_path.parent

                out_dir.mkdir(parents=True, exist_ok=True)

                if self.chk_split_sections.isChecked():
                    self._write_split_markdown_files(
                        pdf_path=pdf_path,
                        markdown_text=markdown_text,
                        out_dir=out_dir,
                        errors=errors,
                    )
                else:
                    self._write_single_markdown_file(
                        pdf_path=pdf_path,
                        markdown_text=markdown_text,
                        out_dir=out_dir,
                        errors=errors,
                    )

            except Exception as e:
                errors.append(f"{pdf_path}: {e}")

            self.progress.setValue(i)
            QApplication.processEvents()

        self._set_controls_enabled(True)

        if errors:
            msg = "Finished with some issues:\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Conversion completed with errors", msg)
        else:
            QMessageBox.information(
                self, "Conversion finished", "All PDFs converted successfully."
            )

    def _write_single_markdown_file(
        self,
        pdf_path: Path,
        markdown_text: str,
        out_dir: Path,
        errors: List[str],
    ) -> None:
        out_path = out_dir / (pdf_path.stem + ".md")
        if out_path.exists() and not self.chk_overwrite.isChecked():
            errors.append(f"Skipped (exists): {out_path}")
            return
        try:
            out_path.write_text(markdown_text, encoding="utf-8")
        except Exception as e:
            errors.append(f"Failed writing {out_path}: {e}")

    def _write_split_markdown_files(
        self,
        pdf_path: Path,
        markdown_text: str,
        out_dir: Path,
        errors: List[str],
    ) -> None:
        sections = split_markdown_by_top_level_headings(markdown_text)

        if not sections:
            self._write_single_markdown_file(pdf_path, markdown_text, out_dir, errors)
            return

        base = pdf_path.stem

        for idx, (title, section_text) in enumerate(sections, start=1):
            slug = slugify(title)
            file_name = f"{base}_{idx:02d}_{slug}.md"
            out_path = out_dir / file_name

            if out_path.exists() and not self.chk_overwrite.isChecked():
                errors.append(f"Skipped (exists): {out_path}")
                continue

            try:
                out_path.write_text(section_text, encoding="utf-8")
            except Exception as e:
                errors.append(f"Failed writing {out_path}: {e}")

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_convert.setEnabled(enabled)
        self.btn_add.setEnabled(enabled)
        self.btn_remove_selected.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_select_output.setEnabled(enabled)
        self.btn_clear_output.setEnabled(enabled)
        self.chk_overwrite.setEnabled(enabled)
        self.chk_reflow.setEnabled(enabled)
        self.chk_split_sections.setEnabled(enabled)
        self.backend_combo.setEnabled(enabled)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        event.accept()


def main() -> None:
    app = QApplication([])
    win = PdfToMarkdownWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
