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
        title = QLabel("Einstellungen")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        save_btn = QPushButton("Änderungen speichern")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save)
        header.addWidget(save_btn)
        outer.addLayout(header)

        tabs = QTabWidget()
        tabs.addTab(self._folders_tab(), "Ordner")
        tabs.addTab(self._ai_tab(), "KI")
        tabs.addTab(self._performance_tab(), "Leistung")
        tabs.addTab(self._appearance_tab(), "Aussehen")
        tabs.addTab(self._maintenance_tab(), "Index && Daten")
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

        watched = Card("Überwachte Ordner")
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(200)
        watched.add(self.folder_list)
        row = QHBoxLayout()
        add_btn = QPushButton("Ordner hinzufügen")
        add_btn.clicked.connect(self._add_folder)
        rm_btn = QPushButton("Markierte entfernen")
        rm_btn.clicked.connect(self._remove_folder)
        row.addWidget(add_btn)
        row.addWidget(rm_btn)
        row.addStretch(1)
        watched.body().addLayout(row)
        layout.addWidget(watched)

        dest = Card("Zielordner für sortierte Dateien")
        dest.add(QLabel(
            "Von Regeln verschobene Dateien landen unter diesem Basis-Ordner:"
        ))
        drow = QHBoxLayout()
        self.dest_edit = QLineEdit()
        browse = QPushButton("Durchsuchen…")
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

        card = Card("KI-Funktionen")
        self.t_ai = ToggleRow(
            "KI aktivieren", "Hauptschalter für Klassifikation, OCR und Suche."
        )
        self.t_classify = ToggleRow(
            "Automatisch klassifizieren",
            "Neue Dateien automatisch erkennen und kategorisieren.",
        )
        self.t_rename = ToggleRow(
            "Automatisch umbenennen",
            "Smarte Dateinamen-Vorschläge automatisch übernehmen (invasiv).",
        )
        self.t_move = ToggleRow(
            "Automatisch verschieben",
            "Regeln dürfen Dateien automatisch verschieben (invasiv).",
        )
        self.t_ocr = ToggleRow(
            "OCR (Texterkennung)",
            "Text aus Bildern und gescannten PDFs lesen (benötigt Tesseract).",
        )
        self.t_search = ToggleRow(
            "Semantische Suche", "Embeddings für bedeutungsbasierte Suche aufbauen."
        )
        self.t_dupes = ToggleRow(
            "Duplikat-Erkennung", "Identische und ähnliche Dateien finden."
        )
        for t in (self.t_ai, self.t_classify, self.t_rename, self.t_move,
                  self.t_ocr, self.t_search, self.t_dupes):
            card.add(t)
        layout.addWidget(card)

        ocr_card = Card("OCR-Sprachen")
        self.ocr_lang = QLineEdit()
        self.ocr_lang.setPlaceholderText("z. B. deu+eng")
        ocr_card.add(self.ocr_lang)
        layout.addWidget(ocr_card)
        layout.addStretch(1)
        return self._scroll(page)

    # ------------------------------------------------------- performance tab
    def _performance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        card = Card("Ressourcennutzung")
        _intensity_de = {"eco": "Eco", "balanced": "Ausgewogen", "performance": "Leistung", "turbo": "Turbo"}
        self.intensity = QComboBox()
        for it in ScanIntensity:
            self.intensity.addItem(_intensity_de.get(it.value, it.value.title()), it)
        card.add(_labelled("Scan-Intensität", self.intensity))

        self.threads = QSpinBox()
        self.threads.setRange(1, 64)
        card.add(_labelled("Worker-Threads", self.threads))

        self.cpu_limit = QSlider(Qt.Orientation.Horizontal)
        self.cpu_limit.setRange(10, 100)
        self.cpu_label = QLabel("CPU-Limit: 70 %")
        self.cpu_limit.valueChanged.connect(
            lambda v: self.cpu_label.setText(f"CPU-Limit: {v} %")
        )
        card.add(self.cpu_label)
        card.add(self.cpu_limit)

        self.ram_limit = QSpinBox()
        self.ram_limit.setRange(128, 32768)
        self.ram_limit.setSuffix(" MB")
        card.add(_labelled("RAM-Budget", self.ram_limit))

        self.cache = QSpinBox()
        self.cache.setRange(32, 4096)
        self.cache.setSuffix(" MB")
        card.add(_labelled("Cache-Größe", self.cache))
        layout.addWidget(card)

        behaviour = Card("Hintergrundverhalten")
        self.t_battery = ToggleRow(
            "Akku-Modus", "Im Akkubetrieb herunterdrosseln, um Strom zu sparen."
        )
        self.t_autostart = ToggleRow(
            "Beim Anmelden starten", "SmartFolders automatisch beim Login starten."
        )
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

        card = Card("Erscheinungsbild")
        self.theme = QComboBox()
        self.theme.addItem("Dunkel", "dark")
        self.theme.addItem("Hell", "light")
        card.add(_labelled("Theme", self.theme))

        self.accent = QLineEdit()
        self.accent.setPlaceholderText("#2563eb")
        card.add(_labelled("Akzentfarbe (Hex)", self.accent))
        layout.addWidget(card)

        tray = Card("Fenster & System-Tray")
        self.t_min_tray = ToggleRow(
            "In den Tray minimieren",
            "Beim Minimieren weiter im System-Tray laufen lassen.",
        )
        self.t_close_tray = ToggleRow(
            "Beim Schließen im Tray bleiben",
            "Schließen des Fensters beendet die App nicht — sie läuft im Hintergrund weiter.",
        )
        self.t_notify = ToggleRow(
            "Benachrichtigungen", "Bei wichtigen Datei-Aktionen benachrichtigen."
        )
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

        card = Card("Suchindex")
        card.add(QLabel(
            "Volltextindex neu aufbauen oder Speicherplatz zurückgewinnen."
        ))
        rebuild = QPushButton("Suchindex neu aufbauen")
        rebuild.clicked.connect(lambda: self.engine.db.rebuild_search_index())
        vacuum = QPushButton("Datenbank komprimieren (VACUUM)")
        vacuum.clicked.connect(lambda: self.engine.db.vacuum())
        card.add(rebuild)
        card.add(vacuum)
        layout.addWidget(card)

        hist = Card("Verlauf")
        clear = QPushButton("Aktivitätsverlauf löschen")
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
