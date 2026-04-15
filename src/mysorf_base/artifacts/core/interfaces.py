"""Interfaces for the artifacts subsystem."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .schema import ArtifactRecord, ArtifactType

ArtifactSaveHook = Callable[[ArtifactRecord], None]


class ArtifactManager(Protocol):
    """Minimal artifact manager interface for ML/research workflows.

    ``finalize()`` is runtime-owned and should be safe to call during context
    teardown. Implementations should treat it as idempotent when practical.
    Any exception raised may be suppressed by the runtime after warning.
    """

    def save(
        self,
        source: Path | str,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> ArtifactRecord: ...

    def load(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> Path: ...

    def resolve_path(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> Path: ...

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        name: str | None = None,
    ) -> list[ArtifactRecord]: ...

    def delete(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str,
    ) -> None: ...

    def register_on_save_hook(self, hook: ArtifactSaveHook) -> None: ...

    def finalize(self) -> None: ...
