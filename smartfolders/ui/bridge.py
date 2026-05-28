"""Marshals :class:`EventBus` events from worker threads onto the Qt thread.

Background workers emit events on arbitrary threads. Touching Qt widgets from a
non-GUI thread is undefined behaviour, so this bridge subscribes to the bus and
re-emits each event as a Qt signal. Qt's queued-connection machinery then
delivers it on the main thread. Widgets simply ``connect`` to :data:`event`.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from ..core.events import Event, EventBus, EventType


class QtEventBridge(QObject):
    """Re-emits bus events as a thread-safe Qt signal."""

    event = pyqtSignal(object)  # emits core.events.Event

    def __init__(self, bus: EventBus, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._bus = bus
        self._unsub = bus.subscribe_all(self._on_bus_event)

    def _on_bus_event(self, ev: Event) -> None:
        # Emitting a queued signal is safe from any thread.
        self.event.emit(ev)

    def close(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


__all__ = ["QtEventBridge", "Event", "EventType"]
