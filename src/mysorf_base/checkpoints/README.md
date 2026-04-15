# Checkpoints

`mysorf_base.checkpoints` provides a small `CheckpointManager` on top of the
artifact subsystem.

It is intended for generic ML-style checkpoint persistence, not for any one
engine or domain package.

## Responsibilities

- persist opaque checkpoint bytes plus compatibility metadata
- persist them through `ArtifactManager`
- restore checkpoint payloads
- validate compatibility metadata such as config hash or schema version

## Public API

```python
from mysorf_base.checkpoints import (
    CheckpointCompatibilityError,
    CheckpointManager,
    CheckpointPayload,
    build_checkpoint_manager,
)
```

## Example

```python
from mysorf_base.checkpoints import build_checkpoint_manager
from mysorf_base.runtime import bootstrap

with bootstrap() as ctx:
    manager = build_checkpoint_manager(ctx.artifact_manager, ctx.event_bus)
    state_bytes = b"...serialized by caller..."
    manager.save_checkpoint(
        state_bytes,
        epoch=5,
        metadata={"config_hash": ctx.config_hash, "schema_version": "v1"},
    )
```

`build_checkpoint_manager(...)` is the preferred convenience entry point when a
caller is already operating inside a `RuntimeContext`.

The caller is responsible for serializing and deserializing the model state.
That keeps `mysorf-base` neutral with respect to PyTorch, NumPy, JAX, or other
framework-specific checkpoint formats.

For large model states already materialized on disk, callers can avoid an
additional in-memory bytes copy by using `save_checkpoint_file(path, ...)`.

`save_checkpoint(...)` defaults the artifact version to:

- explicit `version` when provided
- `epoch_{epoch:04d}` when `epoch` is present
- `"latest"` otherwise

## Events

`CheckpointManager` emits structured events on the `EventBus` for both save and load:

| Event | Payload keys | Emitted by |
|-------|-------------|------------|
| `checkpoint.saved` | `name`, `version`, `epoch`, `path` | `save_checkpoint()` / `save_checkpoint_file()` |
| `checkpoint.loaded` | `name`, `version`, `epoch`, `path` | `load_checkpoint()` |

Subscribe via `ctx.event_bus`:

```python
with bootstrap() as ctx:
    manager = build_checkpoint_manager(ctx.artifact_manager, ctx.event_bus)

    ctx.event_bus.subscribe(
        "checkpoint.saved",
        lambda e: ctx.logger.info(f"saved {e.payload['name']} → {e.payload['path']}"),
    )
    ctx.event_bus.subscribe(
        "checkpoint.loaded",
        lambda e: ctx.logger.info(f"loaded {e.payload['name']} v{e.payload['version']}"),
    )
```
