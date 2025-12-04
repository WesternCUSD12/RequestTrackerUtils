# Tasks: Student Device Audit

**Input**: Design documents from `/specs/004-student-device-audit/`
**Prerequisites**: plan.md (complete), spec.md (complete)

**Tests**: Per Constitution Principle III (Specification-Driven Testing), unit tests for utilities and integration tests for workflows are REQUIRED.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This project uses Flask web application structure:

- Backend: `request_tracker_utils/`
- Templates: `request_tracker_utils/templates/`
- Static assets: `request_tracker_utils/static/`
- Tests: `tests/`

---

## Phase 0: Documentation (Constitution Compliance)

**Purpose**: Update subsystem documentation before implementation per Constitution Principle I

- [x] T000 Update docs/architecture/devices.md to document new /devices/audit routes, audit session management, CSV upload workflow, RT integration for device queries, and integration with existing device check-in workflows

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create directory structure: request_tracker_utils/routes/audit_routes.py, request_tracker_utils/utils/audit_tracker.py, request_tracker_utils/utils/csv_validator.py
- [x] T002 Create directory structure: request_tracker_utils/templates/ for audit_upload.html, audit_verify.html, audit_history.html, audit_report.html
- [x] T003 [P] Create directory structure: request_tracker_utils/static/js/audit.js
- [x] T004 [P] Create directory structure: tests/fixtures/sample_audit.csv for test data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Extend request_tracker_utils/utils/db.py init_db() to create audit_sessions table with fields: session_id (TEXT PRIMARY KEY), creator_name, created_at, status, student_count
- [x] T006 Extend request_tracker_utils/utils/db.py init_db() to create audit_students table with fields: id (AUTOINCREMENT), session_id (FK), name, grade, advisor, audited, audit_timestamp, auditor_name
- [x] T007 Extend request_tracker_utils/utils/db.py init_db() to create audit_device_records table with fields: id (AUTOINCREMENT), audit_student_id (FK), asset_id, asset_tag, serial_number, device_type, verified
- [x] T008 Extend request_tracker_utils/utils/db.py init_db() to create audit_notes table with fields: id (AUTOINCREMENT), audit_student_id (FK), note_text, created_at, created_by
- [x] T009 Add database indexes in request_tracker_utils/utils/db.py: idx_audit_students_session, idx_audit_students_audited, idx_audit_device_records_student, idx_audit_notes_student
- [x] T010 Create request_tracker_utils/routes/audit_routes.py with Flask Blueprint 'audit' (no url_prefix in blueprint definition - prefix set during registration)
- [x] T011 Register audit blueprint in request_tracker_utils/**init**.py create_app() with app.register_blueprint(audit_routes.bp, url_prefix='/devices')

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Upload Student List for Audit (Priority: P1) 🎯 MVP

**Goal**: Teachers can upload CSV files with student data (name, grade, advisor) and view a searchable list of students to audit

**Independent Test**: Upload a CSV file with 10-500 students, verify all appear in searchable list, test search by name/grade/advisor, verify duplicate detection, test invalid CSV rejection

### Implementation for User Story 1

- [x] T012 [P] [US1] Create CSV validation function in request_tracker_utils/utils/csv_validator.py: parse_audit_csv(file_path) returns list of students or validation errors
- [x] T013 [P] [US1] Add CSV column validation in request_tracker_utils/utils/csv_validator.py: validate_required_columns(headers) checks for name, grade, advisor columns
- [x] T014 [P] [US1] Add duplicate detection in request_tracker_utils/utils/csv_validator.py: detect_duplicates(students) identifies duplicate student entries using composite key (name + grade + advisor)
- [x] T015 [P] [US1] Add encoding detection in request_tracker_utils/utils/csv_validator.py: detect_encoding(file_bytes) handles UTF-8, UTF-16, Latin-1
- [x] T016 [P] [US1] Create AuditSession class in request_tracker_utils/utils/audit_tracker.py with methods: create_session(creator_name), add_students(session_id, students), get_session(session_id)
- [x] T017 [US1] Implement POST /audit/upload route in request_tracker_utils/routes/audit_routes.py: accepts CSV file upload, validates, creates session, returns session_id and student count
- [x] T018 [US1] Implement GET /audit/session/<session_id> route in request_tracker_utils/routes/audit_routes.py: renders main audit interface template
- [x] T019 [US1] Implement GET /audit/session/<session_id>/students API in request_tracker_utils/routes/audit_routes.py: returns JSON student list with filtering support (query params: search, audited=false)
- [x] T020 [US1] Create audit upload template in request_tracker_utils/templates/audit_upload.html: CSV file upload form, upload button, file validation feedback, extends base.html
- [x] T021 [US1] Add student list display to request_tracker_utils/templates/audit_upload.html: table with columns name/grade/advisor, search input fields, filter controls
- [x] T022 [US1] Create client-side search/filter in request_tracker_utils/static/js/audit.js: filterStudents() function, AJAX call to /audit/session/<id>/students endpoint
- [x] T023 [US1] Add CSV upload handling in request_tracker_utils/static/js/audit.js: form submission, progress indicator, error display, redirect to session view
- [x] T024 [US1] Add file upload validation in request_tracker_utils/routes/audit_routes.py: check file size (<5MB), file type (.csv only), row count (max 1000 students), return 400 errors with details
- [x] T025 [US1] Add duplicate handling logic in request_tracker_utils/routes/audit_routes.py: when duplicates detected, flag for review in response, allow user to confirm or cancel upload

**Checkpoint**: At this point, User Story 1 should be fully functional - can upload CSV, view students, search/filter list

---

## Phase 4: User Story 2 - Verify Student Device Possession (Priority: P2)

**Goal**: Teachers can select a student, view their RT-assigned devices, mark devices as verified with checkboxes, add notes, and submit the audit

**Independent Test**: Select a student from the list, verify RT devices load within 3 seconds, check all device boxes, add a note, submit audit, verify audit is logged in database

### Implementation for User Story 2

- [x] T026 [P] [US2] Add get_student(student_id) method to request_tracker_utils/utils/audit_tracker.py: returns student details from audit_students table
- [x] T027 [P] [US2] Add mark_student_audited(student_id, auditor_name, device_records, notes) method to request_tracker_utils/utils/audit_tracker.py: updates audit_students, inserts audit_device_records, inserts audit_notes
- [x] T028 [US2] Implement GET /audit/student/<student_id> route in request_tracker_utils/routes/audit_routes.py: renders audit verification template with student info
- [x] T029 [US2] Implement GET /audit/student/<student_id>/devices API in request_tracker_utils/routes/audit_routes.py: queries RT using get_assets_by_owner() with 3-retry exponential backoff (1s, 2s, 4s) for transient failures, returns JSON device list
- [x] T030 [US2] Add RT user lookup in request_tracker_utils/routes/audit_routes.py: resolve student name to RT user ID using fetch_user_data() with 3-retry exponential backoff (1s, 2s, 4s), handle user not found
- [x] T031 [US2] Implement POST /audit/student/<student_id>/verify route in request_tracker_utils/routes/audit_routes.py: accepts verified device IDs and notes, calls mark_student_audited(), returns success/error
- [x] T032 [US2] Create device verification template in request_tracker_utils/templates/audit_verify.html: displays student name/grade/advisor, device list with checkboxes, notes textarea, submit button, extends base.html
- [x] T033 [US2] Add device display in request_tracker_utils/templates/audit_verify.html: table with columns asset_tag/serial_number/device_type/verified_checkbox
- [x] T034 [US2] Add form validation in request_tracker_utils/static/js/audit.js: verifyStudent() function, check all devices marked, confirm submission, submit via AJAX
- [x] T035 [US2] Add RT query error handling in request_tracker_utils/routes/audit_routes.py: catch RT API timeout (504), RT unavailable (502), return user-friendly JSON error
- [x] T036 [US2] Add "no devices" handling in request_tracker_utils/templates/audit_verify.html: display message when RT returns empty device list, allow audit submission with note
- [x] T037 [US2] Add incomplete audit prevention in request_tracker_utils/routes/audit_routes.py: verify route checks all devices have verified status when devices exist, return 400 if incomplete; allow submission with zero devices if student has no assigned devices in RT
- [x] T038 [US2] Add success/error feedback in request_tracker_utils/static/js/audit.js: display success message on audit submission, redirect to student list, show errors inline

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - can upload students, select student, verify devices, submit audit

---

## Phase 5: User Story 4 - Add Notes for IT Staff (Priority: P2)

**Goal**: IT staff can view all audit notes in a dedicated interface, filter by session/date, see which devices are missing

**Independent Test**: Submit audits with notes for 3 students, navigate to IT notes view, verify all notes appear, test filtering by session, verify missing device highlights

### Implementation for User Story 4

- [x] T039 [P] [US4] Add get_all_notes(session_id=None, date_from=None, date_to=None) method to request_tracker_utils/utils/audit_tracker.py: queries audit_notes with joins to audit_students
- [x] T040 [US4] Implement GET /audit/notes route in request_tracker_utils/routes/audit_routes.py: accepts query params (session_id, date_from, date_to), calls get_all_notes(), renders IT report template
- [x] T041 [US4] Create IT staff notes template in request_tracker_utils/templates/audit_report.html: table with columns student/grade/note/devices/date, filter controls, export button, extends base.html
- [x] T042 [US4] Add missing device highlighting in request_tracker_utils/templates/audit_report.html: show devices with verified=0 in red/bold, count missing devices per student
- [x] T043 [US4] Add filter controls in request_tracker_utils/templates/audit_report.html: session dropdown, date range pickers, apply filter button
- [x] T044 [US4] Add filter logic in request_tracker_utils/static/js/audit.js: applyNotesFilter() function, reload page with query params
- [x] T045 [US4] Add notes export in request_tracker_utils/routes/audit_routes.py: GET /audit/notes/export returns CSV file with all notes data

**Checkpoint**: At this point, User Stories 1, 2, AND 4 should work - full audit workflow with IT notes review

---

## Phase 6: User Story 3 - Remove Audited Students from List (Priority: P3)

**Goal**: After audit submission, student is removed from active list, teachers can view completed audits and re-audit if needed

**Independent Test**: Complete audit for 2 students, verify they disappear from active list, navigate to completed audits view, verify both appear, click re-audit, verify student returns to active list

### Implementation for User Story 3

- [x] T046 [P] [US3] Add get_completed_audits(session_id) method to request_tracker_utils/utils/audit_tracker.py: queries audit_students where audited=1
- [x] T047 [P] [US3] Add restore_student_for_reaudit(student_id) method to request_tracker_utils/utils/audit_tracker.py: sets audited=0, clears audit_timestamp and auditor_name
- [x] T048 [US3] Implement GET /audit/session/<session_id>/completed route in request_tracker_utils/routes/audit_routes.py: calls get_completed_audits(), renders completed audits template
- [x] T049 [US3] Implement POST /audit/student/<student_id>/re-audit route in request_tracker_utils/routes/audit_routes.py: calls restore_student_for_reaudit(), returns success/error JSON
- [x] T050 [US3] Update GET /audit/session/<session_id>/students API in request_tracker_utils/routes/audit_routes.py: default filter audited=false to hide completed students
- [x] T051 [US3] Create completed audits template in request_tracker_utils/templates/audit_history.html: table with columns student/grade/auditor/timestamp/re-audit-button, extends base.html
- [x] T052 [US3] Add re-audit action in request_tracker_utils/static/js/audit.js: reauditStudent(student_id) function, confirm dialog, AJAX POST to re-audit endpoint, reload on success
- [x] T053 [US3] Add navigation link in request_tracker_utils/templates/audit_upload.html: "View Completed Audits" button linking to /audit/session/<id>/completed
- [x] T054 [US3] Update mark_student_audited() in request_tracker_utils/utils/audit_tracker.py: preserve existing audit_device_records when re-auditing (mark as historical)

**Checkpoint**: All user stories (1, 2, 3, 4) should now be independently functional - complete audit workflow with history and re-audit

---

## Phase 7: Testing (Constitution Compliance)

**Purpose**: Unit and integration tests per Constitution Principle III

### Unit Tests

- [ ] T065 [P] Create tests/unit/test_csv_validator.py: test parse_audit_csv() with valid CSV, test validate_required_columns() with missing columns, test detect_duplicates() with duplicate students, test detect_encoding() with UTF-8/UTF-16/Latin-1 files
- [ ] T066 [P] Create tests/unit/test_audit_tracker.py: test create_session(), test add_students(), test get_student(), test mark_student_audited(), test get_completed_audits(), test restore_student_for_reaudit()
- [ ] T067 [P] Create tests/fixtures/sample_audit_valid.csv with 10 valid student records (name, grade, advisor)
- [ ] T068 [P] Create tests/fixtures/sample_audit_invalid.csv with missing required columns for validation testing
- [ ] T069 [P] Create tests/fixtures/sample_audit_duplicates.csv with duplicate student entries for duplicate detection testing

### Integration Tests

- [ ] T070 Create tests/integration/test_audit_workflow.py: test full audit flow (upload CSV → select student → query RT devices → verify devices → submit audit → student removed from active list)
- [ ] T071 Add RT API mocking in tests/integration/test_audit_workflow.py: mock get_assets_by_owner() to return test device data, mock fetch_user_data() for student lookup, test RT timeout/error scenarios
- [ ] T072 Add database transaction testing in tests/integration/test_audit_workflow.py: verify audit_sessions creation, verify audit_students insertion, verify audit_device_records logging, verify audit_notes persistence

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T055 [P] Add logging in request_tracker_utils/routes/audit_routes.py: Info level for session creation, audit completion; Warning for duplicates, RT timeout; Error for CSV validation failure, RT API error
- [ ] T056 [P] Add error templates in request_tracker_utils/templates/: 404.html for session/student not found, 500.html for server errors
- [ ] T057 Add performance metrics in request_tracker_utils/routes/audit_routes.py: log CSV upload time, RT query time, audit submission time
- [ ] T058 Add session cleanup in request_tracker_utils/utils/audit_tracker.py: delete_old_sessions(days=90) method to archive completed sessions (manual execution via admin interface or scheduled cron job - deployment guide must document trigger mechanism)
- [ ] T059 Add CSV example in request_tracker_utils/templates/audit_upload.html: show example CSV format with sample rows, downloadable template
- [x] T060 [P] Add navigation updates in request_tracker_utils/templates/base.html: add "Device Audit" link to main navigation menu
- [x] T061 Update home page in request_tracker_utils/templates/index.html: add audit routes to API documentation with descriptions
- [x] T062 Add input sanitization in request_tracker_utils/routes/audit_routes.py: escape user input in notes field, validate session_id format, validate student_id format
- [ ] T063 Add concurrent session handling in request_tracker_utils/utils/audit_tracker.py: check for active sessions, allow multiple concurrent sessions per user
- [ ] T073 Add partial audit auto-save in request_tracker_utils/static/js/audit.js: auto-save device verification state every 30 seconds to browser localStorage, restore on page reload if session active
- [ ] T074 Add partial audit recovery UI in request_tracker_utils/templates/audit_verify.html: detect unsaved verification state on load, display "Resume Previous Audit?" prompt, restore checkbox states from localStorage
- [ ] T064 Security review of request_tracker_utils/routes/audit_routes.py: verify SQL injection prevention (parameterized queries), file upload security, session security

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1) can start after Foundational - no dependencies on other stories
  - User Story 2 (P2) can start after Foundational - depends on US1 student list being available for selection
  - User Story 4 (P2) can start after US2 - needs audit submission to generate notes
  - User Story 3 (P3) can start after US2 - needs completed audits to display
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ MVP
- **User Story 2 (P2)**: Depends on US1 (needs student list to select from) - Can integrate once US1 complete
- **User Story 4 (P2)**: Depends on US2 (needs audit submissions with notes) - Can implement once US2 complete
- **User Story 3 (P3)**: Depends on US2 (needs completed audits) - Can implement once US2 complete

### Within Each User Story

- US1: CSV validator and audit tracker can be built in parallel → then routes → then templates → then JavaScript
- US2: Audit tracker methods can be built in parallel with templates → then routes integrate everything
- US4: Notes query can be built while template is designed → then route integrates
- US3: Completed audits query and re-audit method in parallel → routes and templates follow

### Parallel Opportunities

**Setup (Phase 1)**: All 4 tasks can run in parallel (T001, T002, T003, T004 - different directories)

**Foundational (Phase 2)**: T005-T009 can run in parallel (all database table creation), then T010-T011 (blueprint setup)

**User Story 1**:

- T012, T013, T014, T015 can run in parallel (CSV validator functions)
- T016 can run in parallel with CSV validator (audit tracker class)
- T020, T021 can run in parallel (template creation)

**User Story 2**:

- T026, T027 can run in parallel (audit tracker methods)
- T032, T033 can run in parallel (template creation)

**User Story 4**:

- T039 can run in parallel with T041 (query method + template)

**User Story 3**:

- T046, T047 can run in parallel (audit tracker methods)

**Polish (Phase 7)**: T055, T056, T060 can run in parallel (logging, error templates, navigation)

---

## Parallel Example: User Story 1

```bash
# Parallel group 1: CSV validator functions (T012-T015)
Task T012: "Create CSV validation function in request_tracker_utils/utils/csv_validator.py"
Task T013: "Add CSV column validation in request_tracker_utils/utils/csv_validator.py"
Task T014: "Add duplicate detection in request_tracker_utils/utils/csv_validator.py"
Task T015: "Add encoding detection in request_tracker_utils/utils/csv_validator.py"

# Parallel group 2: Can run simultaneously with group 1
Task T016: "Create AuditSession class in request_tracker_utils/utils/audit_tracker.py"

# Sequential: T017-T019 depend on T012-T016 completion
# Then parallel group 3: Templates (T020-T021)
Task T020: "Create audit upload template in request_tracker_utils/templates/audit_upload.html"
Task T021: "Add student list display to request_tracker_utils/templates/audit_upload.html"

# Then JavaScript (T022-T023) depends on templates existing
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T011) - CRITICAL
3. Complete Phase 3: User Story 1 (T012-T025)
4. **STOP and VALIDATE**:
   - Test CSV upload with sample data
   - Verify student list displays correctly
   - Test search/filter functionality
   - Test duplicate detection
   - Test invalid CSV rejection
5. Deploy/demo MVP - teachers can now organize audit lists

### Incremental Delivery

1. **Foundation** (T001-T011) → Database and routing ready
2. **MVP: CSV Upload** (T012-T025) → Teachers can upload and view student lists ✅
3. **Add: Device Verification** (T026-T038) → Teachers can complete audits ✅
4. **Add: IT Notes** (T039-T045) → IT staff can review audit notes ✅
5. **Add: Audit History** (T046-T054) → Teachers can view completed audits and re-audit ✅
6. **Polish** (T055-T064) → Production-ready with logging, security, performance

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers (after Foundational phase complete):

**Sprint 1** (after T001-T011):

- Developer A: User Story 1 (T012-T025) - CSV upload and student list
- Developer B: Start User Story 2 utilities (T026-T027) - audit tracker methods

**Sprint 2** (after US1 complete):

- Developer A: User Story 4 (T039-T045) - IT notes view
- Developer B: Complete User Story 2 (T028-T038) - device verification

**Sprint 3** (after US2 complete):

- Developer A: User Story 3 (T046-T054) - audit history and re-audit
- Developer B: Polish (T055-T064) - logging, security, performance

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests are REQUIRED per Constitution Principle III (see Phase 7 tasks T065-T072)
- Database changes in Phase 2 must be tested before proceeding
- RT API integration should reuse existing patterns from rt_api.py
- All templates should extend base.html for consistent styling
- Use Flask sessions for audit session tracking across page refreshes
- CSV file upload limited to 5MB to prevent abuse
- Parameterized queries required for all database operations (SQL injection prevention)
