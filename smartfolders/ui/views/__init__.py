"""Individual application screens, each a self-contained QWidget."""

from __future__ import annotations

from .dashboard import DashboardView
from .duplicates_view import DuplicatesView
from .files_view import FilesView
from .optimize_view import OptimizeView
from .rules_view import RulesView
from .search_view import SearchView
from .settings_view import SettingsView

__all__ = [
    "DashboardView",
    "DuplicatesView",
    "FilesView",
    "OptimizeView",
    "RulesView",
    "SearchView",
    "SettingsView",
]
