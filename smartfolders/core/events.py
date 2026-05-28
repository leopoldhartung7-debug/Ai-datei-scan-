"""A tiny, thread-safe publish/subscribe event bus.

The background engine runs on worker threads while the UI lives on the Qt main
thread. Rather than coupling them, every component talks through this bus.
Subscribers receive :class:`Event` objects; the UI adapter (see
``smartfolders.ui.bridge``) marshals them onto the Qt event loop.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ..utils.logging import get_logger

log = get_logger(__name__)


class EventType(Enum):
    # Lifecycle
    ENGINE_STARTED = auto()
    ENGINE_STOPPED = auto()
    ENGINE_PAUSED = auto()
    ENGINE_RESUMED = auto()
    # File processing pipeline
    FILE_DETECTED = auto()
    FILE_CLASSIFIED = auto()
    FILE_RENAMED = auto()
    FILE_MOVED = auto()
    FILE_OCR_DONE = auto()
    FILE_INDEXED = auto()
    DUPLICATE_FOUND = auto()
    FILE_ERROR = auto()
    # Scanning progress
    SCAN_STARTED = auto()
    SCAN_PROGRESS = auto()
    SCAN_FINISHED = auto()
    # Stats / misc
    STATS_UPDATED = auto()
    RULE_APPLIED = auto()
    NOTIFY = auto()              # generic user notification (title/message)


@dataclass
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)


Listener = Callable[[Event], None]


class EventBus:
    """Synchronous, thread-safe pub/sub with optional wildcard subscription."""

    _WILDCARD = None

    def __init__(self) -> None:
        self._listeners: dict[EventType | None, list[Listener]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_type: EventType | None, listener: Listener) -> Callable[[], None]:
        """Register *listener*. Pass ``None`` to receive every event.

        Returns an unsubscribe callable.
        """
        with self._lock:
            self._listeners[event_type].append(listener)

        def _unsub() -> None:
            self.unsubscribe(event_type, listener)

        return _unsub

    def subscribe_all(self, listener: Listener) -> Callable[[], None]:
        return self.subscribe(self._WILDCARD, listener)

    def unsubscribe(self, event_type: EventType | None, listener: Listener) -> None:
        with self._lock:
            try:
                self._listeners[event_type].remove(listener)
            except ValueError:
                pass

    def emit(self, event_type: EventType, **payload: Any) -> None:
        """Publish an event to all matching subscribers."""
        event = Event(event_type, payload)
        with self._lock:
            targeted = list(self._listeners.get(event_type, ()))
            wildcard = list(self._listeners.get(self._WILDCARD, ()))
        for listener in (*targeted, *wildcard):
            try:
                listener(event)
            except Exception:  # pragma: no cover - a bad listener must not kill the bus
                log.exception("Event listener failed for %s", event_type)

    def clear(self) -> None:
        with self._lock:
            self._listeners.clear()
