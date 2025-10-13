# Tasks: Flask Application Organization & Maintainability

**Input**: Design documents from `/specs/002-ensure-my-flask/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Only include test implementation where explicitly driven by User Story 3 (Testing & QA).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., Setup, Found, US1)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a shared baseline of evidence and tooling before story work begins.

- [x] T001 [Setup] Activate the development environment in the repo root (`/Users/jmartin/rtutils`) using `direnv allow` or `devenv shell` so Python 3.11, ruff, isort, black, and pytest are available for subsequent tasks.
- [x] T002 [Setup] Generate a baseline source tree snapshot by running `tree -L 3 request_tracker_utils` and save the output to `docs/architecture/_inputs/request_tracker_utils_tree.txt` (create the `_inputs/` directory if it does not exist).
- [x] T003 [Setup] Extract the current blueprint registrations from `request_tracker_utils/__init__.py` and document them in `docs/architecture/_inputs/blueprint_registry.md` for reference during blueprint standardization.
- [x] T004 [Setup] Catalogue all configuration variables from `request_tracker_utils/config.py`, capturing defaults and sensitivity notes in `docs/configuration/current_env_matrix.md` (create the directory as needed).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core documentation-first scaffolding and planning that blocks all user stories until complete.

- [x] T005 [Found] Copy `docs/_template_architecture.md` to create subsystem skeletons (`assets.md`, `devices.md`, `labels.md`, `students.md`, `tags.md`, `integrations.md`, `infrastructure.md`) under `docs/architecture/`.
- [x] T006 [Found] Author `docs/architecture/index.md` summarizing documentation ownership, evidence inputs, and the documentation-first workflow referenced in the feature plan.
- [x] T007 [Found] Expand the risk register and mitigation table in `specs/002-ensure-my-flask/plan.md` to cover documentation updates, blueprint prefix normalization, utility package moves, pytest scaffolding, and logging/error standardization.
- [x] T008 [Found] Flesh out the migration batch definitions (expected files, validation commands, rollback steps) in `specs/002-ensure-my-flask/quickstart.md#Phase 2 – Implementation Preparation`.
- [x] T009 [Found] Create `docs/deployment/nixos.md` detailing the flake modules, service definition touchpoints, and reiterating the standard `sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils` rollout requirement.

**Checkpoint**: Documentation scaffolding, risk planning, and deployment alignment are in place—user story work can now begin.

---

## Phase 3: User Story 1 - Developer Onboarding (Priority: P1) 🎯 MVP

**Goal**: Make it effortless for a new developer to understand the project structure and find feature code quickly.

**Independent Test**: A new developer can follow README links to architecture docs, confirm blueprint locations, and identify the correct module for "asset tag generation" within 5 minutes.

### Implementation for User Story 1

- [x] T010 [US1] Populate `docs/architecture/assets.md` with purpose, entry points, blueprint routes, dependent utilities, configuration, logging, and testing hooks for the asset creation flow.
- [x] T011 [P] [US1] Populate `docs/architecture/labels.md` with label printing responsibilities, template usage, and PDF generator/linking details.
- [x] T012 [P] [US1] Populate `docs/architecture/devices.md` describing device blueprint routes, CSV logger interactions, and Google Admin dependencies.
- [x] T013 [P] [US1] Populate `docs/architecture/students.md` covering student device tracking routes, student_check_tracker usage, and reconciliation flows.
- [x] T014 [P] [US1] Populate `docs/architecture/tags.md` outlining the tag sequence workflow, file-based asset tag cache, and collision safeguards.
- [x] T015 [P] [US1] Populate `docs/architecture/integrations.md` summarizing RT API and Google Admin client responsibilities, rate limiting, and retry posture.
- [x] T016 [P] [US1] Populate `docs/architecture/infrastructure.md` detailing db.py, configuration loading, logging destinations, and static asset organisation.
- [x] T017 [US1] Embed references to the snapshot files produced in Phase 1 within each subsystem doc (tree output, blueprint registry) to ground documentation in current state evidence.
- [x] T018 [US1] Add an "Architecture" section to `README.md` linking each subsystem doc, highlighting the documentation-first rule, and providing a quick checklist for locating route, template, and utility code.

**Checkpoint**: Documentation allows independent navigation of the codebase for onboarding.

---

## Phase 4: User Story 2 - Code Maintenance & Refactoring (Priority: P1)

**Goal**: Plan and execute refactors so that features remain isolated, blueprint prefixes are consistent, and utility modules have clear boundaries before touching production code.

**Independent Test**: Developers can modify the RT API integration logic without affecting label generation, asset tag management, or device check-in workflows.

### Implementation for User Story 2

