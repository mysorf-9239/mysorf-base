"""Tests for the lightweight runtime event bus."""

from __future__ import annotations

import threading
from warnings import catch_warnings, simplefilter

from mysorf_base.events import Event, EventBus


def test_event_bus_publish_subscribe() -> None:
    bus = EventBus()
    events: list[str] = []
    bus.subscribe("run.started", lambda event: events.append(event.name))

    emitted = bus.publish("run.started", {"run_id": "abc"})

    assert emitted.name == "run.started"
    assert events == ["run.started"]


def test_event_bus_supports_wildcard_subscribers() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("*", lambda event: seen.append(event.name))

    bus.publish("run.started")
    bus.publish("checkpoint.saved")

    assert seen == ["run.started", "checkpoint.saved"]


def test_event_bus_calls_multiple_subscribers() -> None:
    bus = EventBus()
    received: list[str] = []

    bus.subscribe("run.started", lambda event: received.append(f"a:{event.name}"))
    bus.subscribe("run.started", lambda event: received.append(f"b:{event.name}"))

    bus.publish("run.started")

    assert received == ["a:run.started", "b:run.started"]


def test_event_bus_suppresses_handler_exceptions() -> None:
    bus = EventBus()
    received: list[str] = []

    def broken_handler(_: object) -> None:
        raise RuntimeError("boom")

    bus.subscribe("run.started", broken_handler)
    bus.subscribe("run.started", lambda event: received.append(event.name))

    with catch_warnings(record=True) as caught:
        simplefilter("always")
        emitted = bus.publish("run.started")

    assert emitted.name == "run.started"
    assert received == ["run.started"]
    assert len(caught) == 1
    assert "Event handler failed and was suppressed" in str(caught[0].message)


def test_event_bus_supports_custom_handler_error_callback() -> None:
    errors: list[str] = []

    def on_handler_error(event: Event, _handler: object, exc: Exception) -> None:
        errors.append(f"{event.name}:{exc}")

    bus = EventBus(on_handler_error=on_handler_error)

    def broken_handler(_: object) -> None:
        raise RuntimeError("boom")

    bus.subscribe("run.started", broken_handler)
    bus.publish("run.started")

    assert errors == ["run.started:boom"]


def test_event_bus_does_not_replay_old_events_to_new_subscribers() -> None:
    bus = EventBus()
    received: list[str] = []

    bus.publish("run.started")
    bus.subscribe("run.started", lambda event: received.append(event.name))

    assert received == []


def test_event_bus_thread_safe_publish_and_subscribe() -> None:
    bus = EventBus()
    ready = threading.Event()
    received: list[int] = []

    def subscriber() -> None:
        bus.subscribe("metric.logged", lambda event: received.append(int(event.payload["step"])))
        ready.set()

    def publisher() -> None:
        ready.wait()
        for step in range(10):
            bus.publish("metric.logged", {"step": step})

    subscribe_thread = threading.Thread(target=subscriber)
    publish_thread = threading.Thread(target=publisher)
    subscribe_thread.start()
    publish_thread.start()
    subscribe_thread.join()
    publish_thread.join()

    assert received == list(range(10))
