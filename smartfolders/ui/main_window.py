"""The main application window: sidebar navigation + stacked views + tray."""

from __future__ import annotations

from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig
from ..core.events import Event, EventType
from ..engine import SmartFoldersEngine
from .bridge import QtEventBridge
from .icons import app_icon
from .theme import stylesheet_for
from .tray import TrayController
from .views import (
    DashboardView,
    DuplicatesView,
    FilesView,
    OptimizeView,
    RulesView,
    SearchView,
    SettingsView,
)
from .widgets import NavButton

NAV_ITEMS = [
    ("Dashboard", "dashboard"),
    ("Search", "search"),
    ("Files", "files"),
    ("Rules", "rules"),
    ("Duplicates", "duplicates"),
    ("Optimize", "optimize"),
    ("Settings", "settings"),
]


class MainWindow(QWidget):
    def __init__(self, engine: SmartFoldersEngine, config: AppConfig) -> None:
        super().__init__()
        self.engine = engine
        self.config = config
        self._allow_close = False

        self.setObjectName("RootWidget")
        self.setWindowTitle("SmartFolders")
        self.setWindowIcon(app_icon(config.ui.accent_color))
        self.resize(config.ui.window_width, config.ui.window_height)

        self.bridge = QtEventBridge(engine.bus, self)
        self.bridge.event.connect(self._on_event)

        self._build()
        self._apply_theme()
        self._setup_tray()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._topbar())

        self.stack = QStackedWidget()
        self.dashboard = DashboardView(self.engine)
        self.search_view = SearchView(self.engine)
        self.files_view = FilesView(self.engine)
        self.rules_view = RulesView(self.engine)
        self.duplicates_view = DuplicatesView(self.engine)
        self.optimize_view = OptimizeView(self.engine, self._apply_recommended_perf)
        self.settings_view = SettingsView(self.engine, self.config)
        self.settings_view.config_changed.connect(self._on_config_changed)

        for view in (
            self.dashboard, self.search_view, self.files_view, self.rules_view,
            self.duplicates_view, self.optimize_view, self.settings_view,
        ):
            self.stack.addWidget(view)
        right_layout.addWidget(self.stack, 1)
        root.addWidget(right, 1)

        self._select(0)

    def _sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

        logo = QLabel("SmartFolders")
        logo.setObjectName("Logo")
        sub = QLabel("AI file assistant")
        sub.setObjectName("LogoSub")
        layout.addWidget(logo)
        layout.addWidget(sub)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, (label, glyph) in enumerate(NAV_ITEMS):
            btn = NavButton(label, glyph)
            btn.clicked.connect(lambda _=False, i=index: self._select(i))
            self.nav_group.addButton(btn, index)
            layout.addWidget(btn)

        layout.addStretch(1)
        self.engine_status = QLabel("  Engine: stopped")
        self.engine_status.setObjectName("Muted")
        self.engine_status.setContentsMargins(12, 0, 12, 8)
        layout.addWidget(self.engine_status)
        return sidebar

    def _topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(60)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)

        self.global_search = QLineEdit()
        self.global_search.setObjectName("GlobalSearch")
        self.global_search.setPlaceholderText("Search your files in plain language...   (Enter)")
        self.global_search.returnPressed.connect(self._global_search)
        layout.addWidget(self.global_search, 1)
        return bar

    # ------------------------------------------------------------------ tray
    def _setup_tray(self) -> None:
        self.tray = TrayController(
            self.config.ui.accent_color,
            on_show=self._restore_window,
            on_toggle_engine=self._toggle_engine,
            on_scan=lambda: self.engine.scan_now(),
            on_quit=self._quit,
        )
        self.tray.show()

    # ------------------------------------------------------------------ nav
    def _select(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        btn = self.nav_group.button(index)
        if btn:
            btn.setChecked(True)
        # Refresh data-driven views when shown.
        widget = self.stack.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _global_search(self) -> None:
        text = self.global_search.text().strip()
        if text:
            self._select(1)
            self.search_view.focus_search(text)

    # ------------------------------------------------------------------ events
    def _on_event(self, ev: Event) -> None:
        self.dashboard.on_event(ev)
        if ev.type in (EventType.ENGINE_STARTED, EventType.ENGINE_STOPPED):
            running = ev.type is EventType.ENGINE_STARTED
            self.engine_status.setText(f"  Engine: {'running' if running else 'stopped'}")
            self.tray.set_engine_running(running)
        if ev.type is EventType.SCAN_FINISHED and self.config.ui.show_notifications:
            self.tray.notify("Scan complete", f"Queued {ev.payload.get('queued', 0)} files.")
        if ev.type is EventType.NOTIFY and self.config.ui.show_notifications:
            self.tray.notify(ev.payload.get("title", "SmartFolders"), ev.payload.get("message", ""))

    # ------------------------------------------------------------------ config
    def _on_config_changed(self, config: AppConfig) -> None:
        self.config = config
        self.engine.apply_config(config)
        self._apply_theme()
        self.rules_view.refresh()

    def _apply_recommended_perf(self, perf) -> None:
        self.settings_view.apply_performance(perf)
        self._select(6)

    def _apply_theme(self) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet_for(self.config.ui.theme, self.config.ui.accent_color))

    # ------------------------------------------------------------------ engine
    def _toggle_engine(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        else:
            self.engine.start()

    # ------------------------------------------------------------------ window
    def _restore_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._allow_close = True
        from PyQt6.QtWidgets import QApplication

        self.engine.close()
        self.tray.hide()
        app = QApplication.instance()
        if app:
            app.quit()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if self._allow_close or not self.config.ui.close_to_tray or not self.tray.available:
            self.config.ui.window_width = self.width()
            self.config.ui.window_height = self.height()
            self.config.save()
            self.engine.close()
            event.accept()
            return
        # Hide to tray instead of quitting.
        event.ignore()
        self.hide()
        if self.config.ui.show_notifications:
            self.tray.notify("SmartFolders", "Still running in the background.")
