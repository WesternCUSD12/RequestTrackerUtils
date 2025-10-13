# Subsystem: Students

## Purpose

Surfacing Chromebook assignment insights tied to student records. Handles student roster management, device checkout workflows, reconciliation of RT asset ownership, and reporting dashboards surfaced through the web UI.

## Entry Points

- Routes (`request_tracker_utils/routes/student_routes.py`):
  - `GET /students/api/students/health` → health endpoint for monitoring.
  - `GET /students/student-devices` → student dashboard (`student_devices.html`).
  - `GET /students/device-checkout` → checkout UI (`device_checkout.html`).
  - `GET /students/api/students` (+ `/<id>`) → JSON APIs for roster data with optional RT enrichment.
  - `POST /students/api/students/<id>/checkout` / `/checkin` → orchestrate StudentDeviceTracker operations and RT ownership updates.
  - Supporting routes create RT tickets, upload CSVs, and download reports.
- Templates: `student_devices.html`, `student_checkin.html`, `device_checkout.html`, `checkin_logs.html` (shared with Devices).
- CLI/Jobs: `scripts/update_rt_user_custom_fields.py`, `scripts/sync_rt_users.sh`, etc., run outside Flask but interact with the same SQLite dataset.

## Dependencies

- Utility Modules:
  - `utils.student_check_tracker.StudentDeviceTracker` (SQLite accessor + business rules).
  - `utils.rt_api` (`fetch_user_data`, `get_assets_by_owner`, `update_asset_owner`, `create_ticket`).
  - `utils.csv_logger` and local CSV helpers for audit exports.
- External Systems:
  - Request Tracker (asset + ticket APIs).
  - Google Admin API (via `utils.google_admin`) when syncing Chromebook status (integrations doc covers details).

## Configuration

- Environment Variables: `PORT` exposes the API port used by front-end fetch requests; RT credentials mirror other blueprints.
- Files/Secrets: Student roster JSON/SQLite database resides under `instance/student_data/` and `instance/database.sqlite`; ensure persistence between deploys.

## Logging & Error Handling

- Uses module-level logger to capture stack traces when StudentDeviceTracker operations fail; wraps exceptions in JSON responses with descriptive `error`/`details` fields.
- Add standardized JSON envelopes and redaction per logging/error contracts during User Story 2.

## Testing Hooks

- Planned fixtures: temporary SQLite database seeded with sample students to cover check-in/out flows; RT access mocked.
- Manual smoke: generate roster via import, exercise `/students/device-checkout` UI, confirm RT ownership transitions.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- Student tracker schema and workflow notes: `specs/002-ensure-my-flask/research.md` & `data-model.md`.

## Future Work

- Normalize blueprint prefix (currently registered at root; to be moved under `/students` in T024).
- Document background sync cadence once Google Admin integration is refactored into services package.
- Add monitoring guidance for backlog catch-up tasks (tickets auto-created, RT ownership mismatches).
