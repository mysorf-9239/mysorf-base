"""RuntimeContext dataclass for the runtime subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from mysorf_base.artifacts.core.interfaces import ArtifactManager
from mysorf_base.config.core.schema import AppConfig
from mysorf_base.events import EventBus
from mysorf_base.logging.core.interfaces import Logger
from mysorf_base.profiling.core.interfaces import Profiler
from mysorf_base.tracking.core.interfaces import Tracker


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable container holding all subsystem instances produced by bootstrap.

    Supports the context manager protocol: ``__exit__`` calls
    :func:`~mysorf_base.runtime.teardown` automatically.
    """

    cfg: AppConfig
    run_id: str
    config_hash: str
    event_bus: EventBus
    logger: Logger
    tracker: Tracker
    profiler: Profiler
    artifact_manager: ArtifactManager

    def __enter__(self) -> RuntimeContext:
        return self

    def __exit__(self, *args: object) -> None:
        from .bootstrap import teardown

        teardown(self)
