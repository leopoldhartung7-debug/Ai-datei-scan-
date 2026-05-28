"""Cross-platform "run at login" management.

* **Windows:** writes a value under ``HKCU\\...\\Run`` via :mod:`winreg`.
* **macOS:** writes a LaunchAgent plist into ``~/Library/LaunchAgents``.
* **Linux:** writes an XDG ``.desktop`` autostart entry.

All functions are best-effort and never raise; they return ``True`` on success.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ..constants import APP_ID, APP_NAME
from ..utils.logging import get_logger

log = get_logger(__name__)


def _launch_command() -> list[str]:
    """Best-effort command that re-launches the app (frozen exe or python -m)."""
    if getattr(sys, "frozen", False):  # PyInstaller bundle
        return [sys.executable]
    return [sys.executable, "-m", "smartfolders"]


def is_enabled() -> bool:
    try:
        if sys.platform.startswith("win"):
            return _win_is_enabled()
        if sys.platform == "darwin":
            return _mac_plist_path().exists()
        return _linux_desktop_path().exists()
    except Exception:  # pragma: no cover
        return False


def enable() -> bool:
    try:
        if sys.platform.startswith("win"):
            return _win_set(True)
        if sys.platform == "darwin":
            return _mac_set(True)
        return _linux_set(True)
    except Exception:  # pragma: no cover
        log.warning("Could not enable autostart", exc_info=True)
        return False


def disable() -> bool:
    try:
        if sys.platform.startswith("win"):
            return _win_set(False)
        if sys.platform == "darwin":
            return _mac_set(False)
        return _linux_set(False)
    except Exception:  # pragma: no cover
        log.warning("Could not disable autostart", exc_info=True)
        return False


# --------------------------------------------------------------------------- #
# Windows
# --------------------------------------------------------------------------- #
_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _win_is_enabled() -> bool:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY) as key:
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False


def _win_set(enabled: bool) -> bool:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            cmd = " ".join(f'"{part}"' for part in _launch_command())
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd + " --minimized")
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    return True


# --------------------------------------------------------------------------- #
# macOS
# --------------------------------------------------------------------------- #
def _mac_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"com.{APP_ID}.app.plist"


def _mac_set(enabled: bool) -> bool:
    path = _mac_plist_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    args = "".join(f"        <string>{a}</string>\n" for a in (*_launch_command(), "--minimized"))
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        f"    <key>Label</key>\n    <string>com.{APP_ID}.app</string>\n"
        "    <key>ProgramArguments</key>\n    <array>\n"
        f"{args}"
        "    </array>\n"
        "    <key>RunAtLoad</key>\n    <true/>\n"
        "    <key>KeepAlive</key>\n    <false/>\n"
        "</dict>\n"
        "</plist>\n"
    )
    path.write_text(plist, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- #
# Linux (XDG autostart)
# --------------------------------------------------------------------------- #
def _linux_desktop_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / f"{APP_ID}.desktop"


def _linux_set(enabled: bool) -> bool:
    path = _linux_desktop_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    exec_cmd = " ".join(_launch_command()) + " --minimized"
    entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={exec_cmd}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
    )
    path.write_text(entry, encoding="utf-8")
    return True
