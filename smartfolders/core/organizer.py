"""The action executor: safely moves, renames, copies, archives and deletes.

Everything that mutates the filesystem funnels through here so we have a single
place that:

* never overwrites an existing file (uses :func:`unique_destination`),
* records every action in the history table,
* keeps the database's path in sync,
* supports a *dry-run* mode for previews,
* sends files to the OS recycle bin / trash when possible instead of hard delete.

It is platform aware (Windows + macOS + Linux) for the trash operation.
"""

from __future__ import annotations

import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ..constants import FileAction
from ..utils.logging import get_logger
from ..utils.paths import ensure_dir, unique_destination
from .database import Database
from .events import EventBus, EventType
from .models import ActionType, FileRecord, HistoryEntry, Rule, RuleAction
from .rules import render_target

log = get_logger(__name__)


@dataclass
class OrganizeResult:
    record: FileRecord
    performed: list[str]
    final_path: str
    skipped: bool = False
    error: str = ""


class Organizer:
    """Executes rule actions against the filesystem."""

    def __init__(
        self,
        db: Database,
        organized_root: str | Path,
        bus: EventBus | None = None,
        dry_run: bool = False,
    ) -> None:
        self.db = db
        self.organized_root = Path(organized_root)
        self.bus = bus
        self.dry_run = dry_run

    # ------------------------------------------------------------------ apply
    def apply_actions(
        self, record: FileRecord, actions: list[tuple[Rule, RuleAction]]
    ) -> OrganizeResult:
        """Apply an ordered list of ``(rule, action)`` pairs to *record*."""
        performed: list[str] = []
        current_path = Path(record.path)

        for _rule, action in actions:
            try:
                current_path = self._dispatch(action, record, current_path, performed)
                if action.type is ActionType.IGNORE:
                    return OrganizeResult(record, performed, str(current_path), skipped=True)
                if current_path is None:  # deleted
                    return OrganizeResult(record, performed, "", skipped=False)
            except Exception as exc:  # pragma: no cover - filesystem edge cases
                log.exception("Action %s failed for %s", action.type, record.path)
                self._history(record.path, FileAction.ERROR, f"{action.type.value}: {exc}")
                return OrganizeResult(record, performed, str(current_path), error=str(exc))

        record.path = str(current_path)
        record.name = current_path.name
        return OrganizeResult(record, performed, str(current_path))

    def _dispatch(
        self,
        action: RuleAction,
        record: FileRecord,
        current: Path,
        performed: list[str],
    ) -> Path | None:
        kind = action.type
        if kind is ActionType.IGNORE:
            performed.append("ignored")
            return current
        if kind is ActionType.TAG:
            self._tag(record, action.target)
            performed.append(f"tagged:{action.target}")
            return current
        if kind is ActionType.SET_CATEGORY:
            performed.append(f"category:{action.target}")
            return current
        if kind is ActionType.RENAME:
            return self._rename(record, current, action.target, performed)
        if kind is ActionType.MOVE:
            return self._move(record, current, action.target, performed)
        if kind is ActionType.ARCHIVE:
            return self._move(record, current, action.target or "Archives", performed, archive=True)
        if kind is ActionType.COPY:
            self._copy(record, current, action.target, performed)
            return current
        if kind is ActionType.DELETE:
            self._delete(record, current, performed)
            return None
        return current

    # --------------------------------------------------------------- actions
    def _resolve_dir(self, target: str, record: FileRecord) -> Path:
        rendered = render_target(target, record)
        target_path = Path(rendered)
        if not target_path.is_absolute():
            target_path = self.organized_root / target_path
        return target_path

    def _move(
        self,
        record: FileRecord,
        current: Path,
        target: str,
        performed: list[str],
        archive: bool = False,
    ) -> Path:
        dest_dir = self._resolve_dir(target, record)
        dest = unique_destination(dest_dir / current.name)
        if self.dry_run:
            performed.append(f"would-move -> {dest}")
            return current
        ensure_dir(dest.parent)
        shutil.move(str(current), str(dest))
        self.db.update_file_path(str(current), str(dest))
        action = FileAction.MOVED
        self._history(str(dest), action, f"from {current}", old_path=str(current))
        self._emit(EventType.FILE_MOVED, old=str(current), new=str(dest), record=record)
        performed.append(f"moved -> {dest}")
        log.info("Moved %s -> %s", current, dest)
        return dest

    def _rename(
        self, record: FileRecord, current: Path, new_name: str, performed: list[str]
    ) -> Path:
        rendered = render_target(new_name, record)
        # Preserve the original extension if the new name has none.
        if not Path(rendered).suffix:
            rendered += current.suffix
        dest = unique_destination(current.with_name(_sanitize(rendered)))
        if self.dry_run:
            performed.append(f"would-rename -> {dest.name}")
            return current
        current.rename(dest)
        self.db.update_file_path(str(current), str(dest))
        self._history(str(dest), FileAction.RENAMED, f"from {current.name}", old_path=str(current))
        self._emit(EventType.FILE_RENAMED, old=str(current), new=str(dest), record=record)
        performed.append(f"renamed -> {dest.name}")
        log.info("Renamed %s -> %s", current.name, dest.name)
        return dest

    def _copy(self, record: FileRecord, current: Path, target: str, performed: list[str]) -> None:
        dest_dir = self._resolve_dir(target, record)
        dest = unique_destination(dest_dir / current.name)
        if self.dry_run:
            performed.append(f"would-copy -> {dest}")
            return
        ensure_dir(dest.parent)
        shutil.copy2(str(current), str(dest))
        self._history(str(dest), FileAction.MOVED, f"copied from {current}", old_path=str(current))
        performed.append(f"copied -> {dest}")

    def _delete(self, record: FileRecord, current: Path, performed: list[str]) -> None:
        if self.dry_run:
            performed.append("would-delete")
            return
        send_to_trash(current)
        self.db.delete_file(str(current))
        self._history(str(current), FileAction.DELETED, "moved to trash")
        performed.append("deleted")

    def _tag(self, record: FileRecord, tag: str) -> None:
        tags = render_target(tag, record)
        for t in tags.split(","):
            t = t.strip()
            if t and t not in record.tags:
                record.tags.append(t)
        if not self.dry_run and record.id:
            self.db.upsert_file(record)

    # ------------------------------------------------------------------ utils
    def _history(self, path: str, action: FileAction, detail: str, old_path: str = "") -> None:
        if self.dry_run:
            return
        self.db.add_history(HistoryEntry(path=path, action=action, detail=detail, old_path=old_path))

    def _emit(self, event: EventType, **payload) -> None:
        if self.bus and not self.dry_run:
            self.bus.emit(event, **payload)


