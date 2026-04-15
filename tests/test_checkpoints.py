"""Tests for the checkpoint manager built on top of artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from mysorf_base.artifacts.backends.local import LocalBackend
from mysorf_base.checkpoints import (
    CheckpointCompatibilityError,
    CheckpointManager,
    build_checkpoint_manager,
)
from mysorf_base.events import EventBus


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    artifact_manager = LocalBackend(str(tmp_path / "artifacts"), versioning_strategy="manual")
    manager = CheckpointManager(artifact_manager)

    manager.save_checkpoint(
        b"opaque-state",
        epoch=3,
        metadata={"config_hash": "abc123"},
        name="trainer",
        version="v1",
    )
    payload = manager.load_checkpoint(name="trainer", version="v1")

    assert payload.epoch == 3
    assert payload.state_bytes == b"opaque-state"
    assert payload.metadata["config_hash"] == "abc123"


def test_checkpoint_validate_compatibility_raises_on_mismatch() -> None:
    from mysorf_base.checkpoints import CheckpointPayload

    payload = CheckpointPayload(state_bytes=b"x", metadata={"config_hash": "abc123"})

    with pytest.raises(CheckpointCompatibilityError, match="config_hash"):
        CheckpointManager.validate_compatibility(
            payload,
            required_metadata={"config_hash": "xyz999"},
        )


def test_checkpoint_manager_emits_saved_event(tmp_path: Path) -> None:
    artifact_manager = LocalBackend(str(tmp_path / "artifacts"), versioning_strategy="manual")
    event_bus = EventBus()
    events: list[str] = []
    event_bus.subscribe("checkpoint.saved", lambda event: events.append(event.name))
    manager = CheckpointManager(artifact_manager, event_bus=event_bus)

    manager.save_checkpoint(b"weights", epoch=1, metadata={"config_hash": "abc"})

    assert events == ["checkpoint.saved"]


def test_checkpoint_file_roundtrip(tmp_path: Path) -> None:
    artifact_manager = LocalBackend(str(tmp_path / "artifacts"), versioning_strategy="manual")
    manager = CheckpointManager(artifact_manager)
    state_path = tmp_path / "state.bin"
    state_path.write_bytes(b"opaque-state-from-file")

    manager.save_checkpoint_file(
        state_path,
        epoch=4,
        metadata={"config_hash": "def456"},
        name="trainer-file",
        version="v2",
    )
    payload = manager.load_checkpoint(name="trainer-file", version="v2")

    assert payload.epoch == 4
    assert payload.state_bytes == b"opaque-state-from-file"
    assert payload.metadata["config_hash"] == "def456"


def test_build_checkpoint_manager_uses_runtime_dependencies(tmp_path: Path) -> None:
    artifact_manager = LocalBackend(str(tmp_path / "artifacts"), versioning_strategy="manual")
    event_bus = EventBus()
    manager = build_checkpoint_manager(artifact_manager, event_bus)

    assert isinstance(manager, CheckpointManager)
