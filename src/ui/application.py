"""Entry point for launching the PyQt6 application."""
from __future__ import annotations

import sys

from src.ui.main_window import create_app


def run() -> None:
    app = create_app()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()


__all__ = ["run"]
