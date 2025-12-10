"""Logging configuration for src."""
from __future__ import annotations

import logging
import os
from typing import Iterable


def _get_default_level() -> int:
    env_level = os.getenv("RAGSMITH_LOG_LEVEL", "INFO").upper()
    return getattr(logging, env_level, logging.INFO)


def configure_logging(level: int | None = None, quiet_loggers: Iterable[str] | None = None) -> None:
    logging.basicConfig(
        level=level or _get_default_level(),
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
