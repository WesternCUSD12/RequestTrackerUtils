# Subsystem: Tags

## Purpose

Owns asset-tag sequencing, confirmation logging, and webhook workflows that bridge RT asset creation with local numbering rules. Provides shared helpers (`AssetTagManager`) consumed by asset and label features.

## Entry Points

- Routes (`request_tracker_utils/routes/tag_routes.py`):
  - `GET /next-asset-tag` → preview next tag without side effects.
  - `POST /confirm-asset-tag` → increments sequence, logs confirmation, updates RT asset name.
  - `POST /reset-asset-tag` → admin tool to reseed sequence files.
  - `POST /update-asset-name` → manual RT rename for reconciliation.
  - `POST /webhook/asset-created` → invoked by RT Scrip to assign tags on new assets.
  - Admin UI endpoints render `asset_tag_admin.html` for manual review.
- Templates: `asset_tag_admin.html`, `asset_create.html` (shared). Sequence files surfaced in UI via read-only status tables.
- CLI/Jobs: `scripts/update_all_labels.py`, `scripts/add_battery_health_field.py`, etc., rely on the same helpers for consistency.

## Dependencies

- Utility Modules:
  - `utils.rt_api` for asset fetch/update operations and HTTP wrappers.
- External Systems: RT REST API; file system for sequence/log persistence.
- Shared Class: `AssetTagManager` (in this module) consumed by `asset_routes` and tests.

## Configuration

- Environment Variables: `WORKING_DIR` (sequence/log location), `PREFIX` (default tag prefix), optional dynamic prefixes supplied via request parameters.
- Files/Secrets: Sequence files (`asset_tag_sequence*.txt`) and `asset_tag_confirmations.log`; ensure proper file permissions in deployment.

## Logging & Error Handling

- Writes confirmations to rotating log file plus `current_app.logger` for webhook activity. Harmonize via shared logging infrastructure in later tasks.
- Returns JSON errors with descriptive `error` messages; follow-up work adds structured envelopes and extends HTTP coverage (e.g., 409 for conflicting sequence submissions).

## Testing Hooks

- Planned tests: verify concurrency guardrails for `AssetTagManager`, confirm prefix-specific sequence files, and exercise webhook endpoint with mocked RT responses (`pytest tests/integration/test_blueprint_prefixes.py` + future units).
- Manual smoke: `curl` the preview, confirm, and webhook endpoints against sandbox RT to ensure sequence increments as expected.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- Webhook configuration documented inline in `request_tracker_utils/__init__.py` and `specs/002-ensure-my-flask/research.md`.

## Future Work

- Relocate `AssetTagManager` to `utils/services` package with thread-safe locking semantics.
- Implement blueprint-level error handlers and structured logging once shared helpers exist (T026/T028).
- Add documentation covering multi-prefix deployments (TEST, PROD) and disaster recovery for corrupted sequence files.
