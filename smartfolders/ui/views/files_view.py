"""Browsable, filterable table of every indexed file."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...constants import Category
from ...utils.paths import human_size
from .search_view import open_in_file_manager


class FilesView(QWidget):
    def __init__(self, engine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Dateien")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)

        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Nach Name filtern …")
        self.filter_box.setFixedWidth(220)
        self.filter_box.textChanged.connect(self.refresh)
        header.addWidget(self.filter_box)

        self.category_combo = QComboBox()
        self.category_combo.addItem("Alle Kategorien", "")
        for cat in Category:
            self.category_combo.addItem(cat.label, cat.value)
        self.category_combo.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.category_combo)

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Kategorie", "Größe", "Tags", "Indexiert"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemDoubleClicked.connect(self._open_row)
        root.addWidget(self.table, 1)

        self.count_label = QLabel("")
        self.count_label.setObjectName("Muted")
        root.addWidget(self.count_label)

    def refresh(self) -> None:
        name_filter = self.filter_box.text().strip().lower()
        cat_filter = self.category_combo.currentData()
        records = self.engine.db.all_files(limit=2000)
        rows = []
        for rec in records:
            if cat_filter and rec.category.value != cat_filter:
                continue
            if name_filter and name_filter not in rec.name.lower():
                continue
            rows.append(rec)

        self.table.setRowCount(len(rows))
        for r, rec in enumerate(rows):
            self._set(r, 0, rec.name, rec.path)
            self._set(r, 1, rec.category.label)
            self._set(r, 2, human_size(rec.size))
            self._set(r, 3, ", ".join(rec.tags[:6]))
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(rec.indexed_at)) if rec.indexed_at else ""
            self._set(r, 4, ts)
        self.count_label.setText(f"{len(rows)} Datei(en)")

    def _set(self, row: int, col: int, text: str, path: str | None = None) -> None:
        item = QTableWidgetItem(text)
        if path:
            item.setData(Qt.ItemDataRole.UserRole, path)
        self.table.setItem(row, col, item)

    def _open_row(self, item: QTableWidgetItem) -> None:
        name_item = self.table.item(item.row(), 0)
        path = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        if path:
            open_in_file_manager(path)
