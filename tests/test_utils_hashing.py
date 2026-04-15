"""Tests for hashing helpers used by runtime reproducibility flows."""

from __future__ import annotations

from pathlib import Path

from mysorf_base.config import compose_typed_config
from mysorf_base.utils import sha256_bytes, sha256_config, sha256_file


def test_sha256_bytes_is_stable() -> None:
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")


def test_sha256_file_matches_bytes(tmp_path: Path) -> None:
    path = tmp_path / "payload.txt"
    path.write_text("payload", encoding="utf-8")

    assert sha256_file(path) == sha256_bytes(b"payload")


def test_sha256_config_is_stable_for_equivalent_configs() -> None:
    cfg1 = compose_typed_config(["tracking=disabled", "logging=disabled"])
    cfg2 = compose_typed_config(["logging=disabled", "tracking=disabled"])

    assert sha256_config(cfg1) == sha256_config(cfg2)


def test_sha256_config_preserves_scalar_json_semantics() -> None:
    cfg1 = {"flag": True, "none": None, "value": 1.0}
    cfg2 = {"none": None, "value": 1.0, "flag": True}

    assert sha256_config(cfg1) == sha256_config(cfg2)


def test_sha256_config_distinguishes_different_float_values() -> None:
    cfg1 = {"value": 1.0}
    cfg2 = {"value": 1.00000000001}

    assert sha256_config(cfg1) != sha256_config(cfg2)
