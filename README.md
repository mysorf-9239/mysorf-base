# mysorf-base

**mysorf-base** is a reusable Python infrastructure library for ML and research projects.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

It composes infrastructure once via `bootstrap()`, wraps it in a single frozen `RuntimeContext`,
and injects that context into application code — so domain code never calls vendor SDKs directly.

## Subsystems

| Subsystem | Status | Description |
|-----------|--------|-------------|
| [`config`](src/mysorf_base/config/) | Stable | Hydra/OmegaConf composition, fully **typed** `AppConfig` dataclass |
| [`logging`](src/mysorf_base/logging/) | Stable | Logger factory with 4 backends (console, file, structlog, rich) |
| [`tracking`](src/mysorf_base/tracking/) | Stable | Experiment tracker with Weights & Biases backend |
| [`profiling`](src/mysorf_base/profiling/) | Stable | Lightweight tabular data profiling (basic, pandas) |
| [`artifacts`](src/mysorf_base/artifacts/) | Stable | Artifact save/load/versioning with local, S3, GCS backends |
| [`sweeps`](src/mysorf_base/sweeps/) | Stable | Hyperparameter search — grid, random, W&B sweep strategies |
| [`runtime`](src/mysorf_base/runtime/) | Stable | Bootstrap orchestration, frozen `RuntimeContext` with `config_hash` |
| [`events`](src/mysorf_base/events/) | Stable | Lightweight in-process publish/subscribe event bus |
| [`checkpoints`](src/mysorf_base/checkpoints/) | Stable | Checkpoint save/load — emits `checkpoint.saved` and `checkpoint.loaded` |

## Key Design Points

**Typed config** — every subsystem section in `AppConfig` is a `@dataclass`, not a dict.
Attribute access everywhere: `cfg.tracking.wandb.project`, `cfg.logging.backend`.

**Recursive secret redaction** — `redact_secrets()` walks the full config tree and masks
any key matching `api_key`, `token`, `secret`, `password`, or `credential` at any depth.

**Reproducibility via `config_hash`** — `RuntimeContext.config_hash` is a `sha256` digest
of the composed config, written alongside every artifact for exact run reproduction.

**Event bus in every run** — `ctx.event_bus` is always available. Core subsystems
(checkpoints) emit structured events; downstream code can subscribe without coupling.

**Null backend pattern** — disabling any subsystem (`logging=disabled`) returns a protocol-
compatible Null object. Downstream code never branches on `if ctx.logger is None`.

## Installation

### From GitHub

```bash
pip install git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0
```

### With optional extras

```bash
pip install "mysorf-base[logging-rich,tracking-wandb] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0"
pip install "mysorf-base[all] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0"
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "mysorf-base @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0",
]
```

### Local editable install

```bash
git clone https://github.com/mysorf-9239/mysorf-base.git
cd mysorf-base
pip install -e ".[dev]"
pre-commit install
```

## Quick Start

```python
from mysorf_base.runtime import bootstrap

with bootstrap(["logging=rich", "tracking=wandb"]) as ctx:
    ctx.logger.info(f"run_id={ctx.run_id}  config_hash={ctx.config_hash}")
    ctx.tracker.start_run(run_name="baseline")
    ctx.tracker.log_metrics({"loss": 0.42}, step=1)
    # checkpoint events are emitted automatically:
    ctx.event_bus.subscribe("checkpoint.saved", lambda e: ctx.logger.info(e.name))
```

### Typed config access

```python
with bootstrap() as ctx:
    # All fields are typed dataclass attributes — no dict subscripting
    assert ctx.cfg.logging.backend == "console"
    assert ctx.cfg.tracking.wandb.project == "mysorf-base"
    assert ctx.cfg.runtime.seed >= 0
```

### Hyperparameter sweep

```python
from mysorf_base.runtime import bootstrap
from mysorf_base.sweeps import SearchSpace, CategoricalParam, SweepsConfig, run_sweep

with bootstrap() as ctx:
    space = SearchSpace(params=[
        CategoricalParam(name="lr", values=[0.001, 0.01, 0.1]),
    ])

    def trial_fn(ctx, params):
        return {"loss": train_model(lr=float(params["lr"]))}

    summary = run_sweep(space, trial_fn, ctx, SweepsConfig(strategy="grid"))
    best = summary.best_trial("loss", mode="min")
```