- [ ] T019 [US2] Add a blueprint prefix audit table to `specs/002-ensure-my-flask/research.md`, mapping current prefixes from `request_tracker_utils/routes/*.py` to required prefixes.
- [ ] T020 [US2] Update the implementation roadmap in `specs/002-ensure-my-flask/plan.md` to include sequential tasks for normalizing blueprint prefixes and registering them in `request_tracker_utils/__init__.py`.
- [ ] T021 [US2] Extend the Utility Module entity in `specs/002-ensure-my-flask/data-model.md` with target subpackage attributes (`integrations/`, `services/`, `infrastructure/`) and dependency rules.
- [ ] T022 [US2] Create `specs/002-ensure-my-flask/contracts/error_handling_contract.md` defining standardized error and logging envelopes for routes and utilities.
- [ ] T023 [US2] Document planned logging and retry enhancements (modules affected, configuration knobs) within the Constitution Check follow-up notes in `specs/002-ensure-my-flask/plan.md`.
- [ ] T024 [US2] Normalize blueprint prefixes across `request_tracker_utils/routes/*.py` and `request_tracker_utils/__init__.py`, ensuring every blueprint registers with the documented prefix.
- [ ] T025 [US2] Add `tests/integration/test_blueprint_prefixes.py` that enumerates the Flask route map and asserts prefix compliance to prevent regressions.
- [ ] T026 [US2] Introduce shared error-response helpers in `request_tracker_utils/utils/error_responses.py` (or similar) and refactor each blueprint to return standardized JSON envelopes with correct status codes.
- [ ] T027 [US2] Retrofit `request_tracker_utils/utils/rt_api.py` and other external integrations with explicit try/catch, logging, and retry verification; document findings in `research.md`.
- [ ] T028 [US2] Implement structured logging configuration in `request_tracker_utils/logging.py`, update modules to use the canonical format, and add smoke coverage validating output formatting.
- [ ] T029 [US2] Add Flask client regression tests covering 400/500 pathways to confirm error envelopes and status codes match `error_handling_contract.md`.

**Checkpoint**: User Story 1 & 2 complete—code boundaries enforced and constitutional error-handling/logging guarantees satisfied.

---

## Phase 5: User Story 3 - Testing & Quality Assurance (Priority: P2)

**Goal**: Establish a pytest-based unit test harness that runs without external services, complementing existing smoke scripts.

**Independent Test**: Running `pytest tests/unit` executes mocked RT API tests without contacting live services, and integration tests live under `tests/integration/`.

### Tests & Implementation for User Story 3

- [ ] T030 [US3] Create `tests/unit/conftest.py` defining fixtures for temporary SQLite databases, fake RT API responses, and sample asset data.
- [ ] T031 [P] [US3] Implement `tests/unit/utils/test_rt_api.py` covering caching, retry, and error handling behavior with mocked HTTP sessions.
- [ ] T032 [P] [US3] Implement `tests/unit/utils/test_name_generator.py` ensuring deterministic adjective/animal pairing and CSV loading edge cases.
- [ ] T033 [US3] Move the existing root-level `test_integration.py` into `tests/integration/test_application.py`, updating imports and ensuring README/quickstart references the new location.
- [ ] T034 [US3] Author `docs/architecture/testing.md` outlining pytest directory structure, fixtures, and how shell-based smoke scripts complement automated coverage.
- [ ] T035 [US3] Add `.importlinter` configuration enforcing routes → services → integrations layer boundaries, capturing contracts for FR-002 and FR-009.
- [ ] T036 [US3] Update `scripts/quality/validate_structure.py` to run import-linter alongside `ruff`, `pydocstyle`, and pytest, failing when dependency contracts are violated.

**Checkpoint**: Unit and integration test scaffolding exists and enforces modular boundaries.

---

## Phase 6: User Story 4 - Configuration & Deployment (Priority: P2)

**Goal**: Ensure configuration can be applied per environment and deployment steps for NixOS are clearly documented.

**Independent Test**: Operators can provision a new environment using `.env.example`, follow README instructions, and deploy via the documented NixOS steps without reading code.

### Implementation for User Story 4

- [ ] T037 [US4] Create `.env.example` at the repository root documenting placeholders for required/optional variables with guidance on secrets management.
- [ ] T038 [US4] Expand `README.md#Configuration` with a table referencing `.env.example`, indicating defaults, sensitivity, and failure behavior.
- [ ] T039 [US4] Integrate the NixOS deployment procedure and module touchpoints from `docs/deployment/nixos.md` into `specs/002-ensure-my-flask/quickstart.md` validation matrix.
- [ ] T040 [US4] Add startup validation guidance to `request_tracker_utils/config.py` docstrings (without behavior change yet) so future implementation can fail fast on missing required env vars.
- [ ] T041 [US4] Audit repository for direct `sqlite3` usage, refactor outliers to `request_tracker_utils/utils/db.py`, and add tests guarding against future violations.

