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
- Routes (`request_tracker_utils/routes/audit_routes.py`) - **NEW** (Feature 004-student-device-audit):
  - `POST /devices/audit/upload` → CSV upload endpoint for creating audit sessions with student lists
  - `GET /devices/audit/session/<session_id>` → Main audit interface showing student list
  - `GET /devices/audit/session/<session_id>/students` → JSON API for filtered student list (supports search by name/grade/advisor)
  - `GET /devices/audit/student/<student_id>` → Device verification interface for selected student
  - `GET /devices/audit/student/<student_id>/devices` → JSON API querying RT for student's assigned devices (with retry logic)
  - `POST /devices/audit/student/<student_id>/verify` → Submit device verification with notes
  - `GET /devices/audit/session/<session_id>/completed` → View completed audits in session
  - `POST /devices/audit/student/<student_id>/re-audit` → Restore student to active audit list
  - `GET /devices/audit/notes` → IT staff view of all audit notes with filtering
  - `GET /devices/audit/notes/export` → CSV export of audit notes
- Templates: `device_checkin.html`, `device_checkout.html`, `checkin_logs.html` plus shared partials for status badges.
- Audit Templates - **NEW**:
  - `audit_upload.html` → CSV file upload form and searchable student list
  - `audit_verify.html` → Device verification form with RT device display and notes field
  - `audit_history.html` → Completed audits view with re-audit capability
  - `audit_report.html` → IT staff notes review interface with filtering
- CLI/Jobs: Under `scripts/` there are helper scripts (e.g., `sync_chromebook_data.py`) that indirectly reuse utility modules documented here.

## Dependencies

- Utility Modules:
  - `utils.rt_api` (`fetch_asset_data`, `fetch_user_data`, `get_assets_by_owner`, `rt_api_request`, `update_asset_custom_field`).
  - `utils.student_check_tracker.StudentDeviceTracker` for local SQLite state.
  - `utils.csv_logger` for log persistence and exports.
  - `utils.csv_validator` (**NEW**) - CSV parsing, column validation, duplicate detection, encoding detection for audit uploads
  - `utils.audit_tracker` (**NEW**) - Audit session management: create_session(), add_students(), mark_student_audited(), get_completed_audits(), restore_student_for_reaudit()
- Database Tables (**NEW** for audits):
  - `audit_sessions` - Session tracking with creator, status, student_count
  - `audit_students` - Student records with name/grade/advisor, audit status, composite key (name+grade+advisor)
  - `audit_device_records` - Device verification records linked to audits
  - `audit_notes` - IT staff notes for follow-up on missing devices
- External Services: RT REST API for asset/user data; Google Admin Directory API access occurs via `google_admin` (invoked by related scripts rather than blueprints).

## Configuration

- Environment Variables: `RT_URL`, `RT_TOKEN`, `API_ENDPOINT`, and `PORT` (surfaced in templates for API calls). Student tracker uses SQLite under `instance/` or `WORKING_DIR`.

## Testing Hooks

- Planned fixtures: fake RT responses and temporary SQLite DB via `tests/unit/conftest.py` to test check-in/out flows without live services.
- Audit Testing (**NEW**):
  - `tests/unit/test_csv_validator.py` - CSV parsing validation with sample files (valid, invalid, duplicates, various encodings)
  - `tests/unit/test_audit_tracker.py` - Session management, student addition, audit completion, re-audit workflows
  - `tests/integration/test_audit_workflow.py` - End-to-end audit flow: CSV upload → RT query → verification → completion
  - `tests/fixtures/` - Sample CSV files for testing (valid, invalid columns, duplicates)
- Manual smoke: simulate browser usage of `/devices/check-in` with sample asset name, confirm RT lookup, check-in, and CSV log append.
- Uses module-level logger (`logging.getLogger(__name__)`) to capture verbose telemetry (owner lookups, RT requests, CSV writes). Standardize formatting via shared logging helpers in later phases.
- Error responses typically include `error` + `tip` fields and HTTP status codes (404 for missing assets, 500 for API failures). Align with contracts during User Story 2.

## Testing Hooks

- Planned fixtures: fake RT responses and temporary SQLite DB via `tests/unit/conftest.py` to test check-in/out flows without live services.
- Manual smoke: simulate browser usage of `/devices/check-in` with sample asset name, confirm RT lookup, check-in, and CSV log append.

## Evidence

## Future Work

- Normalize blueprint prefix to `/devices` (already configured) and ensure future routes respect this namespace when reorganized.
- Wrap RT HTTP calls with shared retry helpers (T027) to consolidate error handling.
- Document interplay with Google Admin sync scripts once services package split lands.
- Audit feature enhancements (post-004):
  - Add feedback survey mechanism for SC-007 (80% satisfaction target)
  - Implement load testing for SC-008 (10 concurrent users)
  - Consider baseline measurement strategy for SC-004 (40% productivity improvement)
  - Add auto-cleanup cron job for audit_sessions (currently manual via delete_old_sessions())

---

**Last Updated**: December 1, 2025 (Feature 004-student-device-audit documentation)

## Future Work

- Normalize blueprint prefix to `/devices` (already configured) and ensure future routes respect this namespace when reorganized.
- Wrap RT HTTP calls with shared retry helpers (T027) to consolidate error handling.
- Document interplay with Google Admin sync scripts once services package split lands.
