"""Reusable UI building blocks: stat cards, nav buttons, section cards, badges."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .icons import glyph_icon, icon_size


class NavButton(QPushButton):
    """A checkable sidebar navigation entry."""

    def __init__(self, label: str, glyph: str, parent: QWidget | None = None) -> None:
        super().__init__(f"  {label}", parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIcon(glyph_icon(glyph))
        self.setIconSize(icon_size())


class StatCard(QFrame):
    """A dashboard metric tile (big number + label)."""

    def __init__(self, label: str, value: str = "0", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        self._value = QLabel(value)
        self._value.setObjectName("StatValue")
        self._label = QLabel(label)
        self._label.setObjectName("StatLabel")
        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, value: str | int) -> None:
        self._value.setText(str(value))


class Card(QFrame):
    """A titled content container."""

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(12)
        if title:
            header = QLabel(title)
            header.setObjectName("CardTitle")
            self._layout.addWidget(header)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


class Badge(QLabel):
    """A small coloured status pill."""

    def __init__(self, text: str, color: str = "#5b8cff", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.set_color(color)

    def set_color(self, color: str) -> None:
        self.setStyleSheet(
            f"background: {color}33; color: {color}; border-radius: 9px;"
            f"padding: 3px 10px; font-weight: 600; font-size: 12px;"
        )


class ToggleRow(QWidget):
    """A labelled row with a description and a checkbox toggle on the right."""

    toggled = pyqtSignal(bool)

    def __init__(
        self, title: str, description: str = "", checked: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        from PyQt6.QtWidgets import QCheckBox

        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: 600;")
        text_col.addWidget(title_lbl)
        if description:
            desc = QLabel(description)
            desc.setObjectName("Muted")
            desc.setWordWrap(True)
            text_col.addWidget(desc)
        layout.addLayout(text_col, 1)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(checked)
        self.checkbox.toggled.connect(self.toggled.emit)
        layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, value: bool) -> None:
        self.checkbox.setChecked(value)


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2a3042;")
    line.setFixedHeight(1)
    return line
