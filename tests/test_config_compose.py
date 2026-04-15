import os
import subprocess
import sys
from pathlib import Path

import pytest

from mysorf_base.config import compose_typed_config, redact_secrets
from mysorf_base.config.core.validate import validate_config

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_default_config_compose() -> None:
    cfg = compose_typed_config()

    assert cfg.app.name == "mysorf-base"
    assert cfg.env.name == "local"
    assert cfg.runtime.profile == "default"
    assert cfg.tracking.backend == "disabled"
    assert cfg.logging.backend == "console"
    # repo_root resolves to cwd — just verify it's an absolute path
    assert Path(cfg.paths.repo_root).is_absolute()
    assert cfg.paths.config_root.endswith("/conf")


def test_override_config_groups() -> None:
    cfg = compose_typed_config(["env=ci", "runtime=debug", "paths=test"])

    assert cfg.env.name == "ci"
    assert cfg.runtime.debug is True
    assert cfg.paths.output_dir.endswith("/tests/.outputs")


def test_wandb_requires_api_key_for_online_mode() -> None:
    cfg = compose_typed_config(["tracking=wandb", "tracking.wandb.mode=online"], validate=False)

    try:
        validate_config(cfg)
    except ValueError as exc:
        assert "WANDB_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected WandB validation to fail without an API key.")


def test_redaction_masks_wandb_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WANDB_API_KEY", "secret-value")
    cfg = compose_typed_config(["tracking=wandb"], validate=False)
    rendered = redact_secrets(cfg)

    assert "***REDACTED***" in rendered
    assert "secret-value" not in rendered


def test_compose_loads_dotenv_when_os_env_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MYSORF_BASE_ENV_FILE", raising=False)
    monkeypatch.delenv("MYSORF_BASE_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("WANDB_PROJECT", raising=False)
    (tmp_path / ".env").write_text("WANDB_PROJECT=dotenv-project\n", encoding="utf-8")

    cfg = compose_typed_config(["tracking=wandb"], validate=False)

    assert cfg.tracking.wandb.project == "dotenv-project"


def test_os_env_overrides_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MYSORF_BASE_ENV_FILE", raising=False)
    monkeypatch.delenv("MYSORF_BASE_WORKSPACE_ROOT", raising=False)
    monkeypatch.setenv("WANDB_PROJECT", "from-os")
    (tmp_path / ".env").write_text("WANDB_PROJECT=from-dotenv\n", encoding="utf-8")

    cfg = compose_typed_config(["tracking=wandb"], validate=False)

    assert cfg.tracking.wandb.project == "from-os"


def test_explicit_env_file_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    explicit = tmp_path / "custom.env"
    explicit.write_text("WANDB_PROJECT=explicit-project\n", encoding="utf-8")
    (tmp_path / ".env").write_text("WANDB_PROJECT=cwd-project\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MYSORF_BASE_ENV_FILE", str(explicit))
    monkeypatch.delenv("MYSORF_BASE_WORKSPACE_ROOT", raising=False)
    monkeypatch.delenv("WANDB_PROJECT", raising=False)

    cfg = compose_typed_config(["tracking=wandb"], validate=False)

    assert cfg.tracking.wandb.project == "explicit-project"


def test_cli_entrypoint_prints_composed_yaml() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    completed = subprocess.run(
        [sys.executable, "-m", "mysorf_base.cli", "runtime=debug", "tracking=disabled"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "profile: debug" in completed.stdout


def test_cli_config_show_subcommand_prints_composed_yaml() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mysorf_base.cli",
            "config",
            "show",
            "runtime=debug",
            "tracking=disabled",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "profile: debug" in completed.stdout


def test_cli_runtime_validate_subcommand_reports_success() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mysorf_base.cli",
            "runtime",
            "validate",
            "tracking=disabled",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "Runtime configuration is valid." in completed.stdout


def test_cli_bootstrap_smoke_subcommand_reports_runtime_details() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mysorf_base.cli",
            "bootstrap",
            "smoke",
            "tracking=disabled",
            "logging=disabled",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "app_name: mysorf-base" in completed.stdout
    assert "tracking_backend: disabled" in completed.stdout
    assert "Bootstrap smoke test passed." in completed.stdout
