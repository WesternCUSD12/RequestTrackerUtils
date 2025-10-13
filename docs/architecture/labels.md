# Subsystem: Labels

## Purpose

Responsible for generating printable asset labels (single or batch) that embed QR codes, barcodes, and asset metadata fetched from RT. Also provides administrative tooling to synchronize RT label fields across large batches.

## Entry Points

- Routes (see `request_tracker_utils/routes/label_routes.py`):
  - `GET /labels/` → main label form (`label_form.html`).
  - `GET /labels/print` → render HTML label for a single asset (`label.html`).
  - `POST /labels/batch` → generate batch labels (`batch_labels.html`).
  - `POST /labels/update-all` → mass-update RT label custom field.
  - `POST /labels/assets` → query RT assets using JSON filters.
  - `GET /labels/debug` → troubleshooting endpoint (returns JSON context).
  - Additional helpers: `/labels/batch/form`, `/labels/assets/download`, etc., for CSV exports and label previews.
- Templates: `label_form.html`, `label.html`, `batch_labels_form.html`, `batch_labels.html`, `csv_preview.html`, `label.html` (print-ready), `custom_fields_debug.html`.
- CLI/Jobs: none—interactions occur through the UI or via API scripts calling the JSON endpoints.

## Dependencies

- Utility Modules:
  - `utils.rt_api` (`fetch_asset_data`, `search_assets`, `update_asset_custom_field`, `find_asset_by_name`).
  - `utils.pdf_generator` (used for PDF emission when invoked via scripts).
  - `utils.csv_logger` for audit entries when bulk updates run.
- External Libraries: `qrcode`, `python-barcode`, Pillow (`PIL`) for image generation.

## Configuration

- Environment Variables:
  - `RT_URL`, `API_ENDPOINT`, `RT_TOKEN` to reach RT.
  - `LABEL_WIDTH_MM`, `LABEL_HEIGHT_MM`, `PADDING` control layout defaults referenced in templates.
- Files/Secrets: None beyond RT credentials; QR/barcode generation happens in-memory.

## Logging & Error Handling

- Logs asset lookups, QR/barcode generation failures, and RT update responses with `current_app.logger`.
- Existing error responses return JSON with `error` keys; align with `error_handling_contract.md` during standardization to ensure consistent HTTP status codes and redacted messages.
- When QR/barcode generation fails, module writes stack traces and falls back to placeholder images.

## Testing Hooks

- Future pytest targets: parameterized tests for `generate_qr_code`, `generate_barcode`, and integration coverage for `/labels/print` using Flask test client (tasks T031/T032/T029).
- Manual smoke: `GET /labels/print?assetId=<id>` and `POST /labels/batch` using sandbox asset IDs; inspect rendered HTML and assets in RT.

## Evidence

- [`docs/architecture/_inputs/request_tracker_utils_tree.txt`](./_inputs/request_tracker_utils_tree.txt)
- [`docs/architecture/_inputs/blueprint_registry.md`](./_inputs/blueprint_registry.md)
- RT payload expectations captured in `specs/002-ensure-my-flask/contracts/rt-utils-openapi.yaml`.

## Future Work

- Introduce shared error-envelope helpers across label endpoints (T026).
- Add PDF export documentation referencing `utils/pdf_generator` once migration to services package is complete.
- Document best-practice label printer settings and troubleshooting tips after QA sign-off.
