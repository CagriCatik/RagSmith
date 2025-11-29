"""Logging helpers for pdf_md_rag."""
from __future__ import annotations

import logging
import logging.config
import os


DEFAULT_LOG_LEVEL = os.environ.get("PDF_MD_RAG_LOG_LEVEL", "INFO")


def configure_logging(level: str | int = DEFAULT_LOG_LEVEL) -> None:
    """Configure a standard logging setup for the application."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": level,
                }
            },
            "loggers": {
                "pdf_md_rag": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                "pdf_md_rag.backends": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
                "pdf_md_rag.processing": {
                    "handlers": ["console"],
                    "level": level,
                    "propagate": False,
                },
            },
            "root": {"handlers": ["console"], "level": level},
        }
    )


__all__ = ["configure_logging", "DEFAULT_LOG_LEVEL"]
