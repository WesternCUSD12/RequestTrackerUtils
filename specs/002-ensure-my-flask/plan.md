# Implementation Plan: Flask Application Organization & Maintainability

**Branch**: `002-ensure-my-flask` | **Date**: 2025-10-13 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/002-ensure-my-flask/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

- Reaffirm the documentation-first reorganization: create subsystem guides in `docs/architecture/`, tighten README onboarding, and publish contracts before touching code.
- Normalize Flask project boundaries by enforcing prefixed blueprints, dedicated utility modules, and Google-style docstrings so each feature stays isolated and testable.
- Enforce constitutional error-handling, logging, and retry standards across routes and utilities with shared helpers, structured logging, and verification.
- Keep NixOS deployment reproducible by updating the flake, service module, and runbooks in lockstep, emphasizing the standard `sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils` rollout path.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (per project standard)  
**Primary Dependencies**: Flask 2.2+, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+  
**Storage**: SQLite via `request_tracker_utils/utils/db.py`; cached files on disk for asset data  
**Testing**: pytest suite (to be expanded) plus existing fish-based smoke scripts for RT API  
**Target Platform**: NixOS host managed through `flake.nix` and a systemd service module  
**Project Type**: Single Flask web application with CLI/supporting scripts  
**Performance Goals**: Maintain current response characteristics; no new throughput targets defined in spec (flag for future measurement)  
**Constraints**: Documentation-first changes, zero downtime for existing endpoints, preserve environment variable contract, avoid circular imports  
**Scale/Scope**: Supports small district operations (team of 2-5 developers, RT + Google Admin integrations); reorganization limited to single service

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Integration-First Architecture**:

- [x] Feature integrates with existing RT/Google Workspace systems (reorganization preserves current integrations)
- [x] Provides both REST API endpoints and web interface (no interface removals planned)
- [x] Maintains cross-system data consistency (documentation-first audits reinforce RT↔Google workflows)

**Error Handling & Logging**:

- [ ] All external API calls include try/catch with descriptive errors _(Scheduled via tasks T020D–T020F to retrofit utilities and routes)_
- [ ] Sufficient logging for debugging without exposing sensitive data _(Tasks T020D & T020F deliver shared log formatting and usage audit)_
- [ ] Rate limiting and retry logic for external APIs _(T020E validates existing retry posture and documents gaps)_

**API Compatibility**:

- [x] Maintains backward compatibility for existing endpoints (no signature changes permitted)
- [x] New fields only, no removal/type changes to existing fields (reorg is non-breaking)
- [x] Follows semantic versioning for breaking changes (no major version bump required)

**Data Integrity**:

- [ ] Atomic operations with proper transaction handling _(T031A ensures DB helpers back all writes)_
- [ ] Database validation at API and schema levels _(Documented in architecture docs; additional checks captured in T024 & T031A)_
- [ ] Migration scripts with rollback procedures _(Out of scope; confirm N/A during audit)_

**Observability**:

- [ ] Clear success/failure feedback with actionable errors _(T020D introduces shared JSON envelopes and tests)_
- [ ] Audit logging with timestamps for all operations _(T020F verifies structured logging and CSV logger alignment)_
- [ ] Administrative status reporting _(Document existing dashboards or flag as gap during documentation tasks)_

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```
request_tracker_utils/
├── __init__.py                # Flask app factory + blueprint registration
├── config.py                  # Environment variable contract
├── routes/                    # Feature-focused blueprints (assets, devices, labels, students, tags)
├── utils/                     # RT API, Google Admin, DB, PDF, CSV logging helpers
├── templates/                 # Jinja2 templates extending base.html
├── static/
│   └── js/asset_batch.js      # Client-side helpers (expandable to css/, images/)
└── __pycache__/               # Ignored runtime artifacts (to be cleaned in docs)

scripts/                       # Operational and data maintenance scripts (Python + fish)
docs/                          # Architecture + integration guides (new subsystem docs will land here)
tests/                         # Target home for pytest suites (currently sparse; to be expanded)
test_integration.py            # Legacy root-level integration test (migration target)
run.py                         # Entry point for Flask server (will reference create_app)
```

**Structure Decision**: Treat `request_tracker_utils/` as the single Flask project root with blueprints/utilities under it, document supporting scripts in `scripts/`, and centralize automated tests under `tests/` while migrating stragglers like `test_integration.py` during implementation.

