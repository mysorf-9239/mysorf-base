"""Checkpoint manager built on top of the artifact subsystem."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from mysorf_base.artifacts import ArtifactManager, ArtifactRecord, ArtifactType
from mysorf_base.events import EventBus


class CheckpointCompatibilityError(ValueError):
    """Raised when checkpoint metadata does not satisfy compatibility rules."""


@dataclass(frozen=True)
class CheckpointPayload:
    """Portable checkpoint payload persisted through the artifact manager."""

    state_bytes: bytes
    epoch: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """Persist and restore generic ML checkpoints through ArtifactManager."""

    def __init__(
        self,
        artifact_manager: ArtifactManager,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._artifact_manager = artifact_manager
        self._event_bus = event_bus

    def save_checkpoint(
        self,
        state_bytes: bytes,
        *,
        epoch: int | None = None,
        metadata: Mapping[str, Any] | None = None,
        name: str = "checkpoint",
        version: str | None = None,
    ) -> ArtifactRecord:
        """Persist opaque checkpoint bytes plus JSON metadata."""
        tmp_path = self._write_checkpoint_archive(
            state_source=state_bytes,
            epoch=epoch,
            metadata=metadata,
        )
        try:
            return self._save_archive(
                tmp_path,
                name=name,
                version=version,
                epoch=epoch,
                metadata=metadata,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def save_checkpoint_file(
        self,
        state_path: str | Path,
        *,
        epoch: int | None = None,
        metadata: Mapping[str, Any] | None = None,
        name: str = "checkpoint",
        version: str | None = None,
    ) -> ArtifactRecord:
        """Persist a checkpoint by wrapping an existing file path into the archive."""
        source_path = Path(state_path).expanduser().resolve()
        tmp_path = self._write_checkpoint_archive(
            state_source=source_path,
            epoch=epoch,
            metadata=metadata,
        )
        try:
            return self._save_archive(
                tmp_path,
                name=name,
                version=version,
                epoch=epoch,
                metadata=metadata,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def _write_checkpoint_archive(
        self,
        *,
        state_source: bytes | Path,
        epoch: int | None,
        metadata: Mapping[str, Any] | None,
    ) -> Path:
        """Write a temporary checkpoint archive and return its filesystem path."""
        payload_metadata = {
            "epoch": epoch,
            "metadata": dict(metadata or {}),
        }
        with NamedTemporaryFile(suffix=".ckpt", delete=False) as handle:
            tmp_path = Path(handle.name)
            with ZipFile(tmp_path, mode="w", compression=ZIP_DEFLATED) as archive:
                archive.writestr(
                    "metadata.json",
                    json.dumps(payload_metadata, sort_keys=True, separators=(",", ":")),
                )
                if isinstance(state_source, Path):
                    archive.write(state_source, arcname="state.bin")
                else:
                    archive.writestr("state.bin", state_source)
        return tmp_path

    def _save_archive(
        self,
        archive_path: Path,
        *,
        name: str,
        version: str | None,
        epoch: int | None,
        metadata: Mapping[str, Any] | None,
    ) -> ArtifactRecord:
        """Persist a temporary checkpoint archive and emit checkpoint events."""
        resolved_version = (
            version
            if version is not None
            else (f"epoch_{epoch:04d}" if epoch is not None else "latest")
        )
        payload_metadata = dict(metadata or {})
        record = self._artifact_manager.save(
            archive_path,
            name=name,
            artifact_type=ArtifactType.CHECKPOINT,
            version=resolved_version,
        )

        if self._event_bus is not None:
            self._event_bus.publish(
                "checkpoint.saved",
                {
                    "name": name,
                    "epoch": epoch,
                    "version": record.version,
                    "path": str(record.path),
                    "metadata": payload_metadata,
                },
            )
        return record

    def load_checkpoint(
        self,
        *,
        name: str = "checkpoint",
        version: str | None = None,
    ) -> CheckpointPayload:
        """Load a checkpoint archive containing JSON metadata and opaque state bytes."""
        stored_path = self._artifact_manager.load(
            name=name,
            artifact_type=ArtifactType.CHECKPOINT,
            version=version,
        )
        target = stored_path
        if target.is_dir():
            children = [child for child in target.iterdir() if child.is_file()]
            if len(children) != 1:
                raise ValueError(
                    "Checkpoint artifact directory must contain exactly one serialized payload file."
                )
            target = children[0]

        with ZipFile(target, mode="r") as archive:
            names = set(archive.namelist())
            if {"metadata.json", "state.bin"} - names:
                raise ValueError(
                    "Checkpoint archive must contain both 'metadata.json' and 'state.bin'."
                )
            metadata_raw = archive.read("metadata.json")
            state_bytes = archive.read("state.bin")

        metadata_obj = json.loads(metadata_raw.decode("utf-8"))
        epoch_obj = metadata_obj.get("epoch")
        if epoch_obj is not None and not isinstance(epoch_obj, int):
            raise ValueError("Checkpoint metadata field 'epoch' must be an int when set.")
        raw_metadata = metadata_obj.get("metadata", {})
        if not isinstance(raw_metadata, dict):
            raise ValueError("Checkpoint metadata field 'metadata' must be a JSON object.")

        payload = CheckpointPayload(
            state_bytes=state_bytes,
            epoch=epoch_obj,
            metadata=dict(raw_metadata),
        )

        if self._event_bus is not None:
            self._event_bus.publish(
                "checkpoint.loaded",
                {
                    "name": name,
                    "version": version or "latest",
                    "epoch": epoch_obj,
                    "path": str(stored_path),
                },
            )

        return payload

    @staticmethod
    def validate_compatibility(
        payload: CheckpointPayload,
        *,
        required_metadata: Mapping[str, Any],
    ) -> None:
        """Validate that required metadata keys and values match the payload."""
        for key, expected in required_metadata.items():
            actual = payload.metadata.get(key)
            if actual != expected:
                raise CheckpointCompatibilityError(
                    f"Checkpoint metadata mismatch for {key!r}: expected {expected!r}, got {actual!r}."
                )


def build_checkpoint_manager(
    artifact_manager: ArtifactManager,
    event_bus: EventBus | None = None,
) -> CheckpointManager:
    """Construct a checkpoint manager from runtime-owned dependencies."""

    return CheckpointManager(artifact_manager, event_bus=event_bus)
