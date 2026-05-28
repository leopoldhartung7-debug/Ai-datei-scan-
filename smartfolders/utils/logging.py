"""Centralised logging configuration.

A single rotating file handler plus a console handler. Importing modules should
always go through :func:`get_logger` so the configuration stays consistent.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .paths import app_log_dir

_CONFIGURED = False
_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int | str = logging.INFO, *, to_file: bool = True) -> None:
    """Configure the root logger exactly once.

    Safe to call multiple times; subsequent calls only adjust the level.
    """
    global _CONFIGURED
    root = logging.getLogger()

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    if _CONFIGURED:
        root.setLevel(level)
        return

    root.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler(stream=sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)

    if to_file:
        try:
            log_file = Path(app_log_dir()) / "smartfolders.log"
            file_handler = RotatingFileHandler(
                log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except Exception:  # pragma: no cover - never let logging crash the app
            root.warning("Could not attach file log handler", exc_info=True)

    # Tame noisy third party loggers.
    for noisy in ("watchdog", "PIL", "urllib3", "transformers", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger, ensuring logging has been initialised."""
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