Planned change sets include: (1) blueprint prefix normalization and shared error-handling helpers (tasks T020A–T020F), (2) unit-test and import-linter enforcement for utilities (tasks T024–T025B), and (3) docstring retrofits plus naming/logging standards (tasks T033–T036, T034A–T034D).

## Risk Register & Mitigations

| Risk Category                   | Description                                                                                    | Impact                                           | Mitigation / Evidence                                                                                                             | Owner         | Linked Tasks                 |
| ------------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ------------- | ---------------------------- |
| Documentation Drift             | Subsystem guides and README fall out of sync with code changes.                                | High – onboarding slows; reviewers lack context. | Enforce documentation-first workflow, require references in PR checklist, capture evidence snapshots in `_inputs/`.               | Dev Lead      | T005, T006, T017, T018       |
| Blueprint Prefix Normalization  | Updating prefixes introduces broken routes or collisions.                                      | Medium – runtime 404s/500s.                      | Audit current registrations (`blueprint_registry.md`), add regression tests, perform staged rollout with app factory smoke tests. | Feature Team  | T019, T020, T024, T025       |
| Utility Package Moves           | Relocating modules breaks imports across scripts and blueprints.                               | High – runtime import errors.                    | Introduce shim imports during transition, run `ruff --select=I` and `import-linter`, update scripts/README concurrently.          | Feature Team  | T021, T024, T035, T036       |
| Pytest Scaffolding              | New unit tests depend on incomplete fixtures or external services.                             | Medium – flaky CI, slow adoption.                | Build isolated fixtures (`tests/unit/conftest.py`), mock external calls, document patterns in `docs/architecture/testing.md`.     | QA Lead       | T030, T031, T032, T034       |
| Logging & Error Standardization | Rolling out shared logging and error envelopes exposes sensitive data or misses critical logs. | Medium – compliance gaps, debugging difficulty.  | Implement helper module with redaction, run structured logging smoke test, document formats in contracts and standards docs.      | Platform Team | T022, T026, T028, T029, T043 |

> Review cadence: Reassess risks at the start of each phase; append new rows when additional hazards are discovered.

## Implementation Roadmap: Blueprint Prefix Normalization

### Sequential Steps

1. Audit current blueprint registrations and prefixes (see research.md, blueprint_registry.md)
2. Update `request_tracker_utils/__init__.py` to register all blueprints with explicit, non-overlapping prefixes:

- `/labels` for label_routes
- `/tags` for tag_routes
- `/devices` for device_routes
- `/students` for student_routes
- `/assets` for asset_routes

3. Refactor each blueprint module to ensure all route decorators are compatible with the new prefix (update links, redirects, and API docs as needed)
4. Add regression tests in `tests/integration/test_blueprint_prefixes.py` to assert prefix compliance and prevent future collisions
5. Update subsystem docs and README to reflect new route map
6. Stage rollout: deploy to test environment, verify all endpoints, then merge to production

### Dependency Notes

- All prefix changes must be coordinated in a single commit to avoid partial breakage
- Update any scripts, templates, or static assets referencing old route paths
- Document migration steps and validation commands in quickstart.md

## Complexity Tracking

_Fill ONLY if Constitution Check has violations that must be justified_

| Violation                  | Why Needed         | Simpler Alternative Rejected Because |
| -------------------------- | ------------------ | ------------------------------------ |
| [e.g., 4th project]        | [current need]     | [why 3 projects insufficient]        |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient]  |

## Constitution Check Follow-up: Logging & Retry Enhancements

### Modules Affected

- `request_tracker_utils/utils/rt_api.py` (RT API client)
- `request_tracker_utils/utils/google_admin.py` (Google Admin client)
- All route blueprints in `routes/`
- `csv_logger.py` (audit logging)

### Planned Enhancements

- Implement shared logging configuration in `logging.py` with structured format (timestamp, level, module, message, context)
- Refactor all modules to use canonical logger and avoid print statements
- Add retry logic to all external API calls (RT, Google Admin) using requests.Session + urllib3 Retry
- Document retry/backoff settings in subsystem guides and contracts
- Ensure all error responses use standardized JSON envelope (see error_handling_contract.md)
- Add smoke tests to validate logging output and retry behavior

### Configuration Knobs

- `LOG_LEVEL` environment variable to control verbosity
- `RETRY_COUNT`, `RETRY_BACKOFF` for API clients

### Validation

- Regression tests in `tests/integration/test_blueprint_prefixes.py` and new logging/retry test modules
- Manual review of log output for format and completeness
