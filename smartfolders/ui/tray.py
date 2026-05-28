"""System tray integration for background operation."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from .icons import tray_icon


class TrayController:
    """Wraps a QSystemTrayIcon with a context menu and helper notifications."""

    def __init__(
        self,
        accent: str,
        on_show: Callable[[], None],
        on_toggle_engine: Callable[[], None],
        on_scan: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self._accent = accent
        self._on_toggle = on_toggle_engine
        self.tray = QSystemTrayIcon(tray_icon(accent, active=False))
        self.tray.setToolTip("SmartFolders")

        menu = QMenu()
        self._open_action = menu.addAction("Open SmartFolders")
        self._open_action.triggered.connect(lambda: on_show())
        menu.addSeparator()
        self._engine_action = menu.addAction("Start engine")
        self._engine_action.triggered.connect(lambda: on_toggle_engine())
        scan_action: QAction = menu.addAction("Scan now")
        scan_action.triggered.connect(lambda: on_scan())
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(lambda: on_quit())

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: on_show()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )

    def show(self) -> None:
        if self.available:
            self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def set_engine_running(self, running: bool) -> None:
        self.tray.setIcon(tray_icon(self._accent, active=running))
        self._engine_action.setText("Stop engine" if running else "Start engine")
        self.tray.setToolTip(f"SmartFolders - {'running' if running else 'stopped'}")

    def notify(self, title: str, message: str) -> None:
        if self.available:
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)
