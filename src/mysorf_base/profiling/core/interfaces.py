"""Interfaces for the profiling subsystem."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from typing import Any, Protocol

from .schema import ProfileSummary, TimingRecord


class Profiler(Protocol):
    """Minimal profiler interface for tabular records."""

    def profile_records(self, records: Sequence[Mapping[str, Any]]) -> ProfileSummary: ...

    def time(self, name: str) -> AbstractContextManager[None]: ...

    def timing_records(self) -> list[TimingRecord]: ...

    def reset_timing(self) -> None: ...
