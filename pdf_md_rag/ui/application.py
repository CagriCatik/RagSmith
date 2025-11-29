"""Entry point for launching the PyQt6 application."""
from __future__ import annotations

import sys

from pdf_md_rag.ui.main_window import create_app


def run() -> None:  # pragma: no cover - UI entry
    app = create_app()
    sys.exit(app.exec())


__all__ = ["run"]
