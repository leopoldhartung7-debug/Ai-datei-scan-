"""Core engine: data models, database, file watching and organizing."""

from __future__ import annotations

from .database import Database
from .events import Event, EventBus, EventType
from .models import FileRecord, HistoryEntry, Rule, RuleAction, RuleCondition
from .organizer import Organizer, OrganizeResult
from .rules import RuleEngine
from .scanner import Scanner
from .watcher import FolderWatcher

__all__ = [
    "Database",
    "Event",
    "EventBus",
    "EventType",
    "FileRecord",
    "HistoryEntry",
    "Rule",
    "RuleAction",
    "RuleCondition",
    "OrganizeResult",
    "Organizer",
    "RuleEngine",
    "Scanner",
    "FolderWatcher",
]
