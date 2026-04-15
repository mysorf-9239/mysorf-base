"""Minimal synchronous publish/subscribe event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from warnings import warn


@dataclass(frozen=True)
class Event:
    """Immutable event payload emitted through the runtime event bus."""

    name: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


EventHandler = Callable[[Event], None]
EventHandlerErrorCallback = Callable[[Event, EventHandler, Exception], None]


def _default_on_handler_error(event: Event, handler: EventHandler, exc: Exception) -> None:
    warn(
        (
            "Event handler failed and was suppressed: "
            f"event={event.name!r} handler={handler!r} error={exc!r}"
        ),
        RuntimeWarning,
        stacklevel=3,
    )


class EventBus:
    """Synchronous in-process event bus with optional wildcard subscribers."""

    def __init__(
        self,
        *,
        on_handler_error: EventHandlerErrorCallback | None = None,
    ) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = RLock()
        self._on_handler_error = on_handler_error or _default_on_handler_error

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register *handler* for *event_name* or ``"*"`` wildcard events."""
        with self._lock:
            self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload: Mapping[str, Any] | None = None) -> Event:
        """Emit an event and synchronously invoke matching handlers."""
        event = Event(name=event_name, payload=dict(payload or {}))
        with self._lock:
            handlers = [
                *self._subscribers.get(event_name, []),
                *self._subscribers.get("*", []),
            ]
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                self._on_handler_error(event, handler, exc)
        return event
