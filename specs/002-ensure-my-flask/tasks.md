# Tasks: Flask Application Organization & Maintainability

**Input**: Design documents from `/specs/002-ensure-my-flask/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included only where the specification calls for mockable utilities (User Story 3).

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish documentation scaffolding that every story relies on.

- [ ] T001 [Core] Create architecture documentation skeleton by adding the "Architecture" section stub in `README.md`, creating `docs/architecture/README.md`, and seeding `docs/architecture/module_dependencies.md` with headings.
- [ ] T002 [P] [Core] Create `docs/development_guide.md` with sections for blueprints, utilities, configuration, testing, and references to contracts in `specs/002-ensure-my-flask/contracts/`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Quality enforcement and tooling that must exist before modifying application modules.

- [ ] T003 [Core] Add organization quality tooling by updating `pyproject.toml` with `isort`, `pydocstyle`, and pytest configuration, and introducing `.importlinter` in the repo root to enforce the module dependency contracts.
- [ ] T004 [P] [Core] Add `scripts/quality/validate_structure.py` that runs `isort`, `ruff`, `pydocstyle`, and `lint-imports`, and document its usage comment header.
- [ ] T005 [Core] Update `docs/development_guide.md` (Testing & Quality section) with instructions for running `scripts/quality/validate_structure.py` and interpreting failures before proceeding to feature work.

**Checkpoint**: Foundation ready—developers can run shared quality checks.

---

## Phase 3: User Story 1 - Developer Onboarding (Priority: P1) 🎯 MVP

**Goal**: New developers can navigate the codebase and locate feature code quickly.

**Independent Test**: A developer can find the asset tag generation code in under five minutes using the documentation.

### Implementation

- [ ] T006 [US1] Expand the new "Architecture" section in `README.md` with tables describing routes, utilities, templates, and scripts, linking to deeper docs and highlighting asset tag generation entry points.
- [ ] T007 [P] [US1] Create `docs/architecture/blueprints.md` summarizing each blueprint's URL prefix, primary responsibilities, and key route handlers.
- [ ] T008 [US1] Populate `docs/architecture/module_dependencies.md` with the current import graph, calling out allowed directions and identifying any existing violations to address later.
- [ ] T009 [P] [US1] Add `docs/architecture/routes_to_templates.md` mapping each route handler to its corresponding templates and static assets for quick discovery.
- [ ] T010 [US1] Add an onboarding checklist to `docs/development_guide.md` that walks a new developer from cloning the repo through locating the asset tag workflow.

**Checkpoint**: User Story 1 documentation complete and independently reviewable.

---

## Phase 4: User Story 2 - Code Maintenance & Refactoring (Priority: P1)

**Goal**: Developers can change feature-specific code without touching unrelated modules or introducing cycles.

**Independent Test**: Modifying `utils/rt_api.py` does not require touching label generation or check-in routes.

### Implementation

- [ ] T011 [US2] Update `request_tracker_utils/__init__.py` so every blueprint registers with an explicit URL prefix and call a `configure_logging()` helper stub to prepare for consistent logging.
- [ ] T012 [US2] Implement `request_tracker_utils/logging.py` with `configure_logging(app)` mirroring `contracts/logging_contract.md`, wire it into `create_app()`, and document the logging pattern.
- [ ] T013 [US2] Refactor shared route helpers into `request_tracker_utils/utils/blueprint_helpers.py` (or similar) and update `request_tracker_utils/routes/*.py` to remove cross-blueprint imports while preserving functionality.
- [ ] T014 [US2] Add `__all__` declarations to exported utility modules (`request_tracker_utils/utils/*.py`) and align imports in the routes to respect those public APIs.
- [ ] T015 [US2] Audit database access in `request_tracker_utils/routes/` and `request_tracker_utils/utils/` to ensure all read/write operations go through helpers in `request_tracker_utils/utils/db.py`; add a regression check that fails on new direct `sqlite3` usage.
- [ ] T016 [US2] Run and commit import order normalization across `request_tracker_utils/` using the configured `isort` profile to enforce stdlib → third-party → local grouping.
- [ ] T017 [US2] Add 404/500 blueprint-level error handlers to each file in `request_tracker_utils/routes/` following `contracts/error_handling_contract.md` and ensure they emit structured logs.
- [ ] T018 [US2] Review all request handlers in `request_tracker_utils/routes/*.py` to guarantee 400/500 responses return JSON payloads per `contracts/error_handling_contract.md`, adding targeted Flask client tests where gaps exist.

**Checkpoint**: User Story 1 & 2 complete—code boundaries enforced for focused refactors.

---

## Phase 5: User Story 3 - Testing & Quality Assurance (Priority: P2)

**Goal**: Utilities and integrations can be tested without running the Flask app or calling external services.

**Independent Test**: `pytest tests/unit/utils/test_rt_api.py` runs with all external calls mocked.

### Tests (Required for this story)

- [ ] T019 [US3] Add `tests/unit/utils/test_rt_api.py` with mocked `requests` sessions covering fetch/update flows without network access.
- [ ] T020 [P] [US3] Add `tests/unit/utils/test_db.py` validating connection helpers using a temporary SQLite database under the test fixture directory.
- [ ] T021 [US3] Create `tests/conftest.py` providing fixtures for environment variables, temporary working directories, and a shared `requests_mock` adapter.

### Implementation

- [ ] T022 [P] [US3] Configure pytest settings in `pyproject.toml` (or `pytest.ini`) to collect the new test tree and enable the mock fixtures.
- [ ] T023 [US3] Extend the Testing section of `docs/development_guide.md` with instructions to run targeted unit suites and guidance on mocking RT/Google APIs.

**Checkpoint**: User Stories 1–3 independently testable.

---

## Phase 6: User Story 4 - Configuration & Deployment (Priority: P2)

**Goal**: Deployments rely solely on environment configuration with fail-fast safety.

**Independent Test**: App aborts startup with a clear error when `RT_TOKEN` is missing, and deployments use `.env` templates.

### Implementation

- [ ] T024 [US4] Refactor `request_tracker_utils/config.py` to introduce a `require_env()` helper that raises descriptive errors when required variables (e.g., `RT_TOKEN`) are absent and apply it to all mandatory settings.
- [ ] T025 [P] [US4] Add `.env.example` at the repo root covering all documented variables with safe placeholders and comments for optional values.
- [ ] T026 [US4] Update the Configuration section of `README.md` to include required/optional tables aligned with `.env.example` and describe secrets handling.
- [ ] T027 [P] [US4] Create `docs/deployment/configuration.md` detailing environment setup for development, staging, and production (systemd/Nix examples) and referencing `.env.example`.
- [ ] T028 [US4] Update deployment scripts in `scripts/` (e.g., `scheduled_rt_user_sync.py`, `sync_chromebook_data.py`) to load configuration through the new helper and fail fast when prerequisites are missing.
- [ ] T029 [US4] Introduce `scripts/context_helpers.py` exposing `get_app_context()`, refactor scripts needing Flask context to use it, and document the pattern in `docs/deployment/configuration.md` and `docs/development_guide.md`.

**Checkpoint**: User Stories 1–4 complete with environment-ready deployments.

---

## Phase 7: User Story 5 - Code Documentation & Standards (Priority: P3)

**Goal**: Public functions and modules communicate intent clearly through docstrings and inline documentation.

**Independent Test**: Reading docstrings for `AssetTagManager` (or equivalent utility) reveals how to use it without diving into implementation details.

### Implementation

- [ ] T030 [US5] Add module-level docstrings to each file in `request_tracker_utils/routes/` describing blueprint scope, key routes, and dependencies.
- [ ] T031 [P] [US5] Add Google-style docstrings to exported functions in `request_tracker_utils/utils/rt_api.py`, ensuring Args/Returns/Raises sections match contract expectations.
- [ ] T032 [P] [US5] Document public APIs in `request_tracker_utils/utils/db.py`, `google_admin.py`, `pdf_generator.py`, `csv_logger.py`, `student_check_tracker.py`, and `name_generator.py` with Google-style docstrings.
- [ ] T033 [US5] Add inline commentary for complex flows (asset tag sequence, cache management) in `request_tracker_utils/routes/tag_routes.py` and related utilities to explain non-obvious decisions.
- [ ] T034 [US5] Audit `static/` and `templates/` to ensure assets are organized by type, templates extend `base.html`, and naming conventions match FR-012–FR-014; update files and `docs/development_guide.md` with the validated standards.
- [ ] T035 [US5] Update `.github/copilot-instructions.md` and `CLAUDE.md` to reflect mandatory docstring, logging, and error handling standards and reference the relevant contracts.

**Checkpoint**: All five user stories complete with documented standards.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Finalize automation, documentation, and validation across stories.

- [ ] T036 [Core] Add `.pre-commit-config.yaml` wiring `isort`, `ruff`, `pydocstyle`, and `lint-imports`, and document installation steps in `docs/development_guide.md`.
- [ ] T037 [P] [Core] Update `specs/002-ensure-my-flask/quickstart.md` to reflect the executed phases, including new tooling and documentation checkpoints.
- [ ] T038 [Core] Run `scripts/quality/validate_structure.py` and `pytest` locally, capturing the output in `docs/development_guide.md` (Validation section) as proof of compliance.

---

## Dependencies & Execution Order

1. **Setup (Phase 1)** → 2. **Foundational (Phase 2)** → 3. **User Story 1 (Phase 3)** → 4. **User Story 2 (Phase 4)** → 5. **User Story 3 (Phase 5)** → 6. **User Story 4 (Phase 6)** → 7. **User Story 5 (Phase 7)** → 8. **Polish (Phase 8)**

- User Story phases must follow priority order (P1 → P1 → P2 → P2 → P3). Later stories assume prior documentation, utilities, and configuration work is complete.
- Within each phase, respect file-level sequencing: tasks touching the same file (e.g., `README.md`, `docs/development_guide.md`, `request_tracker_utils/config.py`) must proceed sequentially.
- After the Foundational checkpoint, stories may proceed in parallel **only** when their tasks operate on distinct files.

## Parallel Execution Examples

- **User Story 1**: T007 and T009 can run concurrently while T006/T008/T010 proceed sequentially.
- **User Story 2**: T013 and T014 depend on each other, but T016 (bulk import normalization) can run once they land; avoid parallelism on the same files.
- **User Story 3**: T020 and T021 can be developed in parallel while T019 anchors the primary test module.
- **User Story 4**: T025 and T027 can run concurrently as they touch separate files (`.env.example` vs. `docs/deployment/configuration.md`).
- **User Story 5**: T031 and T032 can run in parallel since they target different utility files.

## Implementation Strategy

1. Deliver the MVP by completing Phases 1–3, enabling immediate onboarding improvements.
2. Extend maintainability by finishing Phase 4, stabilizing module boundaries and error handling.
3. Achieve full testability and deployment safety with Phases 5 and 6, enabling confident releases.
4. Conclude with Phase 7 to enforce documentation standards, then Phase 8 for automation and validation.
5. Stop after any checkpoint if interim delivery is needed; each story is independently demonstrable.