### Artifact management

```python
from pathlib import Path
from mysorf_base.artifacts import ArtifactType

with bootstrap() as ctx:
    record = ctx.artifact_manager.save(
        Path("model.pt"), "model", artifact_type=ArtifactType.CHECKPOINT
    )
    assert record.version == ctx.run_id  # run_id used as artifact version
```

## CLI

```bash
# Compose and print the effective config (with secret redaction)
mysorf-base config show
mysorf-base config show logging=rich tracking=wandb runtime.seed=42

# Validate runtime semantics without running anything
mysorf-base runtime validate

# Run a full bootstrap smoke test and print the RuntimeContext summary
mysorf-base bootstrap smoke

# Backward-compatible: bare overrides map to `config show`
mysorf-base logging=structlog
```

## Repository Layout

```text
mysorf-base/
├── conf/                # Source-of-truth Hydra config groups
│   ├── config.yaml      # Primary defaults list
│   ├── env/             # Environment profiles (local, dev, ci)
│   ├── logging/         # Logging backend configs
│   ├── tracking/        # Tracking backend configs
│   ├── profiling/       # Profiling backend configs
│   ├── artifacts/       # Artifact backend configs
│   └── sweeps/          # Sweeps backend configs
├── src/mysorf_base/     # Python package (src layout)
│   ├── config/          # Typed config composition and validation
│   ├── logging/         # Logger factory
│   ├── tracking/        # Tracker factory
│   ├── profiling/       # Profiler factory
│   ├── artifacts/       # Artifact manager factory
│   ├── sweeps/          # Sweep runner
│   ├── runtime/         # Bootstrap and RuntimeContext
│   ├── events/          # In-process event bus
│   ├── checkpoints/     # Checkpoint manager
│   ├── utils/           # sha256_config and shared utilities
│   └── cli.py           # `mysorf-base` CLI entrypoint
├── tests/               # Pytest + Hypothesis property-based tests
├── pyproject.toml       # Packaging and tool configuration
└── Makefile             # Local workflow commands
```

## Subsystem Layout Convention

Every subsystem follows the same internal structure:

```text
src/mysorf_base/<subsystem>/
├── __init__.py       # Shallow public API exports only
├── README.md         # Usage and API reference
├── core/
│   ├── schema.py     # @dataclass config schema
│   ├── interfaces.py # Protocol definitions
│   ├── factory.py    # build_xxx() + parse_xxx_config()
│   └── validate.py   # validate_xxx_config()
└── backends/         # Concrete implementations
```

## Optional Extras

| Extra | Installs | Enables |
|-------|----------|---------|
| `logging-rich` | `rich` | Rich terminal output with tracebacks |
| `logging-structlog` | `structlog` | Structured/JSON logging |
| `tracking-wandb` | `wandb` | Weights & Biases experiment tracking |
| `profiling-pandas` | `pandas` | DataFrame-based data profiling |
| `artifacts-s3` | `boto3` | S3 artifact storage |
| `artifacts-gcs` | `google-cloud-storage` | GCS artifact storage |

## Environment Variables

`mysorf_base.config` loads environment values before Hydra composition:

| Variable | Purpose |
|----------|---------|
| `MYSORF_BASE_WORKSPACE_ROOT` | Workspace root — `.env` loaded from here; resolvers use this path |
| `MYSORF_BASE_CONFIG_DIR` | Override the `conf/` directory path |
| `MYSORF_BASE_ENV_FILE` | Explicit `.env` file path |
| `MYSORF_BASE_ENV` | Select the Hydra `env` group (e.g. `ci`, `dev`, `local`) |

## Development

```bash
make check        # ruff + mypy + pytest
make format       # ruff format --fix
make test         # run test suite
make smoke-wheel  # build wheel + isolated import test
pre-commit run --all-files
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

## Citation

If this software is used in research, please cite it using the metadata in
[`CITATION.cff`](CITATION.cff) or the BibTeX below:

```bibtex
@software{mysorfbase2026,
    author = {Nguyen, Duc Danh},
    title = {mysorf-base: Reusable Python Infrastructure Subsystems},
    year = {2026},
    version = {0.1.0},
    url = {https://github.com/mysorf-9239/mysorf-base},
    license = {MIT}
}
```

## License

[MIT License](LICENSE) — Copyright (c) 2026 Nguyen Duc Danh (Mysorf)
