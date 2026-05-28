"""Comprehensive settings center."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...config import AppConfig
from ...constants import ScanIntensity
from ..widgets import Card, ToggleRow


class SettingsView(QWidget):
    config_changed = pyqtSignal(object)  # emits AppConfig

    def __init__(self, engine, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.config = config
        self._build()
        self._load()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)

        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        save_btn = QPushButton("Save changes")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        header.addWidget(save_btn)
        outer.addLayout(header)

        tabs = QTabWidget()
        tabs.addTab(self._folders_tab(), "Folders")
        tabs.addTab(self._ai_tab(), "AI")
        tabs.addTab(self._performance_tab(), "Performance")
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._maintenance_tab(), "Index & Data")
        outer.addWidget(tabs, 1)

    def _scroll(self, inner: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QScrollArea.Shape.NoFrame)
        area.setWidget(inner)
        return area

    # ---------------------------------------------------------- folders tab
    def _folders_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        watched = Card("Watched folders")
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(200)
        watched.add(self.folder_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Add folder")
        add_btn.clicked.connect(self._add_folder)
        rm_btn = QPushButton("Remove selected")
        rm_btn.clicked.connect(self._remove_folder)
        row.addWidget(add_btn)
        row.addWidget(rm_btn)
        row.addStretch(1)
        watched.body().addLayout(row)
        layout.addWidget(watched)

        dest = Card("Organized destination")
        dest.add(QLabel("Files moved by rules are placed under this root folder:"))
        drow = QHBoxLayout()
        self.dest_edit = QLineEdit()
        browse = QPushButton("Browse")
        browse.clicked.connect(self._pick_dest)
        drow.addWidget(self.dest_edit, 1)
        drow.addWidget(browse)
        dest.body().addLayout(drow)
        layout.addWidget(dest)
        layout.addStretch(1)
        return self._scroll(page)

    # --------------------------------------------------------------- ai tab
    def _ai_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        card = Card("AI features")
        self.t_ai = ToggleRow("Enable AI", "Master switch for classification, OCR and search.")
        self.t_classify = ToggleRow("Auto-classify", "Categorize files automatically as they arrive.")
        self.t_rename = ToggleRow("Auto-rename", "Apply smart filename suggestions automatically (invasive).")
        self.t_move = ToggleRow("Auto-move", "Let rules move files automatically (invasive).")
        self.t_ocr = ToggleRow("OCR", "Read text from images and scanned PDFs (needs Tesseract).")
        self.t_search = ToggleRow("Semantic search", "Build embeddings for meaning-based search.")
        self.t_dupes = ToggleRow("Duplicate detection", "Find identical and similar files.")
        for t in (self.t_ai, self.t_classify, self.t_rename, self.t_move,
                  self.t_ocr, self.t_search, self.t_dupes):
            card.add(t)
        layout.addWidget(card)

        ocr_card = Card("OCR languages")
        self.ocr_lang = QLineEdit()
        self.ocr_lang.setPlaceholderText("e.g. deu+eng")
        ocr_card.add(self.ocr_lang)
        layout.addWidget(ocr_card)
        layout.addStretch(1)
        return self._scroll(page)

    # ------------------------------------------------------- performance tab
    def _performance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        card = Card("Resource usage")
        self.intensity = QComboBox()
        for it in ScanIntensity:
            self.intensity.addItem(it.value.title(), it)
        card.add(_labelled("Scan intensity", self.intensity))

        self.threads = QSpinBox()
        self.threads.setRange(1, 64)
        card.add(_labelled("Worker threads", self.threads))

        self.cpu_limit = QSlider(Qt.Orientation.Horizontal)
        self.cpu_limit.setRange(10, 100)
        self.cpu_label = QLabel("CPU limit: 70%")
        self.cpu_limit.valueChanged.connect(lambda v: self.cpu_label.setText(f"CPU limit: {v}%"))
        card.add(self.cpu_label)
        card.add(self.cpu_limit)

        self.ram_limit = QSpinBox()
        self.ram_limit.setRange(128, 32768)
        self.ram_limit.setSuffix(" MB")
        card.add(_labelled("RAM budget", self.ram_limit))

        self.cache = QSpinBox()
        self.cache.setRange(32, 4096)
        self.cache.setSuffix(" MB")
        card.add(_labelled("Cache size", self.cache))
        layout.addWidget(card)

        behaviour = Card("Background behaviour")
        self.t_battery = ToggleRow("Throttle on battery", "Slow down to save power when unplugged.")
        self.t_autostart = ToggleRow("Run at login", "Launch SmartFolders automatically.")
        behaviour.add(self.t_battery)
        behaviour.add(self.t_autostart)
        layout.addWidget(behaviour)
        layout.addStretch(1)
        return self._scroll(page)

    # -------------------------------------------------------- appearance tab
    def _appearance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        card = Card("Theme")
        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        card.add(_labelled("Theme", self.theme))

        self.accent = QLineEdit()
        self.accent.setPlaceholderText("#5b8cff")
        card.add(_labelled("Accent colour (hex)", self.accent))
        layout.addWidget(card)

        tray = Card("Window & tray")
        self.t_min_tray = ToggleRow("Minimize to tray", "Keep running in the system tray when minimized.")
        self.t_close_tray = ToggleRow("Close to tray", "Closing the window keeps the engine running.")
        self.t_notify = ToggleRow("Show notifications", "Notify on important file actions.")
        tray.add(self.t_min_tray)
        tray.add(self.t_close_tray)
        tray.add(self.t_notify)
        layout.addWidget(tray)
        layout.addStretch(1)
        return self._scroll(page)

    # ------------------------------------------------------- maintenance tab
    def _maintenance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        card = Card("Search index")
        card.add(QLabel("Rebuild the full-text index or reclaim disk space."))
        rebuild = QPushButton("Rebuild search index")
        rebuild.clicked.connect(lambda: self.engine.db.rebuild_search_index())
        vacuum = QPushButton("Compact database (VACUUM)")
        vacuum.clicked.connect(lambda: self.engine.db.vacuum())
        card.add(rebuild)
        card.add(vacuum)
        layout.addWidget(card)

        hist = Card("History")
        clear = QPushButton("Clear activity history")
        clear.setObjectName("Danger")
        clear.clicked.connect(lambda: self.engine.db.clear_history())
        hist.add(clear)
        layout.addWidget(hist)
        layout.addStretch(1)
        return self._scroll(page)

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        c = self.config
        self.folder_list.clear()
        for folder in c.watched_folders:
            self.folder_list.addItem(QListWidgetItem(folder))
        self.dest_edit.setText(c.organized_root)

        self.t_ai.set_checked(c.ai.enabled)
        self.t_classify.set_checked(c.ai.auto_classify)
        self.t_rename.set_checked(c.ai.auto_rename)
        self.t_move.set_checked(c.ai.auto_move)
        self.t_ocr.set_checked(c.ai.ocr_enabled)
        self.t_search.set_checked(c.ai.semantic_search)
        self.t_dupes.set_checked(c.ai.duplicate_detection)
        self.ocr_lang.setText(c.ai.ocr_languages)

        self.intensity.setCurrentIndex(self.intensity.findData(c.performance.intensity))
        self.threads.setValue(c.performance.max_worker_threads)
        self.cpu_limit.setValue(c.performance.cpu_limit_percent)
        self.cpu_label.setText(f"CPU limit: {c.performance.cpu_limit_percent}%")
        self.ram_limit.setValue(c.performance.ram_limit_mb)
        self.cache.setValue(c.performance.cache_size_mb)
        self.t_battery.set_checked(c.performance.throttle_on_battery)

        from ...system import autostart
        self.t_autostart.set_checked(autostart.is_enabled())

        self.theme.setCurrentIndex(self.theme.findData(c.ui.theme))
        self.accent.setText(c.ui.accent_color)
        self.t_min_tray.set_checked(c.ui.minimize_to_tray)
        self.t_close_tray.set_checked(c.ui.close_to_tray)
        self.t_notify.set_checked(c.ui.show_notifications)

    def apply_performance(self, perf) -> None:
        """Called by the optimizer view to push recommended values in."""
        self.config.performance = perf
        self.intensity.setCurrentIndex(self.intensity.findData(perf.intensity))
        self.threads.setValue(perf.max_worker_threads)
        self.cpu_limit.setValue(perf.cpu_limit_percent)
        self.ram_limit.setValue(perf.ram_limit_mb)
        self.cache.setValue(perf.cache_size_mb)
        self._save()

    # ------------------------------------------------------------------ save
    def _save(self) -> None:
        c = self.config
        c.watched_folders = [self.folder_list.item(i).text() for i in range(self.folder_list.count())]
        c.organized_root = self.dest_edit.text().strip()

        c.ai.enabled = self.t_ai.is_checked()
        c.ai.auto_classify = self.t_classify.is_checked()
        c.ai.auto_rename = self.t_rename.is_checked()
        c.ai.auto_move = self.t_move.is_checked()
        c.ai.ocr_enabled = self.t_ocr.is_checked()
        c.ai.semantic_search = self.t_search.is_checked()
        c.ai.duplicate_detection = self.t_dupes.is_checked()
        c.ai.ocr_languages = self.ocr_lang.text().strip() or "deu+eng"

        c.performance.intensity = self.intensity.currentData()
        c.performance.max_worker_threads = self.threads.value()
        c.performance.cpu_limit_percent = self.cpu_limit.value()
        c.performance.ram_limit_mb = self.ram_limit.value()
        c.performance.cache_size_mb = self.cache.value()
        c.performance.throttle_on_battery = self.t_battery.is_checked()

        c.ui.theme = self.theme.currentData()
        c.ui.accent_color = self.accent.text().strip() or "#5b8cff"
        c.ui.minimize_to_tray = self.t_min_tray.is_checked()
        c.ui.close_to_tray = self.t_close_tray.is_checked()
        c.ui.show_notifications = self.t_notify.is_checked()

        from ...system import autostart
        if self.t_autostart.is_checked():
            autostart.enable()
        else:
            autostart.disable()

        c.save()
        self.config_changed.emit(c)

    # ----------------------------------------------------------------- helpers
    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder to watch")
        if folder:
            self.folder_list.addItem(QListWidgetItem(folder))

    def _remove_folder(self) -> None:
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))

    def _pick_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select organized destination")
        if folder:
            self.dest_edit.setText(folder)


def _labelled(label: str, widget: QWidget) -> QWidget:
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label)
    lbl.setMinimumWidth(140)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return container
