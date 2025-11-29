"""PyQt6 MainWindow for pdf_md_rag."""
from __future__ import annotations

from pathlib import Path
import logging
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.app import PdfMarkdownApp
from src.backends import registry
from src.config import AppConfig, BackendConfig

LOGGER = logging.getLogger("src.ui")


class ConversionWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, app: PdfMarkdownApp, files: List[Path], output_dir: Path, split: bool, reflow: bool):
        super().__init__()
        self.app = app
        self.files = files
        self.output_dir = output_dir
        self.split = split
        self.reflow = reflow

    def run(self) -> None:  # pragma: no cover - UI thread
        try:
            total = len(self.files)
            for idx, file in enumerate(self.files, 1):
                self.app.convert_and_write(
                    [file],
                    self.output_dir,
                    split_sections=self.split,
                    reflow=self.reflow,
                )
                percent = int(idx / total * 100)
                self.progress.emit(percent)
            self.finished.emit({str(f): "ok" for f in self.files})
        except Exception as exc:  # noqa: BLE001 - UI surface
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config = config or AppConfig()
        self.setWindowTitle("PDF to RAG Markdown")
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout()

        self.file_list = QListWidget()
        add_files_btn = QPushButton("Add PDFs")
        add_files_btn.clicked.connect(self._add_files)

        backend_row = QHBoxLayout()
        backend_row.addWidget(QLabel("Backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(registry.names())
        self.backend_combo.setCurrentText(self.config.backend.name)
        backend_row.addWidget(self.backend_combo)

        options_row = QHBoxLayout()
        self.reflow_checkbox = QCheckBox("Reflow paragraphs")
        self.reflow_checkbox.setChecked(self.config.default_reflow)
        self.split_checkbox = QCheckBox("Split by top-level headings")
        self.split_checkbox.setChecked(self.config.default_split_sections)
        self.overwrite_checkbox = QCheckBox("Overwrite existing")
        self.overwrite_checkbox.setChecked(self.config.overwrite)
        options_row.addWidget(self.reflow_checkbox)
        options_row.addWidget(self.split_checkbox)
        options_row.addWidget(self.overwrite_checkbox)

        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output Dir:"))
        self.output_label = QLabel(str(self.config.default_output_dir or "(choose)"))
        select_output_btn = QPushButton("Select")
        select_output_btn.clicked.connect(self._select_output_dir)
        output_row.addWidget(self.output_label)
        output_row.addWidget(select_output_btn)

        self.progress = QProgressBar()
        self.status_label = QLabel("Ready")

        convert_btn = QPushButton("Convert")
        convert_btn.clicked.connect(self._convert)

        layout.addWidget(add_files_btn)
        layout.addWidget(self.file_list)
        layout.addLayout(backend_row)
        layout.addLayout(options_row)
        layout.addLayout(output_row)
        layout.addWidget(convert_btn)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def _add_files(self) -> None:  # pragma: no cover - UI event
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", filter="PDF Files (*.pdf)")
        for f in files:
            self.file_list.addItem(QListWidgetItem(f))

    def _select_output_dir(self) -> None:  # pragma: no cover - UI event
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.output_label.setText(directory)

    def _convert(self) -> None:  # pragma: no cover - UI event
        files = [Path(self.file_list.item(i).text()) for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, "No files", "Please add at least one PDF.")
            return

        output_dir_text = self.output_label.text()
        if not output_dir_text or output_dir_text == "(choose)":
            QMessageBox.warning(self, "No output directory", "Please choose an output directory.")
            return

        backend_name = self.backend_combo.currentText()
        backend_config = BackendConfig(name=backend_name)
        app_config = AppConfig(backend=backend_config, overwrite=self.overwrite_checkbox.isChecked())
        app = PdfMarkdownApp(app_config)

        self.thread = QThread(self)
        self.worker = ConversionWorker(
            app,
            files,
            Path(output_dir_text),
            split=self.split_checkbox.isChecked(),
            reflow=self.reflow_checkbox.isChecked(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.start()
        self.status_label.setText("Running conversions...")

    def _on_finished(self, results: dict) -> None:  # pragma: no cover - UI event
        self.status_label.setText("Conversion complete")
        self.progress.setValue(100)
        QMessageBox.information(self, "Done", "Conversion finished.")

    def _on_failed(self, message: str) -> None:  # pragma: no cover - UI event
        LOGGER.error("Conversion failed: %s", message)
        self.status_label.setText("Error")
        QMessageBox.critical(self, "Error", message)


def create_app(config: AppConfig | None = None) -> QApplication:  # pragma: no cover - UI event
    import sys

    qt_app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(config)
    window.show()

    # Keep a reference to prevent garbage collection of the main window
    qt_app.main_window = window

    return qt_app


__all__ = ["MainWindow", "create_app"]
