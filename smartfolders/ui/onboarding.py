"""First-run onboarding wizard.

Shown once on a fresh install. Lets the user confirm watched folders, pick a
theme, and run hardware auto-optimization before the main window appears. This
is what makes the app feel like a polished product rather than a dev tool.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..config import AppConfig
from ..system.hardware import detect_hardware
from ..system.optimizer import recommend_settings


class OnboardingWizard(QWizard):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Willkommen bei SmartFolders")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(580, 480)
        self.addPage(_WelcomePage())
        self.folders_page = _FoldersPage(config)
        self.addPage(self.folders_page)
        self.optimize_page = _OptimizePage(config)
        self.addPage(self.optimize_page)
        self.addPage(_FinishPage())

    def apply(self) -> AppConfig:
        self.config.watched_folders = self.folders_page.folders()
        if self.optimize_page.recommended is not None:
            self.config.performance = self.optimize_page.recommended.performance
        self.config.first_run = False
        self.config.save()
        return self.config


class _WelcomePage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Dein KI-Dateiassistent")
        layout = QVBoxLayout(self)
        text = QLabel(
            "SmartFolders überwacht deine Ordner und klassifiziert, benennt um, "
            "entduplifiziert und indexiert deine Dateien automatisch — komplett offline.\n\n"
            "Alles bleibt auf deinem Gerät. Keine Cloud, keine Telemetrie.\n\n"
            "Lass uns in wenigen Schritten einrichten."
        )
        text.setWordWrap(True)
        layout.addWidget(text)


class _FoldersPage(QWizardPage):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setTitle("Welche Ordner sollen überwacht werden?")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Diese Ordner werden auf neue Dateien überwacht:"
        ))
        self.list = QListWidget()
        for folder in config.watched_folders:
            self.list.addItem(QListWidgetItem(folder))
        layout.addWidget(self.list)
        row = QHBoxLayout()
        add = QPushButton("Ordner hinzufügen")
        add.clicked.connect(self._add)
        remove = QPushButton("Entfernen")
        remove.clicked.connect(self._remove)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        layout.addLayout(row)

    def _add(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Ordner wählen")
        if folder:
            self.list.addItem(QListWidgetItem(folder))

    def _remove(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def folders(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]


class _OptimizePage(QWizardPage):
    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self.setTitle("Für deine Hardware optimieren")
        self.recommended = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Wir stimmen die Leistung auf deinen Rechner ab."
        ))
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.detail = QListWidget()
        layout.addWidget(self.detail)
        btn = QPushButton("Hardware analysieren")
        btn.clicked.connect(self._analyze)
        layout.addWidget(btn)

    def _analyze(self) -> None:
        hw = detect_hardware()
        rec = recommend_settings(hw)
        self.recommended = rec
        self.summary.setText(hw.summary())
        self.detail.clear()
        for r in rec.rationale:
            self.detail.addItem(QListWidgetItem(f"·   {r}"))


class _FinishPage(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Fertig — los geht's")
        layout = QVBoxLayout(self)
        text = QLabel(
            "SmartFolders ist bereit. Die Engine beginnt deine Ordner zu überwachen "
            "und du kannst jederzeit über das Dashboard einen kompletten Scan starten.\n\n"
            "Tipp: Probier oben die Suchleiste mit Sätzen wie »Zeig Rechnungen "
            "von Amazon« oder »Coding-Screenshots«."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
