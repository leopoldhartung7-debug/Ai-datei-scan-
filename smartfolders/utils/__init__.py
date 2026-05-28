"""Shared, dependency-light helper utilities."""

from __future__ import annotations

from .hashing import file_sha256, perceptual_hash, quick_signature
from .logging import get_logger, setup_logging
from .paths import (
    app_config_dir,
    app_data_dir,
    app_log_dir,
    default_database_path,
    default_watched_folders,
    ensure_dir,
    human_size,
    is_subpath,
    unique_destination,
)

__all__ = [
    "file_sha256",
    "perceptual_hash",
    "quick_signature",
    "get_logger",
    "setup_logging",
    "app_config_dir",
    "app_data_dir",
    "app_log_dir",
    "default_database_path",
    "default_watched_folders",
    "ensure_dir",
    "human_size",
    "is_subpath",
    "unique_destination",
]
