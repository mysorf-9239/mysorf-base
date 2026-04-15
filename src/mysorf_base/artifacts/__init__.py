"""Artifacts subsystem for managing ML/research workflow artifacts."""

from .backends.null import NullArtifactManager
from .core.exceptions import ArtifactNotFoundError
from .core.factory import build_artifact_manager, parse_artifacts_config
from .core.interfaces import ArtifactManager, ArtifactSaveHook
from .core.schema import ArtifactRecord, ArtifactsConfig, ArtifactType, VersioningStrategy

__all__ = [
    "ArtifactManager",
    "ArtifactSaveHook",
    "ArtifactNotFoundError",
    "ArtifactRecord",
    "ArtifactType",
    "ArtifactsConfig",
    "NullArtifactManager",
    "VersioningStrategy",
    "build_artifact_manager",
    "parse_artifacts_config",
]
