"""Typed dataclass schema for the mysorf-base application config."""

from __future__ import annotations

from dataclasses import dataclass, field

from omegaconf import MISSING

from mysorf_base.artifacts.core.schema import ArtifactsConfig
from mysorf_base.logging.core.schema import LoggingConfig
from mysorf_base.profiling.core.schema import ProfilingConfig
from mysorf_base.sweeps.core.schema import SweepsConfig
from mysorf_base.tracking.core.schema import TrackingConfig


@dataclass
class AppSection:
    """Application identity metadata."""

    name: str = "mysorf-base"
    subsystem: str = "config"
    version: str = "0.2.0"


@dataclass
class EnvSection:
    """Execution environment descriptor."""

    workspace: str = MISSING
    name: str = "local"
    platform: str = "local"


@dataclass
class PathsSection:
    """Shared filesystem path conventions."""

    repo_root: str = MISSING
    config_root: str = MISSING
    output_dir: str = MISSING
    artifacts_dir: str = MISSING
    cache_dir: str = MISSING


@dataclass
class RuntimeSection:
    """Execution-mode flags and global settings."""

    debug: bool = False
    seed: int = 7
    strict_config: bool = True
    profile: str = "default"


@dataclass
class AppConfig:
    """Top-level typed configuration schema for the mysorf-base library.

    All subsystem sections are typed dataclasses owned by their respective
    subsystems.  Subsystem factory functions accept typed instances directly
    (``isinstance(data, LoggingConfig)`` short-circuits the OmegaConf merge).
    """

    app: AppSection = field(default_factory=AppSection)
    env: EnvSection = field(default_factory=EnvSection)
    paths: PathsSection = field(default_factory=PathsSection)
    runtime: RuntimeSection = field(default_factory=RuntimeSection)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    profiling: ProfilingConfig = field(default_factory=ProfilingConfig)
    artifacts: ArtifactsConfig = field(default_factory=ArtifactsConfig)
    sweeps: SweepsConfig = field(default_factory=SweepsConfig)
