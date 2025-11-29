"""Logging configuration for RagSmith."""
from __future__ import annotations

import logging
from typing import Iterable


def configure_logging(level: int = logging.INFO, quiet_loggers: Iterable[str] | None = None) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    for name in quiet_loggers or ("huggingface_hub", "transformers", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        configure_logging()
    return logger


__all__ = ["configure_logging", "get_logger"]
