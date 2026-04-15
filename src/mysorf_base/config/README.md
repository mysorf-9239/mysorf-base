# Config Subsystem

## Overview

`mysorf_base.config` is the configuration composition layer for the `mysorf-base` library. It is the only subsystem permitted to
interact with Hydra composition directly. All other subsystems receive their config section from a higher-level caller.

## Responsibilities

- compose application config from Hydra config groups under `conf/`
- merge composed config into a typed `AppConfig` schema
- validate cross-cutting runtime invariants
- resolve shared path conventions via OmegaConf resolvers
- redact known secrets before rendering config
- expose a library API and a CLI entrypoint

## Architecture

```text
mysorf_base/config/
├── __init__.py
├── core/
│   ├── compose.py     # compose_config, compose_typed_config, to_yaml, redact_secrets
│   ├── registry.py    # register_config_store
│   ├── resolvers.py   # OmegaConf custom resolvers
│   ├── schema.py      # AppConfig, AppSection, EnvSection, PathsSection, RuntimeSection
│   └── validate.py    # validate_config
└── docs/
    └── EXTENDING.md   # Extension guide for new subsystems
```

## Public API

```python

```

| Symbol                            | Description                                                                        |
|-----------------------------------|------------------------------------------------------------------------------------|
| `compose_config(overrides)`       | Returns raw `DictConfig`                                                           |
| `compose_typed_config(overrides)` | Returns typed `AppConfig` (validates by default)                                   |
| `load_env_files()`                | Loads discovered `.env` files into `os.environ` without overriding existing OS env |
| `to_yaml(overrides)`              | Renders composed config as a YAML string                                           |
| `redact_secrets(cfg)`             | Renders config with known secrets masked                                           |
| `validate_config(cfg)`            | Validates paths, runtime, and tracking invariants                                  |
| `register_config_store()`         | Registers structured config schemas with Hydra's ConfigStore                       |
| `AppConfig`                       | Typed top-level config dataclass                                                   |

## AppConfig Schema

```python
@dataclass
class AppConfig:
    app: AppSection       # name, subsystem, version
    env: EnvSection       # workspace, name, platform
    paths: PathsSection   # repo_root, config_root, output_dir, artifacts_dir, cache_dir
    runtime: RuntimeSection  # debug, seed, strict_config, profile
    logging: LoggingConfig    # owned by mysorf_base.logging
    tracking: TrackingConfig  # owned by mysorf_base.tracking
    profiling: ProfilingConfig  # owned by mysorf_base.profiling
    artifacts: ArtifactsConfig  # owned by mysorf_base.artifacts
    sweeps: SweepsConfig    # owned by mysorf_base.sweeps
```

All subsystem sections are typed `@dataclass` instances — access them as attributes,
not dict keys: `cfg.tracking.backend`, `cfg.tracking.wandb.project`, `cfg.logging.level`.

### `RuntimeSection` defaults

| Field           | Type   | Default     | Description                 |
|-----------------|--------|-------------|-----------------------------|
| `debug`         | `bool` | `false`     | Enable debug mode           |
| `seed`          | `int`  | `7`         | Global random seed          |
| `strict_config` | `bool` | `true`      | Fail on unknown config keys |
| `profile`       | `str`  | `"default"` | Execution profile name      |

## Usage

### Compose config programmatically

```python
from mysorf_base.config import compose_typed_config

cfg = compose_typed_config(["env=ci", "logging=structlog", "runtime.seed=42"])
print(cfg.runtime.seed)  # 42
print(cfg.env.name)  # "ci"
```

### Render config as YAML

```python
from mysorf_base.config import to_yaml

print(to_yaml(["tracking=wandb"]))
```

### Redact secrets before logging

```python
from mysorf_base.config import compose_typed_config, redact_secrets

cfg = compose_typed_config(["tracking=wandb"])
print(redact_secrets(cfg))  # tracking.wandb.api_key: ***REDACTED***
```

### Environment loading

Before Hydra composition, `mysorf_base.config` loads environment values from:

1. `MYSORF_BASE_ENV_FILE`
2. `MYSORF_BASE_WORKSPACE_ROOT/.env`
3. `cwd/.env`

Existing OS environment variables always win over `.env` file values.

```python
from mysorf_base.config import load_env_files

load_env_files()
```

### CLI entrypoint

```bash
python -m mysorf_base.cli logging=console tracking=disabled runtime.seed=42
```

## Secret Handling

Secrets must not be committed to `conf/`. Use `oc.env` interpolation in YAML:

```yaml
# conf/tracking/wandb.yaml
wandb:
  api_key: ${oc.env:WANDB_API_KEY,null}
```

Secrets masked by `redact_secrets()`:

Any dict key whose name (case-insensitive) matches one of the following at **any
nesting depth** is replaced with `***REDACTED***`:

`api_key` · `token` · `secret` · `password` · `credential`

No hardcoded paths — new backends with sensitive fields are redacted automatically
as long as their config keys follow this convention.

## Design Rules

- `mysorf_base.config` is the only composition layer.
- Subsystem schemas stay in the owning subsystem.
- Secrets live in environment variables, not committed YAML.
- Public imports are shallow through `mysorf_base.config`.
- Validation fails early with clear messages.
