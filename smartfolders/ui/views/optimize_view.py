"""AI-optimized settings: detect hardware and auto-tune performance."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...system.hardware import detect_hardware
from ...system.optimizer import recommend_settings
from ..widgets import Card, StatCard


class _DetectWorker(QThread):
    done = pyqtSignal(object, object)

    def run(self) -> None:
        hw = detect_hardware()
        rec = recommend_settings(hw)
        self.done.emit(hw, rec)


class OptimizeView(QWidget):
    def __init__(self, engine, on_apply, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._on_apply = on_apply
        self._recommendation = None
        self._worker: _DetectWorker | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("KI-Optimierung")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        self.detect_btn = QPushButton("Hardware analysieren")
        self.detect_btn.setObjectName("Primary")
        self.detect_btn.clicked.connect(self._detect)
        header.addWidget(self.detect_btn)
        root.addLayout(header)

        intro = QLabel(
            "SmartFolders prüft CPU, RAM, Speichermedium und GPU und empfiehlt die "
            "passende Scan-Intensität, Thread-Anzahl, Cache-Größe und KI-Funktionen "
            "für genau deine Hardware. Empfehlung prüfen — mit einem Klick übernehmen."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.hw_summary = QLabel("Klicke auf »Hardware analysieren«, um zu starten.")
        self.hw_summary.setWordWrap(True)
        root.addWidget(self.hw_summary)

        stats_row = QHBoxLayout()
        self.card_workers = StatCard("Worker-Threads", "–")
        self.card_intensity = StatCard("Scan-Intensität", "–")
        self.card_cache = StatCard("Cache-Größe", "–")
        self.card_ram = StatCard("RAM-Budget", "–")
        for c in (self.card_workers, self.card_intensity, self.card_cache, self.card_ram):
            stats_row.addWidget(c)
        root.addLayout(stats_row)

        rationale_card = Card("Warum diese Einstellungen?")
        self.rationale = QListWidget()
        rationale_card.add(self.rationale)
        root.addWidget(rationale_card, 1)

        self.apply_btn = QPushButton("Empfehlung übernehmen")
        self.apply_btn.setObjectName("Primary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        root.addWidget(self.apply_btn)

    def _detect(self) -> None:
        self.detect_btn.setEnabled(False)
        self.hw_summary.setText("Analysiere Hardware …")
        self._worker = _DetectWorker()
        self._worker.done.connect(self._show)
        self._worker.start()

    def _show(self, hw, rec) -> None:
        self.detect_btn.setEnabled(True)
        self._recommendation = rec
        self.hw_summary.setText(hw.summary())
        perf = rec.performance
        self.card_workers.set_value(perf.max_worker_threads)
        self.card_intensity.set_value(perf.intensity.value.title())
        self.card_cache.set_value(f"{perf.cache_size_mb} MB")
        self.card_ram.set_value(f"{perf.ram_limit_mb} MB")
        self.rationale.clear()
        for reason in rec.rationale:
            self.rationale.addItem(QListWidgetItem(f"-  {reason}"))
        self.apply_btn.setEnabled(True)

    def _apply(self) -> None:
        if self._recommendation:
            self._on_apply(self._recommendation.performance)
