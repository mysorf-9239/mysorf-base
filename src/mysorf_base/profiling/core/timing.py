"""Shared timing helpers for profiler implementations."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from .schema import TimingRecord


class TimingMixin:
    """Provide ``time(...)`` context management and in-memory timing records."""

    def __init__(self) -> None:
        self._timing_records: list[TimingRecord] = []

    @contextmanager
    def time(self, name: str) -> Iterator[None]:
        start = perf_counter()
        try:
            yield
        finally:
            self._timing_records.append(
                TimingRecord(name=name, duration_seconds=perf_counter() - start)
            )

    def timing_records(self) -> list[TimingRecord]:
        return list(self._timing_records)

    def reset_timing(self) -> None:
        self._timing_records.clear()
