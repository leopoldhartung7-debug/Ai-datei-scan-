"""Semantic search screen with natural-language query support."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.paths import human_size
from ..widgets import Badge


class SearchView(QWidget):
    def __init__(self, engine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("KI-Suche")
        title.setObjectName("H1")
        root.addWidget(title)

        hint = QLabel(
            "Frag in natürlicher Sprache, z. B. »Zeig Rechnungen von Amazon«, "
            "»Wo ist mein Lebenslauf?«, »Coding-Screenshots« oder »PDFs vom März«.\n"
            "Ein Klick auf ein Ergebnis öffnet den Ordner und markiert die Datei."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        root.addWidget(hint)

        bar = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setObjectName("GlobalSearch")
        self.input.setPlaceholderText("Suchbegriff oder Frage …")
        self.input.returnPressed.connect(self.run_search)
        bar.addWidget(self.input, 1)
        btn = QPushButton("Suchen")
        btn.setObjectName("Primary")
        btn.clicked.connect(self.run_search)
        bar.addWidget(btn)
        root.addLayout(bar)

        self.backend_badge = Badge(self._backend_text(), self.engine.config.ui.accent_color)
        root.addWidget(self.backend_badge, 0, Qt.AlignmentFlag.AlignLeft)

        self.results = QListWidget()
        # A single click on a result opens its containing folder (and selects
        # the file in the OS file manager: Explorer /select, Finder reveal).
        self.results.itemClicked.connect(self._open_item)
        self.results.setCursor(Qt.CursorShape.PointingHandCursor)
        root.addWidget(self.results, 1)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        root.addWidget(self.status)

    def _backend_text(self) -> str:
        emb = self.engine.embeddings
        if emb and emb.is_ml_backend:
            return f"Semantisches Modell: {emb.model_name}"
        if emb:
            return "Semantisches Modell: leichter Fallback (KI-Extras für beste Qualität installieren)"
        return "Nur Stichwortsuche (semantische Suche deaktiviert)"

    def focus_search(self, text: str = "") -> None:
        if text:
            self.input.setText(text)
        self.input.setFocus()
        if text:
            self.run_search()

    def run_search(self) -> None:
        query = self.input.text().strip()
        self.results.clear()
        if not query:
            return
        hits = self.engine.query(query, limit=80)
        if not hits:
            self.status.setText("Keine Treffer gefunden.")
            return
        self.status.setText(f"{len(hits)} Treffer")
        for hit in hits:
            rec = hit.record
            exists = Path(rec.path).exists()
            tag = f"[{rec.category.label}]"
            mark = "" if exists else "   (fehlt)"
            match_de = {"keyword": "Stichwort", "semantic": "Bedeutung"}.get(
                hit.matched_on, hit.matched_on
            )
            text = (
                f"{rec.name}   {tag}\n"
                f"    {rec.path}   ·   {human_size(rec.size)}   ·   "
                f"Treffer: {match_de}   ·   Score: {hit.score:.2f}{mark}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, rec.path)
            self.results.addItem(item)

    def _open_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            open_in_file_manager(path)


def open_in_file_manager(path: str) -> None:
    """Reveal *path* in the OS file manager (Explorer / Finder / xdg)."""
    p = Path(path)
    try:
        if sys.platform.startswith("win"):
            if p.exists():
                subprocess.run(["explorer", "/select,", str(p)])
            else:
                os.startfile(str(p.parent))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)] if p.exists() else ["open", str(p.parent)])
        else:
            subprocess.run(["xdg-open", str(p.parent if not p.is_dir() else p)])
    except Exception:
        pass
