"""Google Cloud Storage-backed artifact manager implementation."""

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


def _build_gcs_client(project: str | None) -> Any:
    try:
        storage = import_module("google.cloud.storage")
    except ImportError as exc:
        raise RuntimeError(
            "google-cloud-storage is not installed. Install mysorf-base with the 'artifacts-gcs' extra."
        ) from exc
    return storage.Client(project=project)


class GCSBackend:
    """Artifact manager backed by Google Cloud Storage.

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
        project: str | None = None,
    ) -> None:
        self._bucket_name = bucket
        self._prefix = prefix.strip("/")
        self._cache_dir = Path(cache_dir)
        self._strategy = VersioningStrategy(versioning_strategy)
        self._run_id = run_id
        self._tracker = tracker
        self._project = project
        self._on_save_hooks: list[Callable[[ArtifactRecord], None]] = []
        self._client: Any | None = None

    def _gcs(self) -> Any:
        if self._client is None:
            self._client = _build_gcs_client(self._project)
        return self._client

    def _bucket(self) -> Any:
        return self._gcs().bucket(self._bucket_name)

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

    def resolve_path(self, name: str, artifact_type: ArtifactType, version: str) -> Path:
        return Path(f"gs://{self._bucket_name}/{self._prefix_key(name, artifact_type, version)}")

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
            raise ValueError("GCSBackend currently supports file artifacts only.")

        resolved_version = self._resolve_version(version)
        key = self._object_key(name, artifact_type, resolved_version, src.name)
        blob = self._bucket().blob(key)
        blob.upload_from_filename(str(src))

        record = ArtifactRecord(
            name=name,
            version=resolved_version,
            path=Path(f"gs://{self._bucket_name}/{key}"),
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
        blobs = list(self._gcs().list_blobs(self._bucket_name, prefix=prefix))
        if not blobs:
            raise ArtifactNotFoundError(
                f"Artifact not found: name={name!r}, type={artifact_type.value!r}, version={version!r}"
            )
        blob = sorted(blobs, key=lambda item: item.name)[-1]
        target = self._cache_dir / "gcs" / self._bucket_name / str(blob.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(target))
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
        blobs = list(self._gcs().list_blobs(self._bucket_name, prefix=prefix))
        records: list[ArtifactRecord] = []
        for blob in blobs:
            parts = blob.name.split("/")
            if len(parts) < 5:
                continue
            _, type_name, artifact_name, version_name, _ = parts[-5:]
            updated = getattr(blob, "updated", None) or datetime.now(tz=UTC)
            records.append(
                ArtifactRecord(
                    name=artifact_name,
                    version=version_name,
                    path=Path(f"gs://{self._bucket_name}/{blob.name}"),
                    artifact_type=ArtifactType(type_name),
                    size_bytes=int(getattr(blob, "size", 0) or 0),
                    created_at=updated,
                )
            )
        records.sort(key=lambda record: record.created_at)
        return records

    def delete(self, name: str, artifact_type: ArtifactType, version: str) -> None:
        prefix = self._prefix_key(name, artifact_type, version)
        blobs = list(self._gcs().list_blobs(self._bucket_name, prefix=prefix))
        if not blobs:
            raise ArtifactNotFoundError(
                f"Artifact not found: name={name!r}, type={artifact_type.value!r}, version={version!r}"
            )
        for blob in blobs:
            blob.delete()

    def register_on_save_hook(self, hook: Callable[[ArtifactRecord], None]) -> None:
        self._on_save_hooks.append(hook)

    def finalize(self) -> None:
        """Finalize remote client resources."""
