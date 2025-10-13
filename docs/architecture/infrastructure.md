# Subsystem: Infrastructure

## Purpose

Defines how the Flask application runs locally, in test harnesses, and in production-like environments. Covers Nix-based provisioning, dependency packaging, database storage, and static asset serving.

## Entry Points

- Runtime:
  - `run.py` creates the Flask app, registers blueprints, and starts the dev server.
  - `devenv.nix` / `devenv.yaml` provide reproducible local shells with Python 3.11, Node, GAM, etc.
- Deployment:
  - `flake.nix` packages the service into a NixOS module and systemd unit `request-tracker-utils`.
  - `docs/deployment/nixos.md` documents rebuild, rollback, and secrets provisioning.

## Dependencies

- Runtime Services: systemd-managed Flask service (gunicorn optional), Celery stub (future), scheduled cron/timer jobs for sync scripts.
- Data Stores: SQLite database at `instance/database.sqlite`; static JSON/CSV artifacts under `instance/student_data/` and `instance/logs/`.
- Observability: currently file-based logs; future ELK integration and metrics endpoints pending.

## Configuration

- Environment Variables:
  - `FLASK_ENV`, `PORT`, `WORKING_DIR`, `DATABASE_URL` (optional override), `GOOGLE_*`, `RT_*` credentials.
- Secrets/Files:
  - `google-credentials.json`, `.env` for local overrides, Nixops secrets for production tokens.
  - Static assets under `request_tracker_utils/static/` and templates under `templates/` served via Flask.

## Logging & Monitoring

- Logs emitted via Flask’s `app.logger` and written to `instance/logs/` by default; systemd captures stdout/stderr in journal.
- Health: manual smoke via hitting `/` and key endpoints; add `/healthz` route and structured logging in upcoming tasks (T026/T029).

## Testing Hooks

- Local harness: `pytest` configured in `pyproject.toml`; run inside Nix dev shell (`pytest` from repo root or `cd src pytest`).
- CI/CD: none yet; plan to add GitHub Actions with lint (`ruff`), type (`mypy`), and test stages.
- Infrastructure smoke: `scripts/test_sqlite.py` and `test_rt_api.fish` ensure database and RT connectivity.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- [`docs/configuration/current_env_matrix.md`](../configuration/current_env_matrix.md)
- `docs/deployment/nixos.md` for systemd/service details.

## Future Work

- Containerize application (optional) or extend Nix module for staging environments.
- Introduce central secrets management (Vault/SOPS) and automated migrations.
- Add observability stack (Prometheus exporter, structured logging backend) and formal incident runbooks.
- `docs/architecture/_inputs/blueprint_registry.md`
- Additional captures: _TBD_

## Future Work

- _TBD_
