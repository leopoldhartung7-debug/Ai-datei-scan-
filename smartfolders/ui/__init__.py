"""PyQt6 desktop interface for SmartFolders.

The UI never touches the filesystem or database directly; it talks to the
:class:`smartfolders.engine.SmartFoldersEngine` and listens to the
:class:`smartfolders.core.events.EventBus` via :class:`~smartfolders.ui.bridge.QtEventBridge`,
which marshals background-thread events onto the Qt main thread safely.
"""

from __future__ import annotations

__all__ = ["run_app"]


def run_app(*args, **kwargs):
    """Lazy import so importing the package doesn't require PyQt6."""
    from .app_qt import run_app as _run

    return _run(*args, **kwargs)
