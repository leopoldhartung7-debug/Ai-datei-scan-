"""Plain data models shared across the application.

These dataclasses mirror the SQLite schema (see :mod:`smartfolders.core.database`)
but are deliberately storage-agnostic so they can be used in the UI, workers and
tests without importing the database layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..constants import Category, FileAction


@dataclass
class FileRecord:
    """A single tracked file and everything the engine knows about it."""

    path: str
    name: str = ""
    extension: str = ""
    size: int = 0
    category: Category = Category.OTHER
    confidence: float = 0.0
    tags: list[str] = field(default_factory=list)
    ocr_text: str = ""
    content_preview: str = ""
    sha256: str = ""
    phash: str = ""
    original_name: str = ""
    created_at: float = 0.0
    modified_at: float = 0.0
    indexed_at: float = 0.0
    is_duplicate: bool = False
    duplicate_of: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        p = Path(self.path)
        if not self.name:
            self.name = p.name
        if not self.extension:
            self.extension = p.suffix.lower()
        if not self.original_name:
            self.original_name = p.name

    @property
    def searchable_text(self) -> str:
        """Concatenated text used to build the search index / embeddings."""
        parts = [self.name, " ".join(self.tags), self.ocr_text, self.content_preview]
        return "\n".join(part for part in parts if part).strip()

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "size": self.size,
            "category": self.category.value,
            "confidence": self.confidence,
            "tags": ",".join(self.tags),
            "ocr_text": self.ocr_text,
            "content_preview": self.content_preview,
            "sha256": self.sha256,
            "phash": self.phash,
            "original_name": self.original_name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "indexed_at": self.indexed_at or time.time(),
            "is_duplicate": int(self.is_duplicate),
            "duplicate_of": self.duplicate_of,
        }

    @classmethod
    def from_row(cls, row) -> FileRecord:
        d = dict(row)
        tags = [t for t in (d.get("tags") or "").split(",") if t]
        return cls(
            id=d.get("id"),
            path=d["path"],
            name=d.get("name", ""),
            extension=d.get("extension", ""),
            size=d.get("size", 0),
            category=_safe_category(d.get("category")),
            confidence=d.get("confidence", 0.0),
            tags=tags,
            ocr_text=d.get("ocr_text", "") or "",
            content_preview=d.get("content_preview", "") or "",
            sha256=d.get("sha256", "") or "",
            phash=d.get("phash", "") or "",
            original_name=d.get("original_name", "") or "",
            created_at=d.get("created_at", 0.0) or 0.0,
            modified_at=d.get("modified_at", 0.0) or 0.0,
            indexed_at=d.get("indexed_at", 0.0) or 0.0,
            is_duplicate=bool(d.get("is_duplicate", 0)),
            duplicate_of=d.get("duplicate_of", "") or "",
        )


def _safe_category(value) -> Category:
    try:
        return Category(value)
    except (ValueError, TypeError):
        return Category.OTHER


# --------------------------------------------------------------------------- #
# Rules engine models
# --------------------------------------------------------------------------- #
class ConditionField(str, Enum):
    EXTENSION = "extension"
    NAME = "name"
    CATEGORY = "category"
    SIZE = "size"
    AGE_DAYS = "age_days"
    CONTENT = "content"          # matches ocr_text / preview
    TAG = "tag"


class ConditionOp(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"          # regex
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"                    # comma separated list membership


class ActionType(str, Enum):
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"
    TAG = "tag"
    DELETE = "delete"
    ARCHIVE = "archive"
    SET_CATEGORY = "set_category"
    IGNORE = "ignore"


@dataclass
class RuleCondition:
    field: ConditionField
    op: ConditionOp
    value: str

    def to_dict(self) -> dict:
        return {"field": self.field.value, "op": self.op.value, "value": self.value}

    @classmethod
    def from_dict(cls, d: dict) -> RuleCondition:
        return cls(ConditionField(d["field"]), ConditionOp(d["op"]), str(d["value"]))


@dataclass
class RuleAction:
    type: ActionType
    target: str = ""             # destination folder / pattern / tag / category

    def to_dict(self) -> dict:
        return {"type": self.type.value, "target": self.target}

    @classmethod
    def from_dict(cls, d: dict) -> RuleAction:
        return cls(ActionType(d["type"]), d.get("target", ""))


@dataclass
class Rule:
    """A user-defined automation rule."""

    name: str
    conditions: list[RuleCondition] = field(default_factory=list)
    actions: list[RuleAction] = field(default_factory=list)
    match_all: bool = True       # True=AND, False=OR
    enabled: bool = True
    priority: int = 100          # lower runs first
    stop_processing: bool = False
    id: int | None = None

    def to_row(self) -> dict:
        import json

        return {
            "id": self.id,
            "name": self.name,
            "enabled": int(self.enabled),
            "priority": self.priority,
            "match_all": int(self.match_all),
            "stop_processing": int(self.stop_processing),
            "conditions": json.dumps([c.to_dict() for c in self.conditions]),
            "actions": json.dumps([a.to_dict() for a in self.actions]),
        }

    @classmethod
    def from_row(cls, row) -> Rule:
        import json

        d = dict(row)
        conditions = [RuleCondition.from_dict(c) for c in json.loads(d.get("conditions") or "[]")]
        actions = [RuleAction.from_dict(a) for a in json.loads(d.get("actions") or "[]")]
        return cls(
            id=d.get("id"),
            name=d["name"],
            conditions=conditions,
            actions=actions,
            match_all=bool(d.get("match_all", 1)),
            enabled=bool(d.get("enabled", 1)),
            priority=d.get("priority", 100),
            stop_processing=bool(d.get("stop_processing", 0)),
        )


@dataclass
class HistoryEntry:
    """An audit-log row describing something the engine did to a file."""

    path: str
    action: FileAction
    detail: str = ""
    old_path: str = ""
    timestamp: float = field(default_factory=time.time)
    id: int | None = None

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "action": self.action.value,
            "detail": self.detail,
            "old_path": self.old_path,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_row(cls, row) -> HistoryEntry:
        d = dict(row)
        try:
            action = FileAction(d.get("action"))
        except (ValueError, TypeError):
            action = FileAction.SKIPPED
        return cls(
            id=d.get("id"),
            path=d["path"],
            action=action,
            detail=d.get("detail", "") or "",
            old_path=d.get("old_path", "") or "",
            timestamp=d.get("timestamp", 0.0) or 0.0,
        )
