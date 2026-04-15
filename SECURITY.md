# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Security vulnerabilities must not be reported through public GitHub issues.

Report vulnerabilities privately by emailing:

**uydanh214@gmail.com** (Nguyen Duc Danh)

Include the following in the report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- Affected versions.

A response will be provided within 72 hours. Confirmed vulnerabilities will be
patched as soon as possible. Reporters will be credited unless anonymity is
requested.

## Security Considerations

### Secrets and Credentials

- API keys and credentials must not be committed to `conf/` YAML files.
- Use `oc.env` interpolation in YAML to read secrets at composition time:
  `api_key: ${oc.env:WANDB_API_KEY,null}`
- Store secrets in a `.env` file at the workspace root (loaded automatically
  by `mysorf_base.config` before Hydra composition) or export them as OS
  environment variables. Never commit `.env` to version control.
- The `redact_secrets()` function recursively scans the entire config tree and
  masks any key whose name (case-insensitive) matches a sensitive keyword.

### Secret Key Detection

`redact_secrets()` masks values at **any nesting depth** for keys matching:

| Keyword | Example fields masked |
|---|---|
| `api_key` | `tracking.wandb.api_key`, any future backend |
| `token` | `auth.token`, `storage.access_token` |
| `secret` | `oauth.client_secret` |
| `password` | `db.password` |
| `credential` | `cloud.credential` |

No path-specific configuration is required — new backends are covered
automatically as long as their sensitive fields follow this naming convention.

### Dependency Security

- All dependencies are pinned with upper bounds in `pyproject.toml`.
- `bandit` runs as part of the pre-commit pipeline to detect common security
  issues in source code.
- Run `pip audit` periodically to check for known vulnerabilities in
  installed dependencies.
