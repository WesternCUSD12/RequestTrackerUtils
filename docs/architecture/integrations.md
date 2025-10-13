# Subsystem: Integrations

## Purpose

Provides adapters to external SaaS (Google Workspace Admin, Request Tracker REST API), file-based imports, and scheduled synchronization jobs. Acts as glue between core blueprints and third-party systems.

## Entry Points

- Routes:
  - Student import/export endpoints use Google Admin CSV exports and RT API (see `student_routes.import_students`, `student_routes.export_students`).
  - Webhooks `POST /webhook/asset-created` (RT asset events) and `POST /webhook/student-check` (TBD) channel RT-driven updates into local state.
- CLI/Jobs:
  - `scripts/sync_chromebook_data.py`, `scheduled_chromebook_sync.fish` drive nightly Google Admin ↔ RT reconciliation.
  - `scripts/sync_rt_users.sh` and `scheduled_rt_user_sync.py` manage RT user provisioning.
  - Battery collectors (`gam_battery_collector.py`, `csv_battery_collector.py`) ingest device metrics for later reporting.
- Utilities:
  - `utils.google_admin` encapsulates Google API calls.
  - `utils.rt_api` wraps RT REST endpoints with rate limiting and retries.

## Dependencies

- Utility Modules: `utils.google_admin`, `utils.rt_api`, `utils.csv_logger` (for audit), future `utils/services` extraction.
- External Services: Google Admin Directory API, GAM CLI, Request Tracker REST API, local CSV exports.
- Scheduled Execution: systemd timer defined via Nix flake plus cron stubs in `docs/deployment/nixos.md`.

## Configuration

- Environment Variables:
  - `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_ADMIN_DELEGATED_USER`, `GOOGLE_ADMIN_SCOPES` for workspace access.
  - `RT_BASE_URL`, `RT_USERNAME`, `RT_PASSWORD`/token for RT sessions.
  - `SYNC_SCHEDULE` hints used by Nix modules; `WORKING_DIR` for logs/export staging.
- Files/Secrets:
  - `google-credentials.json` stored locally (should move to secret manager); `.csv` drop zone under `instance/student_data/`.
  - Nixops secret management for RT credentials (documented in deployment guide).

## Logging & Error Handling

- Integrations log to dedicated channel via `csv_logger` and standard Flask logging. Retry loops emit structured metadata (`attempt`, `response_code`).
- Error responses bubble up as `IntegrationError` (future) or generic HTTP 500; need consolidated error taxonomy (T027) and alerting hooks.

## Testing Hooks

- Existing tests: `scripts/test_battery_health_status.py`, `scripts/test_dual_battery_update.py` simulate RT API responses.
- Upcoming pytest modules to mock Google Admin service account and RT endpoints using `responses` pre-canned fixtures.
- Manual smoke: run `./scripts/list_custom_fields.py` with sandbox credentials, validate output.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- `docs/google_admin_integration.md` and `DEVICE_STUDENT_INTEGRATION.md` (legacy notes) inform migration path.

## Future Work

- Introduce integration service interfaces with dependency injection for easier testing.
- Centralize credential loading using `config.py` and environment adapters (T021/T022).
- Add monitoring/alerting for sync failures (PagerDuty or email) and infrastructure-as-code for scheduled jobs.
- `docs/architecture/_inputs/blueprint_registry.md`
- Additional captures: _TBD_

## Future Work

- _TBD_
