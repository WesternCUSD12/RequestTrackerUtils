# Tasks: Streamlined Asset Creation with Batch Entry

**Feature**: 001-i-need-to  
**Input**: Design documents from `/specs/001-i-need-to/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not explicitly requested in feature specification - tests are OPTIONAL and not included in this task breakdown.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Per plan.md project structure:

- Flask routes: `request_tracker_utils/routes/`
- Templates: `request_tracker_utils/templates/`
- JavaScript: `request_tracker_utils/static/js/`
- Utils: `request_tracker_utils/utils/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for batch asset creation feature

- [x] T001 [P] Create asset_routes blueprint file `request_tracker_utils/routes/asset_routes.py` with Flask blueprint initialization
- [x] T002 [P] Create asset creation template `request_tracker_utils/templates/asset_create.html` extending base.html
- [x] T003 [P] Create JavaScript module `request_tracker_utils/static/js/asset_batch.js` for form state management
- [x] T004 Register asset_routes blueprint in `request_tracker_utils/__init__.py` create_app() function

**Checkpoint**: ✅ File structure ready - foundational utilities can now be implemented

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Enhance AssetTagManager in `request_tracker_utils/routes/tag_routes.py` to support dynamic digit expansion (W12-9999 → W12-10000)
- [x] T006 [P] Implement serial number uniqueness validation function in `request_tracker_utils/routes/asset_routes.py` using RT API search
- [x] T007 [P] Implement asset tag preview endpoint GET /assets/preview-next-tag in `request_tracker_utils/routes/asset_routes.py`
- [x] T008 Configure sessionStorage constants and helper functions in `request_tracker_utils/static/js/asset_batch.js` (STORAGE_KEY, PERSISTED_FIELDS, CLEARED_FIELDS)

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Rapid Batch Asset Entry (Priority: P1) 🎯 MVP

**Goal**: IT staff can quickly register multiple identical devices by persisting common fields and only changing unique identifiers (serial number, internal name). Auto-increment asset tags and create assets in RT.

**Independent Test**: Create 3 identical assets with different serial numbers (e.g., Dell Chromebook 3100 with serials ABC001, ABC002, ABC003) and verify:

1. Common fields (manufacturer, model, funding source, category) persist across entries
2. Serial number and internal name fields clear after each creation
3. Asset tags increment sequentially (e.g., W12-1001, W12-1002, W12-1003)
4. All 3 assets created successfully in RT
5. 10 assets can be created in under 5 minutes (SC-001)

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement POST /assets/create endpoint in `request_tracker_utils/routes/asset_routes.py` with request validation
- [x] T010 [P] [US1] Implement GET /assets/validate-serial endpoint in `request_tracker_utils/routes/asset_routes.py` for real-time serial uniqueness checking
- [x] T011 [US1] Implement asset creation logic in POST /assets/create: validate serial uniqueness, get next asset tag, create asset in RT via rt_api_request, increment sequence, log confirmation
- [x] T012 [US1] Add error handling in POST /assets/create for RT API failures (400 for validation errors, 500 for server errors with retry flag)
- [x] T013 [US1] Implement form HTML structure in `request_tracker_utils/templates/asset_create.html` with persisted fields (manufacturer, model, category, funding_source) and editable unique fields (serial_number, internal_name) per FR-002
- [x] T014 [US1] Add form validation and submission handler in `request_tracker_utils/static/js/asset_batch.js` (handleSubmit function)
- [x] T015 [US1] Implement sessionStorage persistence logic in `request_tracker_utils/static/js/asset_batch.js` (saveFormState, loadFormState functions)
- [x] T016 [US1] Implement unique field clearing logic in `request_tracker_utils/static/js/asset_batch.js` (clearUniqueFields function) to reset serial_number and internal_name after each creation per FR-002
- [x] T017 [US1] Add next asset tag preview display in `request_tracker_utils/templates/asset_create.html` (right sidebar card) and loadNextTag function in JavaScript
- [x] T018 [US1] Add success/error alert display in `request_tracker_utils/templates/asset_create.html` with showSuccess and showError functions in JavaScript
- [x] T019 [US1] Add audit logging for asset creation operations in POST /assets/create endpoint with timestamps, asset tags, user info per FR-010

**Checkpoint**: ✅ User Story 1 COMPLETE - Fully functional and testable independently. Staff can create multiple assets with persisted common fields, auto-incrementing tags, and RT integration.

---

## Phase 4: User Story 2 - Asset Label Auto-Generation (Priority: P2)

**Goal**: After creating each asset, staff get an immediate physical label to attach to the device without navigating to a separate labeling workflow. Browser print dialog automatically triggered.

**Independent Test**: Create a single asset and verify:

1. Asset created successfully in RT
2. Browser print dialog opens automatically
3. Label preview shows QR code, asset tag, serial number, model, manufacturer
4. Label is print-ready (correct dimensions, readable text)
5. 95% of operations generate labels within 2 seconds (SC-003)

