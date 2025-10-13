# Subsystem: Assets

## Purpose

Provides the batch asset creation workflow, including serial-number validation, automatic asset-tag assignment, and downstream label generation links. The blueprint exposes both HTML forms for operators and JSON APIs that coordinate with Request Tracker (RT) to persist new asset records.

## Entry Points

- Routes (from `request_tracker_utils/routes/asset_routes.py`):
  - `GET /assets/form` → renders batch creation UI.
  - `GET /assets/preview-internal-name` → previews generated adjective–animal names.
  - `GET /assets/catalogs` and `GET /assets/catalog-options` → hydrate dropdown metadata with caching.
  - `POST /assets/clear-cache` → manual cache flush.
  - `GET /assets/preview-next-tag` → exposes upcoming tag without incrementing sequence.
  - `GET /assets/validate-serial` → server-side uniqueness check.
  - `POST /assets/create` → main asset creation endpoint.
- Templates: `templates/asset_create.html` (primary UI), with follow-on links to `/labels/print` for generated assets.
- CLI/Jobs: none today; future automation should consume the JSON APIs to avoid duplicating business logic.

## Dependencies

- Utility Modules:
  - `utils.rt_api` (functions `rt_api_request`, `sanitize_json`) for RT REST interactions.
  - `utils.name_generator.InternalNameGenerator` for adjective–animal slug creation.
  - `routes.tag_routes.AssetTagManager` for sequence management and confirmation logging.
- External Services:
  - Request Tracker REST API (`RT_URL`/`API_ENDPOINT`), leveraged for asset CRUD and catalog metadata.

## Configuration

- Environment Variables:
  - `RT_URL`, `API_ENDPOINT`, `RT_TOKEN` → required for RT access (see `docs/configuration/current_env_matrix.md`).
  - `WORKING_DIR`, `PREFIX`, `LABEL_WIDTH_MM`, `LABEL_HEIGHT_MM`, `PADDING` → influence asset-tag sequences, cached files, and downstream label formatting.
- Files/Secrets:
  - `instance/asset_tag_sequence*.txt` and `asset_tag_confirmations.log` live under `WORKING_DIR` and must be writable by the Flask service user.

## Logging & Error Handling

- Uses `current_app.logger` to capture cache hits/misses, RT API call outcomes, and validation failures. Logs should migrate to structured helpers during User Story 2 (tasks T026/T028).
- Error responses follow JSON envelopes with `success`/`error` keys; align with `contracts/error_handling_contract.md` when shared helpers land.
- Exceptions from RT calls are caught and translated into retryable (`retry: True`) responses when feasible.

## Testing Hooks

- Planned pytest coverage (`tests/unit/utils/test_rt_api.py`, integration suite for blueprint prefixes) should mock RT API via fixtures in `tests/unit/conftest.py` once User Story 3 completes.
- Manual smoke: invoke `POST /assets/create` against RT sandbox and confirm labels render and sequences increment.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- RT API interaction details: `specs/002-ensure-my-flask/research.md` (Utility Module analysis), `contracts/rt-utils-openapi.yaml`.

## Future Work

- Move `AssetTagManager` into a dedicated services package (`utils/services/tag_manager.py`) ahead of utility reorganization.
- Add blueprint-level error handlers once shared JSON envelope helpers are available (T026).
- Document sample RT payloads and typical failure states in this guide after User Story 2 hardening work.
