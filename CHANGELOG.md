# Changelog

All notable changes to **mysorf-base** should be documented in this file.

## [0.1.0] - 2026-04-15

### Added

- 9-subsystem infrastructure library: `config`, `logging`, `tracking`, `profiling`,
  `artifacts`, `sweeps`, `runtime`, `events`, `checkpoints`
- Typed `AppConfig` — all subsystem sections are `@dataclass` types with full attribute
  access (`cfg.logging.backend`, `cfg.tracking.wandb.project`, etc.)
- Recursive secret redaction in `redact_secrets()` — scans all dict keys against
  `_SENSITIVE_KEYS` frozenset (`api_key`, `token`, `secret`, `password`, `credential`)
- `checkpoint.loaded` event emitted symmetrically with `checkpoint.saved` on every
  `load_checkpoint()` call
- `bootstrap()` context manager returning a frozen `RuntimeContext` with `cfg`, `run_id`,
  `config_hash`, `event_bus`, `logger`, `tracker`, `profiler`, `artifact_manager`
- Null backend pattern for all subsystems — disabled backends return `NullLogger`,
  `NullTracker`, `NullProfiler` with identical protocol surface
- In-process event bus with typed `publish` / `subscribe` / `unsubscribe` API
- `sweeps` subsystem with grid, random, and Weights & Biases sweep strategies
- `mysorf-base` CLI entrypoint with `config show`, `runtime validate`,
  `bootstrap smoke` subcommands
- Full test suite (pytest + hypothesis) with property-based tests for bootstrap
  completeness, determinism, immutability, teardown resilience, null backends, and
  override round-trips
- GitHub Actions CI (`.github/workflows/ci.yml`) and tag-based release workflow
  (`.github/workflows/release.yml`)
- Pre-commit hooks: ruff lint+format, mypy strict, bandit security scan
- `pyproject.toml` with Hatchling build, optional extras for all optional backends,
  `mysorf-base` CLI script entry point
- `CITATION.cff`, `SECURITY.md`, `CONTRIBUTING.md`

### Dependencies

- `hydra-core>=1.3,<2.0`
- `omegaconf>=2.3,<3.0`
- `PyYAML>=6.0,<7.0`
- `python-dotenv>=1.0,<2.0`
