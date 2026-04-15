"""Validation for the artifacts subsystem config."""

from __future__ import annotations

from .schema import ArtifactsConfig

_SUPPORTED_BACKENDS = {"local", "disabled", "s3", "gcs"}
_SUPPORTED_STRATEGIES = {"run_id", "epoch", "timestamp", "manual"}


def validate_artifacts_config(cfg: ArtifactsConfig) -> None:
    """Validate ArtifactsConfig, raising ValueError on invalid values."""
    if cfg.backend not in _SUPPORTED_BACKENDS:
        raise ValueError(
            f"Unsupported artifacts backend: {cfg.backend!r}. "
            f"Valid options: {sorted(_SUPPORTED_BACKENDS)}"
        )
    if cfg.backend == "disabled" and cfg.enabled:
        raise ValueError("artifacts.enabled must be false when backend is disabled.")
    if cfg.backend in {"s3", "gcs"} and not cfg.bucket:
        raise ValueError(f"artifacts.bucket is required when backend is {cfg.backend!r}.")
    if cfg.versioning_strategy not in _SUPPORTED_STRATEGIES:
        raise ValueError(
            f"Unsupported versioning_strategy: {cfg.versioning_strategy!r}. "
            f"Valid options: {sorted(_SUPPORTED_STRATEGIES)}"
        )
