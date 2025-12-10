"""PyQt6 application entrypoint."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    run()
