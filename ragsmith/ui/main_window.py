"""Main application window for the RagSmith GUI."""
from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QWidget,
)

from ragsmith.app import PdfMarkdownApp
from ragsmith.config import RagSmithConfig
from ragsmith.errors import BackendNotAvailableError, OutputWriteError, BackendConversionError, format_exception_chain
from ragsmith.logging_config import configure_logging


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        configure_logging()
        self.setWindowTitle("RagSmith PDF → Markdown")

        self.config = RagSmithConfig()
        self.app: PdfMarkdownApp | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        layout = QGridLayout()
        central.setLayout(layout)

        # File list
        layout.addWidget(QLabel("PDF files:"), 0, 0, 1, 3)
        self.file_list = QListWidget()
        layout.addWidget(self.file_list, 1, 0, 1, 3)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_files)
        remove_btn = QPushButton("Remove selected")
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_files)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout, 2, 0, 1, 3)

        # Output directory
        layout.addWidget(QLabel("Output directory:"), 3, 0)
        self.output_dir_edit = QLineEdit()
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.select_output_dir)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout, 3, 1, 1, 2)

        # Backend options
        layout.addWidget(QLabel("Backend:"), 4, 0)
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["docling", "markitdown", "pymupdf4llm"])
        self.backend_combo.setCurrentText(self.config.backend)
        layout.addWidget(self.backend_combo, 4, 1, 1, 2)

        # Checkboxes
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.reflow_checkbox = QCheckBox("Reflow paragraphs")
        self.reflow_checkbox.setChecked(self.config.reflow)
        self.split_checkbox = QCheckBox("Split sections by # headings")
        self.split_checkbox.setChecked(self.config.split_sections)
        layout.addWidget(self.overwrite_checkbox, 5, 0, 1, 3)
        layout.addWidget(self.reflow_checkbox, 6, 0, 1, 3)
        layout.addWidget(self.split_checkbox, 7, 0, 1, 3)

        # Progress and actions
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress, 8, 0, 1, 3)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, 9, 0, 1, 3)

        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(self.convert_files)
        layout.addWidget(convert_btn, 10, 0, 1, 3)

        self.setCentralWidget(central)

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDF files", "", "PDF Files (*.pdf)")
        for file_path in files:
            self.file_list.addItem(QListWidgetItem(file_path))

    def remove_selected(self) -> None:
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_files(self) -> None:
        self.file_list.clear()

    def select_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_dir_edit.setText(directory)

    def _collect_paths(self) -> List[Path]:
        return [Path(self.file_list.item(i).text()) for i in range(self.file_list.count())]

    def _build_config(self) -> RagSmithConfig:
        return RagSmithConfig(
            backend=self.backend_combo.currentText(),
            reflow=self.reflow_checkbox.isChecked(),
            split_sections=self.split_checkbox.isChecked(),
            overwrite=self.overwrite_checkbox.isChecked(),
        )

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def convert_files(self) -> None:
        paths = self._collect_paths()
        if not paths:
            QMessageBox.warning(self, "No files", "Please add at least one PDF file to convert.")
            return

        output_dir_text = self.output_dir_edit.text().strip()
        output_dir = Path(output_dir_text) if output_dir_text else None

        try:
            self.config = self._build_config()
            self.app = PdfMarkdownApp(self.config)
        except BackendNotAvailableError as exc:
            QMessageBox.critical(self, "Backend unavailable", str(exc))
            return

        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self._set_status("Working…")

        try:
            for index, path in enumerate(paths, start=1):
                results = self.app.convert_and_write([path], output_dir=output_dir)
                created = results.get(path, [])
                self.progress.setValue(index)
                self._set_status(f"Wrote {len(created)} file(s) for {path.name}")
            QMessageBox.information(self, "Done", "Conversion completed successfully.")
            self._set_status("Completed")
        except (OutputWriteError, BackendConversionError) as exc:
            QMessageBox.critical(self, "Conversion error", format_exception_chain(exc))
            self._set_status("Error")
        except Exception as exc:  # pragma: no cover - GUI safety
            QMessageBox.critical(self, "Unexpected error", format_exception_chain(exc))
            self._set_status("Error")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