**Checkpoint**: Configuration guidance and database access patterns support environment setup and rollout.

---

## Phase 7: User Story 5 - Code Documentation & Standards (Priority: P3)

**Goal**: Define docstring, logging, and naming standards so developers understand module contracts without deep dives.

**Independent Test**: Developers can read standards docs to understand how to document public functions and format logs before implementation begins, and automated checks enforce the standards.

### Implementation for User Story 5

- [ ] T042 [US5] Create `docs/standards/docstrings.md` capturing the Google-style docstring convention with examples relevant to utilities and route handlers.
- [ ] T043 [P] [US5] Create `docs/standards/logging.md` recording the mandated log format (timestamp, level, module, message) and mapping modules that require updates.
- [ ] T044 [US5] Update `specs/002-ensure-my-flask/research.md` with a new "Documentation & Logging Standards" decision capturing rationale and alternatives.
- [ ] T045 [US5] Add a docstring coverage expectation table to `specs/002-ensure-my-flask/data-model.md`, mapping Blueprint and Utility Module entities to the 90% coverage success criterion.
- [ ] T046 [US5] Apply Google-style docstrings to exported functions in `request_tracker_utils/utils/*.py` and `request_tracker_utils/routes/*.py`, targeting ≥90% coverage validated by `pydocstyle --count`.
- [ ] T047 [US5] Add module-level docstrings and inline commentary for complex flows (e.g., tag sequence management) across routes and supporting utilities.
- [ ] T048 [US5] Author `docs/standards/style.md` documenting naming conventions and extend `scripts/quality/validate_structure.py` to run the corresponding lint checks (ruff rules, custom assertions).
- [ ] T049 [US5] Update `.github/copilot-instructions.md` and `CLAUDE.md` to reference the finalized docstring, logging, and naming standards.

**Checkpoint**: Standards are documented and enforced across the codebase.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Align documentation, quality logs, and communications after story work concludes.

- [ ] T050 [Polish] Reconcile links across `docs/architecture/index.md`, `README.md`, and `specs/002-ensure-my-flask/quickstart.md`, ensuring every subsystem doc, standard, and validation command is referenced.
- [ ] T051 [Polish] Update `specs/002-ensure-my-flask/quickstart.md` to include the new change sets, error-handling enforcement steps, and validation commands (`import-linter`, blueprint prefix tests, docstring coverage).
- [ ] T052 [P] [Polish] Run `ruff check .`, `pydocstyle request_tracker_utils`, `lint-imports`, `pytest`, and the blueprint-prefix regression tests, capturing outputs in `docs/quality/validation-log.md` to document baseline lint/test status.
- [ ] T053 [Polish] Draft release notes in `docs/releases/002-ensure-my-flask.md` summarizing documentation, testing, and deployment updates for IT/ops stakeholders.

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → Enables Foundational work.
- **Foundational (Phase 2)** → Blocks all user stories; complete before Phase 3+.
- **User Story Phases (3–7)** → Proceed in priority order (P1 → P1 → P2 → P2 → P3) once Foundational tasks finish; stories can run in parallel where marked [P] if coordination allows.
- **Polish (Phase 8)** → Runs after desired user stories finish.

### Story Dependency Graph

```
Setup → Foundational → US1 → US2 → US3 → US4 → US5 → Polish
										 └──────────────┬──────────────┘
																		└─ US3/US4/US5 can start once US1 & US2 deliver documentation scaffolding
```

## Parallel Execution Examples

- **User Story 1**: After T010, tasks T011–T016 touch different files and can proceed in parallel.
- **User Story 3**: T031 and T032 create independent test modules and can run concurrently once fixtures (T030) exist.
- **User Story 5**: T043 can run in parallel with T042 because they target different documentation files.
- **Polish**: T052 can run concurrently with T053 since they affect different directories.

## Implementation Strategy

### MVP First (Deliver User Story 1)

1. Complete Phases 1 & 2 to establish documentation scaffolding.
2. Execute Phase 3 tasks to publish subsystem docs and README navigation aids.
3. Validate onboarding flow using the independent test before tackling further stories.

### Incremental Delivery

1. After MVP, deliver Phase 4 (US2) to lock in refactor plans.
2. Proceed with Phase 5 (US3) to stand up test scaffolding.
3. Follow with Phase 6 (US4) for configuration/deployment clarity.
4. Wrap with Phase 7 (US5) to enshrine standards before implementing code changes.

### Parallel Team Strategy

- Once Foundational work is complete, assign:
  - Developer A → User Story 1 documentation updates (T010–T018)
  - Developer B → User Story 2 enforcement work (T019–T029)
  - Developer C → User Story 3 test scaffolding and contracts (T030–T036)
- After initial stories, redeploy collaborators onto US4/US5 (T037–T049) and Polish tasks (T050–T053), leveraging [P] markers to avoid conflicts.
