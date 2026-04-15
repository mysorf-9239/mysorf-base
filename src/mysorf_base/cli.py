"""CLI entrypoint for mysorf-base."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .config import compose_typed_config, redact_secrets
from .runtime import bootstrap


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mysorf-base",
        description="Infrastructure-oriented CLI for mysorf-base.",
    )
    subparsers = parser.add_subparsers(dest="command")

    config_parser = subparsers.add_parser(
        "config",
        help="Inspect composed configuration.",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command")
    config_show = config_subparsers.add_parser(
        "show",
        help="Compose, validate, and print the effective config.",
    )
    config_show.add_argument("overrides", nargs="*", help="Hydra override strings.")

    runtime_parser = subparsers.add_parser(
        "runtime",
        help="Validate runtime configuration.",
    )
    runtime_subparsers = runtime_parser.add_subparsers(dest="runtime_command")
    runtime_validate = runtime_subparsers.add_parser(
        "validate",
        help="Compose config and validate runtime semantics.",
    )
    runtime_validate.add_argument("overrides", nargs="*", help="Hydra override strings.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Run bootstrap-oriented diagnostics.",
    )
    bootstrap_subparsers = bootstrap_parser.add_subparsers(dest="bootstrap_command")
    bootstrap_smoke = bootstrap_subparsers.add_parser(
        "smoke",
        help="Run a bootstrap smoke test and print core runtime details.",
    )
    bootstrap_smoke.add_argument("overrides", nargs="*", help="Hydra override strings.")

    return parser


def _print_config(overrides: Sequence[str]) -> int:
    cfg = compose_typed_config(list(overrides))
    print(redact_secrets(cfg), end="")
    return 0


def _validate_runtime(overrides: Sequence[str]) -> int:
    compose_typed_config(list(overrides))
    print("Runtime configuration is valid.")
    return 0


def _bootstrap_smoke(overrides: Sequence[str]) -> int:
    with bootstrap(list(overrides)) as ctx:
        summary = {
            "app_name": ctx.cfg.app.name,
            "run_id": ctx.run_id,
            "logging_backend": ctx.cfg.logging.backend,
            "tracking_backend": ctx.cfg.tracking.backend,
            "profiling_backend": ctx.cfg.profiling.backend,
            "artifacts_backend": ctx.cfg.artifacts.backend,
        }
    for key, value in summary.items():
        print(f"{key}: {value}")
    print("Bootstrap smoke test passed.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])

    # Backward-compatible behavior: bare Hydra overrides map to `config show`.
    if not args or args[0] not in {"config", "runtime", "bootstrap"}:
        return _print_config(args)

    parser = _build_parser()
    namespace = parser.parse_args(args)

    if namespace.command == "config":
        if namespace.config_command != "show":
            parser.error("config requires a subcommand.")
        return _print_config(namespace.overrides)

    if namespace.command == "runtime":
        if namespace.runtime_command != "validate":
            parser.error("runtime requires a subcommand.")
        return _validate_runtime(namespace.overrides)

    if namespace.command == "bootstrap":
        if namespace.bootstrap_command != "smoke":
            parser.error("bootstrap requires a subcommand.")
        return _bootstrap_smoke(namespace.overrides)

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
