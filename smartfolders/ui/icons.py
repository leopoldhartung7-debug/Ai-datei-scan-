"""Programmatically drawn icons - no binary assets needed.

Generating icons in code keeps the repo asset-free and lets every icon inherit
the current accent colour. Each function returns a :class:`QIcon`/:class:`QPixmap`
rendered with antialiased vector paths.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap


def app_icon(accent: str = "#5b8cff", size: int = 256) -> QIcon:
    """The SmartFolders mark: a rounded folder with a spark."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Rounded background tile.
    bg = QColor(accent)
    painter.setBrush(QBrush(bg))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)

    # Folder shape.
    s = size
    folder = QPainterPath()
    folder.moveTo(s * 0.22, s * 0.34)
    folder.lineTo(s * 0.42, s * 0.34)
    folder.lineTo(s * 0.48, s * 0.42)
    folder.lineTo(s * 0.78, s * 0.42)
    folder.lineTo(s * 0.78, s * 0.72)
    folder.lineTo(s * 0.22, s * 0.72)
    folder.closeSubpath()
    painter.setBrush(QBrush(QColor(255, 255, 255, 235)))
    painter.drawPath(folder)

    # Spark / AI dot.
    painter.setBrush(QBrush(bg))
    painter.drawEllipse(QRectF(s * 0.58, s * 0.5, s * 0.12, s * 0.12))
    painter.end()
    return QIcon(pm)


def tray_icon(accent: str = "#5b8cff", active: bool = True) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    color = QColor(accent) if active else QColor("#888a96")
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(8, 16, 48, 36), 8, 8)
    painter.drawRoundedRect(QRectF(8, 12, 24, 12), 6, 6)
    painter.end()
    return QIcon(pm)


_GLYPHS = {
    "dashboard": "▦",
    "search": "⌕",
    "files": "🗀",
    "rules": "⚙",
    "duplicates": "⧉",
    "optimize": "⚡",
    "settings": "⚙",
}


def glyph_icon(name: str, color: str = "#9aa0b4", size: int = 20) -> QIcon:
    """A simple monochrome glyph icon for the sidebar."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color)))
    font = QFont()
    font.setPointSize(int(size * 0.7))
    painter.setFont(font)
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, _GLYPHS.get(name, "•"))
    painter.end()
    return QIcon(pm)


def color_swatch(color: str, size: int = 16) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return QIcon(pm)


def icon_size() -> QSize:
    return QSize(18, 18)
