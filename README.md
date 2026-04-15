# mysorf-base

**mysorf-base** is a reusable Python infrastructure library for ML and research projects.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

It composes infrastructure once, wraps it in a single runtime context, and injects that context into application code — so domain code never calls vendor SDKs directly.

## Subsystems

| Subsystem | Status | Description |
|-----------|--------|-------------|
| [`config`](src/mysorf_base/config/README.md) | Stable | Hydra/OmegaConf composition, typed schema, validation |
| [`logging`](src/mysorf_base/logging/README.md) | Stable | Logger factory with 4 backends (console, file, structlog, rich) |
| [`tracking`](src/mysorf_base/tracking/README.md) | Stable | Experiment tracker with Weights & Biases backend |
| [`profiling`](src/mysorf_base/profiling/README.md) | Stable | Lightweight tabular data profiling |
| [`artifacts`](src/mysorf_base/artifacts/README.md) | Stable | Artifact save/load/version management |
| [`sweeps`](src/mysorf_base/sweeps/README.md) | Stable | Hyperparameter search (grid, random, wandb) |
| [`runtime`](src/mysorf_base/runtime/README.md) | Stable | Bootstrap orchestration, `RuntimeContext` |
| [`events`](src/mysorf_base/events/README.md) | Stable | Lightweight in-process event bus |
| [`checkpoints`](src/mysorf_base/checkpoints/README.md) | Stable | Checkpoint save/load with event emission |

## Installation

### From GitHub

```bash
pip install git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0
```

### With optional extras

```bash
# Rich terminal logging
pip install "mysorf-base[logging-rich] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0"

# Weights & Biases tracking
pip install "mysorf-base[tracking-wandb] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0"

# All optional backends
pip install "mysorf-base[all] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0"
```

### In pyproject.toml

```toml
[project]
dependencies = [
    "mysorf-base @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0",
]

[project.optional-dependencies]
ml = [
    "mysorf-base[tracking-wandb,logging-rich] @ git+https://github.com/mysorf-9239/mysorf-base.git@v0.1.0",
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
    ctx.logger.info(f"Run started: {ctx.run_id}")
    ctx.tracker.start_run(run_name="baseline")
    ctx.tracker.log_metrics({"loss": 0.42}, step=1)
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
        loss = train_model(lr=float(params["lr"]))
        return {"loss": loss}

    summary = run_sweep(space, trial_fn, ctx, SweepsConfig(strategy="grid"))
    best = summary.best_trial("loss", mode="min")
```

### Artifact management

```python
from pathlib import Path
from mysorf_base.runtime import bootstrap
from mysorf_base.artifacts import ArtifactType

with bootstrap() as ctx:
    ctx.artifact_manager.save(
        Path("model.pt"), "model", artifact_type=ArtifactType.CHECKPOINT
    )
```

## CLI

```bash
# Inspect the effective composed config
mysorf-base

# With overrides
mysorf-base logging=structlog tracking=wandb runtime.seed=42

# Subcommands
mysorf-base config show
mysorf-base runtime validate
mysorf-base bootstrap smoke
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
│   ├── config/          # Config composition layer
│   ├── logging/         # Logging subsystem
│   ├── tracking/        # Tracking subsystem
│   ├── profiling/       # Profiling subsystem
│   ├── artifacts/       # Artifact management
│   ├── sweeps/          # Hyperparameter search
│   ├── runtime/         # Bootstrap orchestration
│   ├── events/          # In-process event bus
│   ├── checkpoints/     # Checkpoint management
│   ├── utils/           # Shared utilities
│   └── cli.py           # `mysorf-base` CLI entrypoint
├── tests/               # Test suite (pytest + hypothesis)
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
│   ├── schema.py     # @dataclass config schema and data models
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
| `profiling-pandas` | `pandas` | DataFrame-based profiling |
| `artifacts-s3` | `boto3` | S3 artifact storage |
| `artifacts-gcs` | `google-cloud-storage` | GCS artifact storage |

```bash
pip install -e ".[logging-rich,tracking-wandb]"
```

## Environment Variables

`mysorf_base.config` loads environment values before Hydra composition using this precedence:

1. existing OS environment variables
2. file from `MYSORF_BASE_ENV_FILE`
3. `.env` under `MYSORF_BASE_WORKSPACE_ROOT`
4. `.env` in the current working directory

Config files use `oc.env` interpolation; `.env` is a convenient way to populate `os.environ`.

## Development

```bash
make check    # ruff + mypy + pytest
make format   # ruff format --fix
make test     # run test suite
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
