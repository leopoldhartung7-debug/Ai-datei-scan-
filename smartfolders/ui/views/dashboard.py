"""Dashboard: live stats, activity feed and engine controls."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...constants import Category
from ...core.events import Event, EventType
from ...utils.paths import human_size
from ..widgets import Badge, Card, StatCard


class DashboardView(QWidget):
    def __init__(self, engine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._build()
        self.refresh()

    # ------------------------------------------------------------------ build
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Übersicht")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)

        self.status_badge = Badge("Bereit", "#9aa0b4")
        header.addWidget(self.status_badge)

        self.toggle_btn = QPushButton("Engine starten")
        self.toggle_btn.setObjectName("Primary")
        self.toggle_btn.clicked.connect(self._toggle_engine)
        header.addWidget(self.toggle_btn)

        self.scan_btn = QPushButton("Jetzt scannen")
        self.scan_btn.clicked.connect(lambda: self.engine.scan_now())
        header.addWidget(self.scan_btn)
        root.addLayout(header)

        # Stat cards
        grid = QGridLayout()
        grid.setSpacing(14)
        self.card_files = StatCard("Indexierte Dateien")
        self.card_classified = StatCard("Klassifiziert")
        self.card_ocr = StatCard("OCR verarbeitet")
        self.card_size = StatCard("Gesamtgröße")
        self.card_dupes = StatCard("Duplikate")
        self.card_queue = StatCard("In Warteschlange")
        for i, c in enumerate(
            [self.card_files, self.card_classified, self.card_ocr,
             self.card_size, self.card_dupes, self.card_queue]
        ):
            grid.addWidget(c, i // 3, i % 3)
        root.addLayout(grid)

        # Progress + activity
        lower = QHBoxLayout()
        lower.setSpacing(16)

        left_card = Card("Kategorien")
        self.cat_list = QListWidget()
        self.cat_list.setMaximumHeight(260)
        left_card.add(self.cat_list)
        lower.addWidget(left_card, 1)

        right_card = Card("Letzte Aktivität")
        self.activity = QListWidget()
        right_card.add(self.activity)
        lower.addWidget(right_card, 1)
        root.addLayout(lower, 1)

        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        self.scan_progress.setRange(0, 0)  # indeterminate
        root.addWidget(self.scan_progress)

    # ------------------------------------------------------------------ events
    def on_event(self, ev: Event) -> None:
        if ev.type in (EventType.STATS_UPDATED, EventType.FILE_INDEXED):
            self.refresh_stats()
        if ev.type is EventType.SCAN_STARTED:
            self.scan_progress.setVisible(True)
        if ev.type is EventType.SCAN_FINISHED:
            self.scan_progress.setVisible(False)
            self.refresh()
        if ev.type in (EventType.ENGINE_STARTED, EventType.ENGINE_STOPPED):
            self._sync_status()
        if ev.type in (
            EventType.FILE_CLASSIFIED, EventType.FILE_MOVED,
            EventType.FILE_RENAMED, EventType.DUPLICATE_FOUND, EventType.RULE_APPLIED,
        ):
            self._log_activity(ev)

    def _log_activity(self, ev: Event) -> None:
        ts = time.strftime("%H:%M:%S")

        def _cat_label(value: str) -> str:
            try:
                return Category(value).label
            except ValueError:
                return str(value)

        text = {
            EventType.FILE_CLASSIFIED: lambda p: (
                f"Erkannt als {_cat_label(p.get('category'))} "
                f"({int(p.get('confidence', 0) * 100)} %)"
            ),
            EventType.FILE_MOVED: lambda p: f"Verschoben → {p.get('new', '')}",
            EventType.FILE_RENAMED: lambda p: f"Umbenannt → {p.get('new', '')}",
            EventType.DUPLICATE_FOUND: lambda p: (
                f"{p.get('files', 0)} Duplikate in {p.get('groups', 0)} Gruppen"
            ),
            EventType.RULE_APPLIED: lambda p: f"Regel »{p.get('rule')}« angewendet",
        }.get(ev.type, lambda p: str(p))(ev.payload)
        path = ev.payload.get("path") or ev.payload.get("new") or ""
        name = path.split("/")[-1].split("\\")[-1] if path else ""
        item = QListWidgetItem(f"{ts}   {name}   —   {text}")
        self.activity.insertItem(0, item)
        while self.activity.count() > 200:
            self.activity.takeItem(self.activity.count() - 1)

    # ------------------------------------------------------------------ refresh
    def refresh(self) -> None:
        self.refresh_stats()
        self.refresh_categories()
        self._sync_status()

    def refresh_stats(self) -> None:
        db = self.engine.db
        stats = self.engine.stats
        self.card_files.set_value(db.count_files())
        self.card_classified.set_value(stats.files_classified)
        self.card_ocr.set_value(stats.ocr_done)
        self.card_size.set_value(human_size(db.total_size()))
        self.card_dupes.set_value(stats.duplicates_found)
        self.card_queue.set_value(stats.queue_size)

    def refresh_categories(self) -> None:
        self.cat_list.clear()
        counts = self.engine.db.category_counts()
        for cat_value, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            try:
                label = Category(cat_value).label
            except ValueError:
                label = cat_value
            self.cat_list.addItem(QListWidgetItem(f"{label}   ·   {count}"))
        if not counts:
            item = QListWidgetItem(
                "Noch keine Dateien indexiert.\nKlicke oben auf »Jetzt scannen«, "
                "um deine überwachten Ordner einzulesen."
            )
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.cat_list.addItem(item)

    def _sync_status(self) -> None:
        running = self.engine.is_running
        self.status_badge.setText("Läuft" if running else "Bereit")
        self.status_badge.set_color("#3ecf8e" if running else "#9aa0b4")
        self.toggle_btn.setText("Engine stoppen" if running else "Engine starten")

    def _toggle_engine(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        else:
            self.engine.start()
        self._sync_status()
