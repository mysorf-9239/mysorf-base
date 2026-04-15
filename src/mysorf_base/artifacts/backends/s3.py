"""S3-backed artifact manager implementation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core.exceptions import ArtifactNotFoundError
from ..core.schema import ArtifactRecord, ArtifactType, VersioningStrategy

if TYPE_CHECKING:
    from mysorf_base.tracking.core.interfaces import Tracker

logger = logging.getLogger(__name__)


def _build_s3_client(region: str | None) -> Any:
    try:
        boto3 = import_module("boto3")
    except ImportError as exc:
        raise RuntimeError(
            "boto3 is not installed. Install mysorf-base with the 'artifacts-s3' extra."
        ) from exc
    return boto3.client("s3", region_name=region)


class S3Backend:
    """Artifact manager backed by Amazon S3.

    Remote backends currently support file artifacts only.
    """

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "artifacts",
        cache_dir: str,
        versioning_strategy: str = "run_id",
        run_id: str | None = None,
        tracker: Tracker | None = None,
        region: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._cache_dir = Path(cache_dir)
        self._strategy = VersioningStrategy(versioning_strategy)
        self._run_id = run_id
        self._tracker = tracker
        self._region = region
        self._on_save_hooks: list[Callable[[ArtifactRecord], None]] = []
        self._client: Any | None = None

    def _s3(self) -> Any:
        if self._client is None:
            self._client = _build_s3_client(self._region)
        return self._client

    def _resolve_version(self, version: str | None) -> str:
        if self._strategy == VersioningStrategy.RUN_ID:
            if version is not None:
                return version
            if self._run_id is None:
                raise ValueError(
                    "versioning_strategy=RUN_ID requires run_id to be set on the manager."
                )
            return self._run_id
        if self._strategy == VersioningStrategy.EPOCH:
            if version is None:
                raise ValueError(
                    "versioning_strategy=EPOCH requires an explicit version (epoch number)."
                )
            return f"epoch_{int(version):04d}"
        if self._strategy == VersioningStrategy.TIMESTAMP:
            return version or datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        if version is None:
            raise ValueError("versioning_strategy=MANUAL requires an explicit version string.")
        return version

    def _object_key(
        self, name: str, artifact_type: ArtifactType, version: str, filename: str
    ) -> str:
        return "/".join(
            part for part in (self._prefix, artifact_type.value, name, version, filename) if part
        )

    def _prefix_key(
        self, name: str, artifact_type: ArtifactType, version: str | None = None
    ) -> str:
        return "/".join(
            part for part in (self._prefix, artifact_type.value, name, version or "") if part
        )

    def _list_objects(self, prefix: str) -> list[dict[str, Any]]:
        contents: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {"Bucket": self._bucket, "Prefix": prefix}
        while True:
            response = self._s3().list_objects_v2(**kwargs)
            page = response.get("Contents", [])
            if isinstance(page, list):
                contents.extend(page)
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
            if token is None:
                break
            kwargs["ContinuationToken"] = token
        return contents

    def resolve_path(self, name: str, artifact_type: ArtifactType, version: str) -> Path:
        return Path(f"s3://{self._bucket}/{self._prefix_key(name, artifact_type, version)}")

    def save(
        self,
        source: Path | str,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> ArtifactRecord:
        src = Path(source)
        if not src.exists():
            raise ArtifactNotFoundError(f"Source path does not exist: {src}")
        if src.is_dir():
            raise ValueError("S3Backend currently supports file artifacts only.")

        resolved_version = self._resolve_version(version)
        key = self._object_key(name, artifact_type, resolved_version, src.name)
        self._s3().upload_file(str(src), self._bucket, key)

        record = ArtifactRecord(
            name=name,
            version=resolved_version,
            path=Path(f"s3://{self._bucket}/{key}"),
            artifact_type=artifact_type,
            size_bytes=src.stat().st_size,
            created_at=datetime.now(tz=UTC),
        )

        if self._tracker is not None:
            try:
                self._tracker.log_artifact(str(record.path), name=record.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "tracker.log_artifact() failed after saving artifact %r: %s", name, exc
                )

        for hook in self._on_save_hooks:
            try:
                hook(record)
            except Exception as exc:  # noqa: BLE001
                logger.warning("artifact save hook failed for artifact %r: %s", name, exc)
        return record

    def load(
        self,
        name: str,
        artifact_type: ArtifactType,
        version: str | None = None,
    ) -> Path:
        prefix = self._prefix_key(name, artifact_type, version)
        contents = self._list_objects(prefix)
        if not contents:
            raise ArtifactNotFoundError(
                f"Artifact not found: name={name!r}, type={artifact_type.value!r}, version={version!r}"
            )
        key = str(sorted(item["Key"] for item in contents)[-1])
        target = self._cache_dir / "s3" / self._bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        self._s3().download_file(self._bucket, key, str(target))
        return target

    def list_artifacts(
        self,
        artifact_type: ArtifactType | None = None,
        name: str | None = None,
    ) -> list[ArtifactRecord]:
        prefix = "/".join(
            part
            for part in (self._prefix, artifact_type.value if artifact_type else "", name or "")
            if part
        )
        records: list[ArtifactRecord] = []
        for item in self._list_objects(prefix):
            key = item["Key"]
            parts = key.split("/")
            if len(parts) < 5:
                continue
            _, type_name, artifact_name, version_name, filename = parts[-5:]
            records.append(
                ArtifactRecord(
                    name=artifact_name,
                    version=version_name,
                    path=Path(f"s3://{self._bucket}/{key}"),
                    artifact_type=ArtifactType(type_name),
                    size_bytes=int(item.get("Size", 0)),
                    created_at=item.get("LastModified", datetime.now(tz=UTC)),
                )
            )
        records.sort(key=lambda record: record.created_at)
        return records

    def delete(self, name: str, artifact_type: ArtifactType, version: str) -> None:
        prefix = self._prefix_key(name, artifact_type, version)
        contents = self._list_objects(prefix)
        if not contents:
            raise ArtifactNotFoundError(
                f"Artifact not found: name={name!r}, type={artifact_type.value!r}, version={version!r}"
            )
        for item in contents:
            self._s3().delete_object(Bucket=self._bucket, Key=item["Key"])

    def register_on_save_hook(self, hook: Callable[[ArtifactRecord], None]) -> None:
        self._on_save_hooks.append(hook)

    def finalize(self) -> None:
        """Finalize remote client resources."""
