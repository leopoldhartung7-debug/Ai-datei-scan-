"""The SmartFolders engine - the orchestrator that ties everything together.

Responsibilities:

* Own the long-lived services (DB, classifier, OCR, embeddings, search, rules).
* Watch folders and run an initial scan.
* Run every detected file through the processing pipeline on a bounded thread
  pool, throttled to respect the user's performance settings.
* Publish progress / results on the :class:`EventBus` so the UI stays decoupled.

The pipeline per file:
    detect -> extract text -> OCR (if image/scan) -> classify -> embed/index
    -> evaluate rules -> (optionally) rename + move -> record history.

The engine is UI-agnostic and fully usable headless (see ``__main__`` CLI).
"""

from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .ai.classifier import FileClassifier
from .ai.content import extract_preview
from .ai.duplicates import DuplicateFinder
from .ai.embeddings import EmbeddingEngine
from .ai.ocr import OCREngine
from .ai.rename import SmartRenamer
from .ai.search import SemanticSearch
from .config import AppConfig
from .constants import (
    IMAGE_EXTENSIONS,
    OCR_EXTENSIONS,
    PDF_EXTENSIONS,
    FileAction,
)
from .core.database import Database
from .core.events import EventBus, EventType
from .core.models import ActionType, FileRecord, HistoryEntry
from .core.organizer import Organizer
from .core.rules import RuleEngine, default_rules
from .core.scanner import Scanner
from .core.watcher import FolderWatcher
from .utils.logging import get_logger

log = get_logger(__name__)


class Stats:
    """Mutable, thread-safe-ish counters for the dashboard."""

    def __init__(self) -> None:
        self.files_processed = 0
        self.files_classified = 0
        self.files_renamed = 0
        self.files_moved = 0
        self.ocr_done = 0
        self.duplicates_found = 0
        self.errors = 0
        self.queue_size = 0
        self._lock = threading.Lock()

    def bump(self, **kw: int) -> None:
        with self._lock:
            for key, val in kw.items():
                setattr(self, key, getattr(self, key) + val)

    def as_dict(self) -> dict:
        return {
            "files_processed": self.files_processed,
            "files_classified": self.files_classified,
            "files_renamed": self.files_renamed,
            "files_moved": self.files_moved,
            "ocr_done": self.ocr_done,
            "duplicates_found": self.duplicates_found,
            "errors": self.errors,
            "queue_size": self.queue_size,
        }


