"""Filesystem path helpers and per-user application directories.

Uses :mod:`platformdirs` when available (correct on Windows/macOS/Linux), and
falls back to a sensible ``~/.smartfolders`` layout otherwise so the module
never hard-fails on a minimal install.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..constants import APP_NAME, ORG_NAME

try:  # pragma: no cover - exercised indirectly
    from platformdirs import user_config_dir, user_data_dir, user_log_dir

    _HAVE_PLATFORMDIRS = True
except Exception:  # pragma: no cover
    _HAVE_PLATFORMDIRS = False


def _fallback_base() -> Path:
    return Path.home() / ".smartfolders"


def app_data_dir() -> Path:
    """Directory for the database, cache and downloaded models."""
    if _HAVE_PLATFORMDIRS:
        return ensure_dir(Path(user_data_dir(APP_NAME, ORG_NAME)))
    return ensure_dir(_fallback_base() / "data")


def app_config_dir() -> Path:
    """Directory for the JSON settings file."""
    if _HAVE_PLATFORMDIRS:
        return ensure_dir(Path(user_config_dir(APP_NAME, ORG_NAME)))
    return ensure_dir(_fallback_base() / "config")


def app_log_dir() -> Path:
    """Directory for rotating log files."""
    if _HAVE_PLATFORMDIRS:
        return ensure_dir(Path(user_log_dir(APP_NAME, ORG_NAME)))
    return ensure_dir(_fallback_base() / "logs")


def default_database_path() -> Path:
    return app_data_dir() / "smartfolders.db"


def ensure_dir(path: str | os.PathLike[str]) -> Path:
    """Create *path* (and parents) if needed and return it as a ``Path``."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_watched_folders() -> list[Path]:
    """Best-effort list of common user folders to monitor by default."""
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
        home / "Pictures",
    ]
    # Windows localized names sometimes differ; only return existing folders,
    # but always include Downloads/Desktop even if missing so the UI shows them.
    result: list[Path] = []
    for c in candidates:
        result.append(c)
    return result


def is_subpath(child: str | os.PathLike[str], parent: str | os.PathLike[str]) -> bool:
    """Return ``True`` if *child* is the same as or located under *parent*."""
    try:
        child_r = Path(child).resolve()
        parent_r = Path(parent).resolve()
    except (OSError, RuntimeError):
        return False
    return child_r == parent_r or parent_r in child_r.parents


def unique_destination(dest: str | os.PathLike[str]) -> Path:
    """Return a non-colliding destination path.

    If ``report.pdf`` exists, returns ``report (1).pdf``, then ``report (2).pdf``
    and so on. Pure path arithmetic - performs no I/O beyond ``exists`` checks.
    """
    dest = Path(dest)
    if not dest.exists():
        return dest
    stem, suffix, parent = dest.stem, dest.suffix, dest.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def human_size(num_bytes: float) -> str:
    """Format a byte count as a human readable string (e.g. ``1.4 MB``)."""
    if num_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
