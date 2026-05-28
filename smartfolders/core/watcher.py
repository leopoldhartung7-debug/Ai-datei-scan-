"""Real-time folder watching.

Wraps :mod:`watchdog` to monitor folders for new / changed / moved files and
forwards debounced "file ready" callbacks. When ``watchdog`` is not installed it
transparently falls back to a lightweight polling watcher so the feature still
works (just with higher latency).

Debouncing matters because browsers and copy operations fire many rapid events
while a file is still being written; we wait until a file's size has been stable
for ``settle_seconds`` before declaring it ready.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from ..constants import IGNORED_SUFFIXES
from ..utils.logging import get_logger

log = get_logger(__name__)

ReadyCallback = Callable[[Path], None]

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _HAVE_WATCHDOG = True
except Exception:  # pragma: no cover
    _HAVE_WATCHDOG = False
    FileSystemEventHandler = object  # type: ignore[assignment,misc]


class _DebounceTracker:
    """Tracks recently-seen paths and fires a callback once they settle."""

    def __init__(self, on_ready: ReadyCallback, settle_seconds: float = 2.0) -> None:
        self._on_ready = on_ready
        self._settle = settle_seconds
        self._pending: dict[str, float] = {}
        self._sizes: dict[str, int] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def touch(self, path: Path) -> None:
        with self._lock:
            self._pending[str(path)] = time.monotonic()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="sf-debounce", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self) -> None:
        while not self._stop.wait(0.5):
            now = time.monotonic()
            ready: list[str] = []
            with self._lock:
                for path, ts in list(self._pending.items()):
                    if now - ts < self._settle:
                        continue
                    size = _safe_size(path)
                    if size is None:               # vanished
                        self._pending.pop(path, None)
                        self._sizes.pop(path, None)
                        continue
                    if self._sizes.get(path) == size:
                        ready.append(path)
                        self._pending.pop(path, None)
                        self._sizes.pop(path, None)
                    else:                          # still growing - reset timer
                        self._sizes[path] = size
                        self._pending[path] = now
            for path in ready:
                try:
                    self._on_ready(Path(path))
                except Exception:  # pragma: no cover
                    log.exception("ready callback failed for %s", path)


def _safe_size(path: str) -> int | None:
    try:
        return os.stat(path).st_size
    except OSError:
        return None


def _is_relevant(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(IGNORED_SUFFIXES) or name.startswith("~$"):
        return False
    return True


if _HAVE_WATCHDOG:

    class _Handler(FileSystemEventHandler):
        def __init__(self, tracker: _DebounceTracker) -> None:
            self._tracker = tracker

        def on_created(self, event: FileSystemEvent) -> None:
            self._maybe(event)

        def on_modified(self, event: FileSystemEvent) -> None:
            self._maybe(event)

        def on_moved(self, event: FileSystemEvent) -> None:
            dest = getattr(event, "dest_path", None)
            if dest and not getattr(event, "is_directory", False):
                p = Path(dest)
                if _is_relevant(p):
                    self._tracker.touch(p)

        def _maybe(self, event: FileSystemEvent) -> None:
            if getattr(event, "is_directory", False):
                return
            p = Path(event.src_path)
            if _is_relevant(p):
                self._tracker.touch(p)


class FolderWatcher:
    """Watches multiple folders and reports settled files via a callback."""

    def __init__(self, on_ready: ReadyCallback, settle_seconds: float = 2.0) -> None:
        self._tracker = _DebounceTracker(on_ready, settle_seconds)
        self._folders: list[Path] = []
        self._running = False
        self._observer = None
        self._poller: _PollingWatcher | None = None
        self.backend = "watchdog" if _HAVE_WATCHDOG else "polling"

    def set_folders(self, folders: list[str | Path]) -> None:
        self._folders = [Path(f) for f in folders]
        if self._running:
            self.stop()
            self.start()

    def start(self) -> None:
        if self._running:
            return
        self._tracker.start()
        existing = [f for f in self._folders if f.exists()]
        if _HAVE_WATCHDOG:
            self._observer = Observer()
            handler = _Handler(self._tracker)
            for folder in existing:
                self._observer.schedule(handler, str(folder), recursive=True)
            self._observer.start()
        else:
            self._poller = _PollingWatcher(existing, self._tracker)
            self._poller.start()
        self._running = True
        log.info("Watching %d folder(s) via %s backend", len(existing), self.backend)

    def stop(self) -> None:
        if not self._running:
            return
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._observer = None
        if self._poller is not None:
            self._poller.stop()
            self._poller = None
        self._tracker.stop()
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running


class _PollingWatcher:
    """Fallback watcher: periodically diff folder contents for new files."""

    def __init__(self, folders: list[Path], tracker: _DebounceTracker, interval: float = 5.0):
        self._folders = folders
        self._tracker = tracker
        self._interval = interval
        self._known: set[str] = set()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._prime()
        self._thread = threading.Thread(target=self._loop, name="sf-poller", daemon=True)
        self._thread.start()

    def _prime(self) -> None:
        for folder in self._folders:
            for p in _iter_files(folder):
                self._known.add(str(p))

    def _loop(self) -> None:
        while not self._stop.wait(self._interval):
            for folder in self._folders:
                for p in _iter_files(folder):
                    key = str(p)
                    if key not in self._known:
                        self._known.add(key)
                        if _is_relevant(p):
                            self._tracker.touch(p)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)


def _iter_files(folder: Path):
    try:
        for entry in os.scandir(folder):
            try:
                if entry.is_file():
                    yield Path(entry.path)
                elif entry.is_dir() and not entry.name.startswith("."):
                    yield from _iter_files(Path(entry.path))
            except OSError:
                continue
    except OSError:
        return
