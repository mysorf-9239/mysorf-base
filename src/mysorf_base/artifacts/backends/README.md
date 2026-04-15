# Artifact Backends

`mysorf_base.artifacts.backends` contains concrete storage adapters for the
artifact subsystem.

Current backends:

- `local` — filesystem-backed implementation
- `disabled` — null/no-op implementation
- `s3` — Amazon S3-backed file artifact storage
- `gcs` — Google Cloud Storage-backed file artifact storage

Remote backend notes:

- S3 listing handles pagination explicitly through `ContinuationToken`
- GCS listing relies on the client iterator for pagination, but current
  `list_artifacts()` materializes the iterator into memory before sorting;
  callers with very large buckets should account for that behavior

## Adding a new backend

Production-oriented projects may need remote storage backends such as S3 or
GCS. `mysorf-base` now includes basic remote file backends and keeps the
extension contract intentionally small.

A new backend should:

1. implement the `ArtifactManager` protocol
2. support `save`, `load`, `resolve_path`, `list_artifacts`, `delete`
3. support `register_on_save_hook(...)`
4. define `finalize()` as safe during runtime teardown
5. keep backend-specific SDK imports local to the backend module

Recommended shape:

```text
mysorf_base/artifacts/backends/
├── local.py
├── null.py
└── s3.py
```

Implementation guidance:

- keep storage semantics behind the protocol, not in callers
- translate remote object layout to the same logical artifact model
- treat `finalize()` as idempotent when practical
- emit warnings instead of breaking the save path for optional hook failures
- add config validation and factory wiring before documenting the backend