class SmartFoldersEngine:
    """Central application engine."""

    def __init__(self, config: AppConfig, bus: EventBus | None = None) -> None:
        self.config = config
        self.bus = bus or EventBus()
        self.stats = Stats()

        self.db = Database(config.database_path)
        self._seed_rules_if_empty()

        # AI services (lazy-friendly; all degrade gracefully)
        self.embeddings = (
            EmbeddingEngine(config.ai.embedding_model)
            if config.ai.enabled and config.ai.semantic_search
            else None
        )
        self.classifier = FileClassifier(self.embeddings, use_ml=config.ai.enabled)
        self.ocr = (
            OCREngine(config.ai.ocr_languages)
            if config.ai.enabled and config.ai.ocr_enabled
            else None
        )
        self.renamer = SmartRenamer()
        self.search = SemanticSearch(self.db, self.embeddings)
        self.duplicates = DuplicateFinder(
            perceptual=config.ai.perceptual_image_match,
            phash_threshold=config.ai.perceptual_threshold,
        )

        self.scanner = Scanner()
        self.rule_engine = RuleEngine(self.db.get_rules(enabled_only=True))
        self.organizer = Organizer(self.db, config.organized_root, self.bus)
        self.watcher = FolderWatcher(self._on_file_ready)

        # Worker pool + queue
        self._queue: queue.Queue[str] = queue.Queue()
        self._executor: ThreadPoolExecutor | None = None
        self._dispatcher: threading.Thread | None = None
        self._running = False
        self._paused = threading.Event()
        self._stop = threading.Event()
        self._inflight: set[str] = set()
        self._inflight_lock = threading.Lock()

    # --------------------------------------------------------------- lifecycle
    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._paused.clear()
        workers = max(1, self.config.performance.max_worker_threads)
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="sf-worker")
        self._dispatcher = threading.Thread(target=self._dispatch_loop, name="sf-dispatch", daemon=True)
        self._dispatcher.start()
        self.watcher.set_folders(self.config.watched_folders)
        self.watcher.start()
        self._running = True
        self.bus.emit(EventType.ENGINE_STARTED, backend=self.watcher.backend)
        log.info("Engine started (%d workers, watcher=%s)", workers, self.watcher.backend)

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        self.watcher.stop()
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        self._running = False
        self.bus.emit(EventType.ENGINE_STOPPED)
        log.info("Engine stopped")

    def pause(self) -> None:
        self._paused.set()
        self.bus.emit(EventType.ENGINE_PAUSED)

    def resume(self) -> None:
        self._paused.clear()
        self.bus.emit(EventType.ENGINE_RESUMED)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    def close(self) -> None:
        self.stop()
        self.db.close()

    # ------------------------------------------------------------------ scans
    def scan_now(self, folders: list[str] | None = None) -> None:
        """Queue an initial bulk scan of *folders* (defaults to watched)."""
        folders = folders or self.config.watched_folders
        threading.Thread(
            target=self._scan_worker, args=(folders,), name="sf-scan", daemon=True
        ).start()

    def _scan_worker(self, folders: list[str]) -> None:
        self.bus.emit(EventType.SCAN_STARTED, folders=folders)
        count = 0
        for path in self.scanner.scan_many([Path(f) for f in folders]):
            self.enqueue(str(path))
            count += 1
            if count % 50 == 0:
                self.bus.emit(EventType.SCAN_PROGRESS, queued=count)
        self.bus.emit(EventType.SCAN_FINISHED, queued=count)
        log.info("Initial scan queued %d files", count)

    # ------------------------------------------------------------------ queue
    def enqueue(self, path: str) -> None:
        with self._inflight_lock:
            if path in self._inflight:
                return
            self._inflight.add(path)
        self._queue.put(path)
        self.stats.queue_size = self._queue.qsize()

    def _on_file_ready(self, path: Path) -> None:
        self.bus.emit(EventType.FILE_DETECTED, path=str(path))
        self.enqueue(str(path))

    def _dispatch_loop(self) -> None:
        """Pull paths off the queue and hand them to the worker pool."""
        while not self._stop.is_set():
            try:
                path = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if self._paused.is_set():
                # Re-queue and back off while paused.
                self._queue.put(path)
                time.sleep(0.5)
                continue
            self._throttle()
            if self._executor:
                self._executor.submit(self._safe_process, path)
            self.stats.queue_size = self._queue.qsize()

    def _safe_process(self, path: str) -> None:
        try:
            self.process_file(path)
        except Exception:  # pragma: no cover
            log.exception("Pipeline failed for %s", path)
            self.stats.bump(errors=1)
            self.bus.emit(EventType.FILE_ERROR, path=path)
        finally:
            with self._inflight_lock:
                self._inflight.discard(path)

    # ---------------------------------------------------------------- throttle
    def _throttle(self) -> None:
        """Soft CPU throttle: sleep proportionally when over the configured cap."""
        cap = self.config.performance.cpu_limit_percent
        if cap >= 100:
            return
        try:
            import psutil

            usage = psutil.cpu_percent(interval=None)
            if usage > cap:
                time.sleep(min(0.5, (usage - cap) / 100.0))
        except Exception:
            # No psutil: a tiny fixed yield keeps Eco mode gentle.
            if self.config.performance.intensity.value == "eco":
                time.sleep(0.05)

    # --------------------------------------------------------------- pipeline
    def process_file(self, path: str) -> FileRecord | None:
        """Run the full processing pipeline for a single file."""
        p = Path(path)
        if not p.exists() or not p.is_file():
            return None

        stat = p.stat()
        record = self.db.get_file(path) or FileRecord(path=path)
        record.size = stat.st_size
        record.modified_at = stat.st_mtime
        record.created_at = getattr(stat, "st_ctime", stat.st_mtime)

        ext = p.suffix.lower()

        # 1) Extract textual content (cheap) -----------------------------------
        text = extract_preview(p)
        record.content_preview = text[:2000]

        # 2) OCR for images / scanned PDFs -------------------------------------
        if self.ocr and self.ocr.available and ext in OCR_EXTENSIONS:
            if ext in IMAGE_EXTENSIONS or (ext in PDF_EXTENSIONS and not text.strip()):
                ocr_text = self.ocr.extract(p)
                if ocr_text:
                    record.ocr_text = ocr_text[:5000]
                    self.stats.bump(ocr_done=1)
                    self.db.add_history(HistoryEntry(path, FileAction.OCR, "ocr extracted"))
                    self.bus.emit(EventType.FILE_OCR_DONE, path=path, chars=len(ocr_text))

        # 3) Classification -----------------------------------------------------
        is_shot = ext in IMAGE_EXTENSIONS and "screenshot" in p.name.lower()
        result = self.classifier.classify(
            p, text=f"{text}\n{record.ocr_text}", is_screenshot_hint=is_shot
        )
        record.category = result.category
        record.confidence = result.confidence
        record.tags = sorted(set(record.tags) | set(result.tags))
        self.stats.bump(files_classified=1)
        self.bus.emit(
            EventType.FILE_CLASSIFIED,
            path=path, category=result.category.value, confidence=result.confidence,
        )

        # 4) Persist + index ----------------------------------------------------
        file_id = self.db.upsert_file(record)
        self.db.add_history(HistoryEntry(record.path, FileAction.INDEXED, result.reason))

        # 5) Embedding for semantic search -------------------------------------
        if self.embeddings and self.config.ai.semantic_search:
            vec = self.embeddings.encode(record.searchable_text)
            if any(vec):
                self.db.store_embedding(file_id, vec, self.embeddings.backend_name)
        self.bus.emit(EventType.FILE_INDEXED, path=record.path)

        # 6) Smart rename suggestion (+ optional apply) ------------------------
        if self.config.ai.auto_rename and result.confidence >= self.config.ai.confidence_threshold:
            suggestion = self.renamer.suggest(p, result.category, text=f"{text}\n{record.ocr_text}", tags=record.tags)
            if suggestion.changed and suggestion.confidence >= 0.7:
                from .core.models import RuleAction

                res = self.organizer.apply_actions(
                    record, [(_synthetic_rule(), RuleAction(ActionType.RENAME, suggestion.new_name))]
                )
                if res.final_path:
                    record = res.record
                    self.stats.bump(files_renamed=1)

        # 7) Apply user rules ---------------------------------------------------
        # Non-invasive actions (tag/category) always run; filesystem-mutating
        # actions are gated behind the explicit auto_move / auto_rename toggles
        # so SmartFolders never moves or deletes a file without consent.
        actions = self.rule_engine.evaluate(record)
        allowed = self._filter_allowed_actions(actions)
        if allowed:
            res = self.organizer.apply_actions(record, allowed)
            if any("moved" in a for a in res.performed):
                self.stats.bump(files_moved=1)
            if any("renamed" in a for a in res.performed):
                self.stats.bump(files_renamed=1)
            for rule, _action in allowed:
                self.bus.emit(EventType.RULE_APPLIED, rule=rule.name, path=record.path)
            record = res.record

        self.stats.bump(files_processed=1)
        self.bus.emit(EventType.STATS_UPDATED, **self.stats.as_dict())
        return record

    # ------------------------------------------------------------------ search
    def query(self, text: str, limit: int = 50):
        return self.search.search(text, limit)

    def find_duplicates(self):
        records = self.db.all_files()
        groups = self.duplicates.find_all(records)
        total = sum(g.count for g in groups)
        if total:
            self.stats.duplicates_found = total
            self.bus.emit(EventType.DUPLICATE_FOUND, groups=len(groups), files=total)
        return groups

    # --------------------------------------------------------------- internals
    def reload_rules(self) -> None:
        self.rule_engine.set_rules(self.db.get_rules(enabled_only=True))

    def apply_config(self, config: AppConfig) -> None:
        """Apply a changed configuration without a full restart where possible."""
        self.config = config
        self.organizer.organized_root = Path(config.organized_root)
        self.watcher.set_folders(config.watched_folders)
        self.reload_rules()

    def _seed_rules_if_empty(self) -> None:
        if not self.db.get_rules():
            for rule in default_rules():
                self.db.save_rule(rule)
            log.info("Seeded default rule set")

    def _filter_allowed_actions(self, actions):
        """Drop invasive actions unless the matching auto-toggle is enabled."""
        non_invasive = {ActionType.TAG, ActionType.SET_CATEGORY, ActionType.IGNORE}
        move_like = {ActionType.MOVE, ActionType.COPY, ActionType.ARCHIVE, ActionType.DELETE}
        allowed = []
        for rule, action in actions:
            if action.type in non_invasive:
                allowed.append((rule, action))
            elif action.type is ActionType.RENAME and self.config.ai.auto_rename:
                allowed.append((rule, action))
            elif action.type in move_like and self.config.ai.auto_move:
                allowed.append((rule, action))
        return allowed


def _synthetic_rule():
    from .core.models import Rule

    return Rule(name="__smart_rename__", priority=0)
