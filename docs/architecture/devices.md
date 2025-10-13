# Subsystem: Devices

## Purpose

Delivers Chromebook/device intake workflows: look up assets in RT, display ownership metadata, process check-in/out events, and capture CSV audit logs. Operators rely on this area for daily device management and troubleshooting.

## Entry Points

- Routes (`request_tracker_utils/routes/device_routes.py`):
  - `GET /devices/check-in` (+ `/check-in/<asset_name>`) → check-in UI (`device_checkin.html`).
  - `GET /devices/api/asset/<asset_name>` → REST lookup that enriches asset data and owner context.
  - `POST /devices/api/checkin` / `/checkout` (and batch variants) → JSON APIs for state changes.
  - `GET /devices/logs/download` → CSV export of audit trail.
  - Additional utilities include CSV import, Chromebook sync endpoints, and health checks.
- Templates: `device_checkin.html`, `device_checkout.html`, `checkin_logs.html` plus shared partials for status badges.
- CLI/Jobs: Under `scripts/` there are helper scripts (e.g., `sync_chromebook_data.py`) that indirectly reuse utility modules documented here.

## Dependencies

- Utility Modules:
  - `utils.rt_api` (`fetch_asset_data`, `fetch_user_data`, `get_assets_by_owner`, `rt_api_request`, `update_asset_custom_field`).
  - `utils.student_check_tracker.StudentDeviceTracker` for local SQLite state.
  - `utils.csv_logger` for log persistence and exports.
- External Services: RT REST API for asset/user data; Google Admin Directory API access occurs via `google_admin` (invoked by related scripts rather than blueprints).

## Configuration

- Environment Variables: `RT_URL`, `RT_TOKEN`, `API_ENDPOINT`, and `PORT` (surfaced in templates for API calls). Student tracker uses SQLite under `instance/` or `WORKING_DIR`.
- Files/Secrets: Student database lives at `instance/student_data/student_devices_*.json` and `instance/database.sqlite`; ensure appropriate backups.

## Logging & Error Handling

- Uses module-level logger (`logging.getLogger(__name__)`) to capture verbose telemetry (owner lookups, RT requests, CSV writes). Standardize formatting via shared logging helpers in later phases.
- Error responses typically include `error` + `tip` fields and HTTP status codes (404 for missing assets, 500 for API failures). Align with contracts during User Story 2.

## Testing Hooks

- Planned fixtures: fake RT responses and temporary SQLite DB via `tests/unit/conftest.py` to test check-in/out flows without live services.
- Manual smoke: simulate browser usage of `/devices/check-in` with sample asset name, confirm RT lookup, check-in, and CSV log append.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- Student tracker schema documented in `specs/002-ensure-my-flask/data-model.md` (Utility Module entity).

## Future Work

- Normalize blueprint prefix to `/devices` (already configured) and ensure future routes respect this namespace when reorganized.
- Wrap RT HTTP calls with shared retry helpers (T027) to consolidate error handling.
- Document interplay with Google Admin sync scripts once services package split lands.