# --------------------------------------------------------------------------- #
# Cross-platform helpers
# --------------------------------------------------------------------------- #
def _sanitize(name: str) -> str:
    """Strip characters that are illegal in filenames on Windows/macOS."""
    illegal = '<>:"/\\|?*'
    cleaned = "".join("_" if c in illegal else c for c in name).strip(" .")
    return cleaned or f"file_{int(time.time())}"


def send_to_trash(path: str | Path) -> None:
    """Send *path* to the OS recycle bin / trash, falling back to deletion.

    Tries the optional ``send2trash`` package first (best cross-platform
    behaviour on Windows + macOS), then a platform-native approach, and only as
    a last resort performs a permanent delete.
    """
    path = Path(path)
    if not path.exists():
        return
    try:
        import send2trash  # type: ignore

        send2trash.send2trash(str(path))
        return
    except Exception:
        pass

    if sys.platform == "darwin":  # macOS: move to ~/.Trash
        try:
            trash = Path.home() / ".Trash"
            ensure_dir(trash)
            shutil.move(str(path), str(unique_destination(trash / path.name)))
            return
        except Exception:  # pragma: no cover
            log.warning("macOS trash move failed for %s", path, exc_info=True)
    # Last resort - permanent delete.
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    except OSError:  # pragma: no cover
        log.warning("Could not delete %s", path, exc_info=True)
