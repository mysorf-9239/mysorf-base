"""Schema and data models for the artifacts subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class ArtifactType(StrEnum):
    """Classification of artifact kinds."""

    CHECKPOINT = "checkpoint"
    DATASET = "dataset"
    OUTPUT = "output"
    GENERIC = "generic"


class VersioningStrategy(StrEnum):
    """Strategy for auto-generating artifact versions."""

    RUN_ID = "run_id"
    EPOCH = "epoch"
    TIMESTAMP = "timestamp"
    MANUAL = "manual"


@dataclass
class ArtifactsConfig:
    """Configuration schema owned by the artifacts subsystem."""

    backend: str = "local"
    enabled: bool = True
    base_dir: str | None = None
    versioning_strategy: str = "run_id"
    bucket: str | None = None
    prefix: str = "artifacts"
    cache_dir: str | None = None
    region: str | None = None
    gcs_project: str | None = None


@dataclass
class ArtifactRecord:
    """Metadata describing a saved artifact."""

    name: str
    version: str
    path: Path
    artifact_type: ArtifactType
    size_bytes: int
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
