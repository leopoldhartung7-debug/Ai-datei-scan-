"""Theming: dark / light QSS stylesheets with a configurable accent colour.

Generated as f-strings so the accent colour from settings flows through every
widget. Kept in one place so the look stays consistent and is trivial to tweak.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    bg_elevated: str
    surface: str
    surface_hover: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    success: str
    warning: str
    danger: str


def dark_palette(accent: str = "#5b8cff") -> Palette:
    return Palette(
        name="dark",
        bg="#0f1117",
        bg_elevated="#151823",
        surface="#1b1f2e",
        surface_hover="#232838",
        border="#2a3042",
        text="#e8eaf0",
        text_muted="#9aa0b4",
        accent=accent,
        accent_hover=_lighten(accent),
        success="#3ecf8e",
        warning="#f5a623",
        danger="#ff5c6c",
    )


def light_palette(accent: str = "#3a6df0") -> Palette:
    return Palette(
        name="light",
        bg="#f4f6fb",
        bg_elevated="#ffffff",
        surface="#ffffff",
        surface_hover="#eef1f8",
        border="#dde2ec",
        text="#1a1d29",
        text_muted="#5c6478",
        accent=accent,
        accent_hover=_darken(accent),
        success="#1f9d62",
        warning="#c9820a",
        danger="#e23744",
    )


def build_stylesheet(p: Palette) -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "SF Pro Text", "Inter", "Helvetica Neue", Arial, sans-serif;
        font-size: 14px;
        color: {p.text};
        outline: none;
    }}
    QMainWindow, QWidget#RootWidget {{ background: {p.bg}; }}

    /* Sidebar */
    QWidget#Sidebar {{
        background: {p.bg_elevated};
        border-right: 1px solid {p.border};
    }}
    QLabel#Logo {{
        font-size: 19px;
        font-weight: 700;
        color: {p.text};
        padding: 18px 18px 6px 18px;
    }}
    QLabel#LogoSub {{
        font-size: 11px;
        color: {p.text_muted};
        padding: 0 18px 16px 18px;
    }}
    QPushButton#NavButton {{
        background: transparent;
        border: none;
        border-radius: 10px;
        text-align: left;
        padding: 11px 16px;
        margin: 2px 10px;
        color: {p.text_muted};
        font-weight: 500;
    }}
    QPushButton#NavButton:hover {{ background: {p.surface_hover}; color: {p.text}; }}
    QPushButton#NavButton:checked {{
        background: {p.accent};
        color: white;
        font-weight: 600;
    }}

    /* Top bar */
    QWidget#TopBar {{ background: {p.bg}; border-bottom: 1px solid {p.border}; }}
    QLineEdit#GlobalSearch {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 10px;
        padding: 9px 14px;
        font-size: 14px;
    }}
    QLineEdit#GlobalSearch:focus {{ border: 1px solid {p.accent}; }}

    /* Cards */
    QFrame#Card {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    QFrame#StatCard {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 14px;
    }}
    QLabel#StatValue {{ font-size: 28px; font-weight: 700; color: {p.text}; }}
    QLabel#StatLabel {{ font-size: 12px; color: {p.text_muted}; }}
    QLabel#CardTitle {{ font-size: 16px; font-weight: 600; }}
    QLabel#H1 {{ font-size: 24px; font-weight: 700; }}
    QLabel#Muted {{ color: {p.text_muted}; }}

    /* Buttons */
    QPushButton {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 9px;
        padding: 8px 16px;
        color: {p.text};
    }}
    QPushButton:hover {{ background: {p.surface_hover}; }}
    QPushButton#Primary {{
        background: {p.accent};
        border: none;
        color: white;
        font-weight: 600;
    }}
    QPushButton#Primary:hover {{ background: {p.accent_hover}; }}
    QPushButton#Danger {{ background: {p.danger}; border: none; color: white; }}

    /* Inputs */
    QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
        background: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 8px;
        padding: 7px 10px;
        selection-background-color: {p.accent};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {p.accent}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {p.bg_elevated};
        border: 1px solid {p.border};
        selection-background-color: {p.accent};
    }}

    /* Lists / tables / trees */
    QListWidget, QTreeWidget, QTableWidget, QListView, QTreeView {{
        background: {p.surface};
        border: 1px solid {p.border};
        border-radius: 12px;
        padding: 6px;
    }}
    QListWidget::item, QTreeWidget::item {{ padding: 8px; border-radius: 8px; }}
    QListWidget::item:selected, QTreeWidget::item:selected {{
        background: {p.accent}; color: white;
    }}
    QListWidget::item:hover, QTreeWidget::item:hover {{ background: {p.surface_hover}; }}
    QHeaderView::section {{
        background: {p.bg_elevated};
        color: {p.text_muted};
        border: none;
        border-bottom: 1px solid {p.border};
        padding: 8px;
        font-weight: 600;
    }}

    /* Checkboxes & toggles */
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px;
        border: 1px solid {p.border};
        border-radius: 5px;
        background: {p.bg_elevated};
    }}
    QCheckBox::indicator:checked {{ background: {p.accent}; border: 1px solid {p.accent}; }}

    /* Progress bar */
    QProgressBar {{
        background: {p.bg_elevated};
        border: 1px solid {p.border};
        border-radius: 8px;
        text-align: center;
        height: 16px;
    }}
    QProgressBar::chunk {{ background: {p.accent}; border-radius: 7px; }}

    /* Scrollbars */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 4px; }}
    QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 5px; min-width: 30px; }}

    /* Tabs */
    QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 12px; }}
    QTabBar::tab {{
        background: transparent; padding: 9px 18px; color: {p.text_muted};
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; }}

    QToolTip {{
        background: {p.bg_elevated}; color: {p.text};
        border: 1px solid {p.border}; padding: 6px; border-radius: 6px;
    }}
    QFrame#Badge {{ border-radius: 9px; padding: 2px 8px; }}
    """


def stylesheet_for(theme: str, accent: str) -> str:
    palette = dark_palette(accent) if theme != "light" else light_palette(accent)
    return build_stylesheet(palette)


def palette_for(theme: str, accent: str) -> Palette:
    return dark_palette(accent) if theme != "light" else light_palette(accent)


# --------------------------------------------------------------------------- #
def _clamp(v: int) -> int:
    return max(0, min(255, v))


def _lighten(hex_color: str, amount: int = 24) -> str:
    r, g, b = _to_rgb(hex_color)
    return _to_hex(_clamp(r + amount), _clamp(g + amount), _clamp(b + amount))


def _darken(hex_color: str, amount: int = 28) -> str:
    r, g, b = _to_rgb(hex_color)
    return _to_hex(_clamp(r - amount), _clamp(g - amount), _clamp(b - amount))


def _to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"
