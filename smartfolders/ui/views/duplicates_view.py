"""Duplicate finder screen - scan, review groups, reclaim space."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.organizer import send_to_trash
from ...utils.paths import human_size
from .search_view import open_in_file_manager


class _DupeWorker(QThread):
    done = pyqtSignal(object)

    def __init__(self, engine) -> None:
        super().__init__()
        self.engine = engine

    def run(self) -> None:
        groups = self.engine.find_duplicates()
        self.done.emit(groups)


class DuplicatesView(QWidget):
    def __init__(self, engine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._worker: _DupeWorker | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Duplikat-Finder")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        self.scan_btn = QPushButton("Duplikate suchen")
        self.scan_btn.setObjectName("Primary")
        self.scan_btn.clicked.connect(self._scan)
        header.addWidget(self.scan_btn)
        root.addLayout(header)

        info = QLabel(
            "Findet bytegleiche Dateien (exakt) sowie visuell ähnliche Bilder (perzeptuell). "
            "Hake die Kopien an, die du entfernen willst — sie landen im Papierkorb, "
            "werden also nicht endgültig gelöscht."
        )
        info.setObjectName("Muted")
        info.setWordWrap(True)
        root.addWidget(info)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Datei", "Größe", "Pfad"])
        self.tree.setColumnWidth(0, 280)
        self.tree.itemDoubleClicked.connect(self._open)
        root.addWidget(self.tree, 1)

        bottom = QHBoxLayout()
        self.summary = QLabel("")
        self.summary.setObjectName("Muted")
        bottom.addWidget(self.summary)
        bottom.addStretch(1)
        self.delete_btn = QPushButton("Markierte in den Papierkorb")
        self.delete_btn.setObjectName("Danger")
        self.delete_btn.clicked.connect(self._delete_ticked)
        self.delete_btn.setEnabled(False)
        bottom.addWidget(self.delete_btn)
        root.addLayout(bottom)

    def _scan(self) -> None:
        self.tree.clear()
        self.progress.setVisible(True)
        self.scan_btn.setEnabled(False)
        self._worker = _DupeWorker(self.engine)
        self._worker.done.connect(self._show_results)
        self._worker.start()

    def _show_results(self, groups) -> None:
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)
        self.delete_btn.setEnabled(bool(groups))
        total_waste = 0
        kind_de = {"exact": "Exakt", "similar": "Ähnlich"}
        for g in groups:
            total_waste += g.wasted_bytes
            label = (
                f"{kind_de.get(g.kind, g.kind.title())}-Gruppe   ·   "
                f"{g.count} Dateien   ·   {human_size(g.wasted_bytes)} freisetzbar"
            )
            parent = QTreeWidgetItem([label, "", ""])
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(True)
            for i, rec in enumerate(g.files):
                child = QTreeWidgetItem([rec.name, human_size(rec.size), rec.path])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                # Keep the first file unticked (suggested keeper).
                child.setCheckState(0, Qt.CheckState.Unchecked if i == 0 else Qt.CheckState.Checked)
                child.setData(0, Qt.ItemDataRole.UserRole, rec.path)
                parent.addChild(child)
        n_groups = self.tree.topLevelItemCount()
        if n_groups == 0:
            self.summary.setText("Keine Duplikate gefunden — deine Dateien sind ordentlich!")
        else:
            self.summary.setText(
                f"{n_groups} Gruppe(n)   ·   bis zu {human_size(total_waste)} freisetzbar"
            )

    def _delete_ticked(self) -> None:
        paths = []
        for i in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.CheckState.Checked:
                    paths.append(child.data(0, Qt.ItemDataRole.UserRole))
        if not paths:
            QMessageBox.information(
                self, "Nichts ausgewählt", "Hake zuerst die zu entfernenden Kopien an."
            )
            return
        if QMessageBox.question(
            self, "In den Papierkorb", f"{len(paths)} Datei(en) in den Papierkorb verschieben?"
        ) != QMessageBox.StandardButton.Yes:
            return
        for path in paths:
            send_to_trash(path)
            self.engine.db.delete_file(path)
        QMessageBox.information(
            self, "Fertig", f"{len(paths)} Datei(en) in den Papierkorb verschoben."
        )
        self._scan()

    def _open(self, item: QTreeWidgetItem) -> None:
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            open_in_file_manager(path)