### Implementation for User Story 2

- [ ] T020 [US2] Implement automatic label printing trigger in `request_tracker_utils/static/js/asset_batch.js` (printLabel function) that fetches from existing GET /labels/print endpoint
- [ ] T021 [US2] Implement hidden iframe creation and print dialog trigger in printLabel function using window.print()
- [ ] T022 [US2] Add label printing call to handleSubmit success path in `request_tracker_utils/static/js/asset_batch.js` after asset creation succeeds (verify FR-004: printLabel called only after successful RT creation response)
- [ ] T023 [US2] Add label printing success/failure tracking to success response display in showSuccess function
- [ ] T024 [US2] Verify existing GET /labels/print endpoint in `request_tracker_utils/routes/label_routes.py` returns print-optimized HTML with QR code and barcode

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Assets are created AND labels automatically print.

---

## Phase 5: User Story 3 - Form State Management (Priority: P3)

**Goal**: Staff can modify which fields persist, clear the form to start a new asset type, and recover from errors without losing data.

**Independent Test**:

1. Create 3 assets of one type (e.g., Dell Chromebook 3100)
2. Click "Clear All" button - verify all fields empty and sessionStorage cleared
3. Create 2 assets of different type (e.g., HP Laptop 450)
4. Verify new persisted values override old ones
5. Trigger a validation error (duplicate serial) - verify all form data retained for correction

### Implementation for User Story 3

- [ ] T025 [P] [US3] Implement POST /assets/batch/clear-form endpoint in `request_tracker_utils/routes/asset_routes.py` (returns success confirmation)
- [ ] T026 [P] [US3] Add "Clear All" button to form in `request_tracker_utils/templates/asset_create.html`
- [ ] T027 [US3] Implement clearAll function in `request_tracker_utils/static/js/asset_batch.js` that clears sessionStorage, resets form fields, and hides alerts
- [ ] T028 [US3] Wire "Clear All" button click event to clearAll function in asset_batch.js
- [ ] T029 [US3] Add form data persistence on error in handleSubmit error path (form values retained, no clearing of unique fields)
- [ ] T030 [US3] Add visual feedback for "Clear All" action (confirmation message or brief success alert)
- [ ] T031 [US3] Add "Tips" card to sidebar in `request_tracker_utils/templates/asset_create.html` explaining form persistence behavior

**Checkpoint**: All user stories should now be independently functional. Complete form management with persistence, clearing, and error recovery.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final integration verification

- [ ] T032 [P] Add keyboard navigation optimization: Tab key flow through form fields, Enter key to submit
- [ ] T033 [P] Add loading indicators during async operations (asset creation, serial validation, tag preview)
- [ ] T034 [P] Add Bootstrap styling and icons to form elements in `request_tracker_utils/templates/asset_create.html`
- [ ] T035 [P] Add label generation retry button display logic in `request_tracker_utils/static/js/asset_batch.js` (showLabelError function with "Retry Print" button)
- [ ] T036 Implement graceful label failure handling per FR-011: show success with asset tag + "Retry Print" button when label generation fails
- [ ] T037 [P] Add client-side input validation (serial number format, required fields) before submission
- [ ] T038 [P] Add responsive design styling for smaller screens in asset_create.html
- [ ] T039 Verify asset tag sequence handles overflow correctly (W12-9999 → W12-10000) per FR-003 via AssetTagManager enhancement
- [ ] T040 [P] Update quickstart.md with any implementation deviations or additional setup instructions
- [ ] T041 Run complete quickstart.md validation: test all steps, verify MVP functionality, confirm success criteria SC-001 through SC-005, and verify FR-004 (asset created in RT before label generation in all code paths)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 (calls printLabel after asset creation) but US1 can work without US2
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 form behavior but US1 can work without US3

### Within Each User Story

**User Story 1**:

- T009 (create endpoint) and T010 (validate endpoint) can run in parallel [P]
- T011 (creation logic) depends on T009, T006 (validation function)
- T012 (error handling) depends on T011
- T013 (form HTML) can run in parallel with backend tasks [P]
- T014-T019 depend on T013 (form must exist) but can follow in sequence

**User Story 2**:

- T020-T024 are sequential, each builds on previous
- T024 is verification only, can run in parallel with other tasks [P]

**User Story 3**:

- T025 (endpoint) and T026 (button HTML) can run in parallel [P]
- T027-T031 are sequential, implementing clearAll flow

### Parallel Opportunities

- **Phase 1**: All setup tasks T001-T003 can run in parallel (different files), then T004 integrates
- **Phase 2**: T005-T007 can all run in parallel (different concerns, different files)
- **User Stories**: Once Phase 2 completes, US1, US2, US3 can start in parallel if team capacity allows
- **Phase 6**: T032-T034, T037-T038, T040 can all run in parallel (different files/concerns)

