"""Stable hashing helpers for runtime reproducibility and cache identity."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, OmegaConf


def sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest for *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hex digest for the file at *path*."""
    digest = hashlib.sha256()
    with Path(path).expanduser().resolve().open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_for_hashing(value: Any) -> Any:
    """Convert config-like values to a deterministic JSON-serializable form."""
    if isinstance(value, DictConfig | ListConfig):
        return _normalize_for_hashing(OmegaConf.to_container(value, resolve=True))
    if is_dataclass(value):
        return _normalize_for_hashing(asdict(cast(Any, value)))
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_for_hashing(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_for_hashing(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def sha256_config(cfg: Any) -> str:
    """Return a deterministic SHA-256 hash for a config object or mapping."""
    normalized = _normalize_for_hashing(cfg)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(payload.encode("utf-8"))
