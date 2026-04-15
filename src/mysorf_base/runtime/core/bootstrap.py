"""Bootstrap orchestration for the runtime subsystem."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

from .schema import RuntimeContext


def _generate_run_id() -> str:
    """Return a filesystem-safe runtime identifier."""
    timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    return f"run_{timestamp}_{uuid4().hex[:8]}"


def bootstrap(overrides: Sequence[str] | None = None) -> RuntimeContext:
    """Compose configuration and construct all subsystem instances.

    Subsystem construction order:

    1. :func:`~mysorf_base.config.compose_typed_config` — config composition and
       validation.
    2. :func:`~mysorf_base.logging.build_logger` — logging backend.
    3. :func:`~mysorf_base.tracking.build_tracker` — tracking backend.
    4. :func:`~mysorf_base.profiling.build_profiler` — profiling backend.
    5. :func:`~mysorf_base.artifacts.build_artifact_manager` — artifact manager.

    Exceptions raised by any step propagate directly without wrapping.

    Args:
        overrides: Hydra override strings applied during config composition,
            e.g. ``["logging=rich", "runtime.seed=42"]``.  Defaults to an
            empty list when ``None``.

    Returns:
        An immutable :class:`RuntimeContext` containing all subsystem
        instances.
    """
    from mysorf_base.artifacts import build_artifact_manager
    from mysorf_base.config import compose_typed_config
    from mysorf_base.events import EventBus
    from mysorf_base.logging import build_logger
    from mysorf_base.profiling import build_profiler
    from mysorf_base.tracking import build_tracker
    from mysorf_base.utils import sha256_config

    cfg = compose_typed_config(list(overrides) if overrides is not None else [])
    run_id = _generate_run_id()
    config_hash = sha256_config(cfg)
    event_bus = EventBus()
    logger = build_logger(cfg.logging, name=cfg.app.name)
    logger.debug(f"bootstrap: app={cfg.app.name} run_id={run_id} config_hash={config_hash[:8]}")
    tracker = build_tracker(cfg.tracking)
    profiler = build_profiler(cfg.profiling)
    artifact_manager = build_artifact_manager(
        cfg.artifacts,
        cfg.paths,
        tracker=tracker,
        run_id=run_id,
    )

    return RuntimeContext(
        cfg=cfg,
        run_id=run_id,
        config_hash=config_hash,
        event_bus=event_bus,
        logger=logger,
        tracker=tracker,
        profiler=profiler,
        artifact_manager=artifact_manager,
    )


def teardown(context: RuntimeContext) -> None:
    """Release resources held by a :class:`RuntimeContext`.

    Teardown is runtime-owned and follows a deterministic order:

    1. ``context.tracker.finish()``
    2. ``context.artifact_manager.finalize()``
    3. close logger handlers when exposed by the backend

    Any exception raised by an individual step is suppressed after a warning
    is emitted via ``context.logger``, ensuring that teardown does not mask an
    exception propagating from the caller.

    Args:
        context: The runtime context to tear down.
    """

    def _warn(message: str) -> None:
        with suppress(Exception):
            context.logger.warning(message)

    try:
        context.tracker.finish()
    except Exception as exc:  # noqa: BLE001
        _warn(f"tracker.finish() failed during teardown: {exc}")

    try:
        context.artifact_manager.finalize()
    except Exception as exc:  # noqa: BLE001
        _warn(f"artifact_manager.finalize() failed during teardown: {exc}")

    handlers = getattr(context.logger, "handlers", None)
    if handlers is None:
        return

    for handler in list(handlers):
        try:
            handler.close()
        except Exception as exc:  # noqa: BLE001
            _warn(f"logger handler close failed during teardown: {exc}")

    try:
        handlers.clear()
    except Exception as exc:  # noqa: BLE001
        _warn(f"logger handler cleanup failed during teardown: {exc}")