---

## Parallel Example: User Story 1

```bash
# Launch foundational backend work together:
Task T009: "Implement POST /assets/create endpoint validation"
Task T010: "Implement GET /assets/validate-serial endpoint"

# Meanwhile, launch frontend work in parallel:
Task T013: "Implement form HTML structure in asset_create.html"

# After backend endpoints ready, implement business logic:
Task T011: "Implement asset creation logic in POST /assets/create"

# After form HTML ready, implement JavaScript features:
Task T014: "Add form validation and submission handler"
Task T015: "Implement sessionStorage persistence logic"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T009-T019)
4. **STOP and VALIDATE**: Test User Story 1 independently with 3 identical assets
   - Verify common fields persist
   - Verify serial numbers clear after each
   - Verify asset tags increment correctly
   - Verify assets created in RT successfully
   - Measure: Can 10 assets be created in under 5 minutes? (SC-001)
5. Deploy/demo if ready - core value delivered!

### Incremental Delivery

1. **Setup + Foundational** → Foundation ready (T001-T008)
2. **Add User Story 1** → Test independently → Deploy/Demo (MVP! Core batch entry works)
3. **Add User Story 2** → Test independently → Deploy/Demo (Auto-printing added)
4. **Add User Story 3** → Test independently → Deploy/Demo (Enhanced form management)
5. **Add Polish** → Final integration testing → Production release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (T001-T008)
2. **Once Foundational is done**, split work:
   - **Developer A**: User Story 1 (T009-T019) - Core batch entry
   - **Developer B**: User Story 2 (T020-T024) - Auto-printing (waits for US1 basic structure)
   - **Developer C**: User Story 3 (T025-T031) - Form management (waits for US1 basic structure)
3. Stories complete and integrate independently
4. **All team**: Polish phase together (T032-T041)

---

## Task Summary

**Total Tasks**: 41 tasks across 6 phases

**Task Breakdown by Phase**:

- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (US1 - Rapid Batch Entry): 11 tasks 🎯 MVP
- Phase 4 (US2 - Auto-Label Printing): 5 tasks
- Phase 5 (US3 - Form Management): 7 tasks
- Phase 6 (Polish): 10 tasks

**Parallel Opportunities**: 15 tasks marked [P] can run in parallel with other tasks in same phase

**Independent Test Criteria**:

- **US1**: Create 3 identical assets with different serials, verify persistence & auto-increment
- **US2**: Create 1 asset, verify print dialog auto-opens with correct label content
- **US3**: Create assets, click Clear All, create different assets, trigger error and recover

**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 19 tasks

- Delivers core value: Rapid batch asset entry with persistence and auto-increment
- Can be validated independently
- Approximately 2-3 days for single developer, 1-2 days for small team

**Full Feature Scope**: All 41 tasks

- Delivers complete feature with auto-printing and enhanced form management
- Approximately 4-6 days for single developer, 2-3 days for small team

---

## Success Criteria Validation

After completing all tasks, validate against spec.md success criteria:

- [ ] **SC-001**: IT staff can create 10 identical assets (different serial numbers only) in under 5 minutes

  - Test: Time the creation of 10 Dell Chromebook 3100 devices with sequential serial numbers
  - Target: < 5 minutes total (< 30 seconds per asset)

- [ ] **SC-002**: Asset tag sequence increments correctly without gaps or duplicates across 100+ consecutive asset creations

  - Test: Create 100+ assets and verify sequential tags (W12-1001, W12-1002, ... W12-1100)
  - Verify no duplicates in RT and audit log

- [ ] **SC-003**: 95% of asset creation operations automatically generate printable labels within 2 seconds of asset creation

  - Test: Create 20 assets and measure label generation time for each
  - Target: 19+ complete within 2 seconds

- [ ] **SC-004**: Zero duplicate asset tags are assigned during bulk asset entry operations

  - Test: Create 50 assets rapidly (simulating concurrent use cases)
  - Verify all tags unique, no collisions

- [ ] **SC-005**: Users successfully complete asset creation on first attempt 90% of the time without validation errors
  - Test: User acceptance testing with 10 asset creation attempts
  - Target: 9+ succeed without validation errors (valid serial numbers, required fields filled)

---

## Notes

- Tasks are sequenced for single-developer execution; adjust for parallel team work
- [P] markers indicate tasks that can be parallelized (different files, no dependencies)
- [Story] labels map tasks to user stories for traceability and independent testing
- Each user story phase includes checkpoint for independent validation
- MVP (User Story 1 only) delivers core value in ~19 tasks
- Tests are NOT included as they were not explicitly requested in feature specification
- Commit after each task or logical group for easier rollback
- Verify quickstart.md steps match implementation at end (T040-T041)
