# Tasks: Unified Student Data Management

**Input**: Design documents from `/specs/007-unified-student-data/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not explicitly requested - implementation tasks only.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- **Apps**: `apps/students/`, `apps/audit/`, `apps/devices/`
- **Common utilities**: `common/`
- **Settings**: `rtutils/settings.py`
- **Tests**: `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency configuration

- [x] T001 Install django-import-export dependency and add to pyproject.toml
- [x] T002 Add 'import_export' to INSTALLED_APPS in rtutils/settings.py
- [x] T003 [P] Remove existing students/audit migrations to start fresh in apps/students/migrations/ and apps/audit/migrations/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models and database schema that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create unified Student model in apps/students/models.py with fields: student_id (PK), first_name, last_name, username, grade, advisor, rt_user_id, is_active, device_checked_in, check_in_date, created_at, updated_at
- [x] T005 [P] Create DeviceInfo model in apps/students/models.py with fields: student (OneToOne), asset_id, asset_tag, serial_number, device_type, check_in_timestamp
- [x] T006 Update AuditStudent model in apps/audit/models.py to add optional ForeignKey to Student (SET_NULL, null=True)
- [x] T007 Create and apply migrations: python manage.py makemigrations students audit && python manage.py migrate

**Checkpoint**: Database schema ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Import Student Data from SIS CSV (Priority: P1) 🎯 MVP

**Goal**: Technology staff can import student rosters from SIS CSV via Django admin

**Independent Test**: Export CSV from SIS, access Django admin at /admin/students/student/import/, upload CSV, verify all students appear with correct data (name, grade, advisor, username)

### Implementation for User Story 1

- [x] T008 [US1] Create StudentResource class in apps/students/resources.py with import_id_fields=['student_id'] and all CSV field mappings
- [x] T009 [US1] Implement before_import hook in StudentResource to mark all students as inactive (is_active=False) before CSV import
- [x] T010 [US1] Implement after_save_instance hook in StudentResource to set is_active=True for imported students
- [x] T011 [US1] Add CSV column validation in StudentResource.before_import_row to check required columns: student_id, first_name, last_name, grade, advisor, username
- [x] T012 [US1] Create StudentAdmin with ImportExportModelAdmin in apps/students/admin.py with resource_class=StudentResource
- [x] T013 [US1] Add list_display, list_filter, search_fields to StudentAdmin for grade, advisor, is_active, device_checked_in
- [x] T014 [US1] Add import/export buttons to StudentAdmin using ImportExportActionModelAdmin mixin

**Checkpoint**: User Story 1 complete - CSV import functional via Django admin

---

## Phase 4: User Story 2 - Unified Device Check-In with Student Tracking (Priority: P2)

**Goal**: When device is checked in, automatically update the associated student's status via end-user web interface at `/devices/check-in`

**Independent Test**: Navigate to `/devices/check-in`, scan device asset tag, verify device owner cleared in RT AND student record shows device_checked_in=True with DeviceInfo populated. Confirm re-check-in warnings work (FR-018). Verify <2s page load time (FR-016).

### Implementation for User Story 2

**Backend Functions**:
- [x] T015 [US2] Create student lookup function in apps/students/views.py: find_student_by_rt_user(rt_user_id) → Student or None
- [x] T016 [US2] Create update_student_checkin function in apps/students/views.py to set device_checked_in=True, check_in_date, and create/update DeviceInfo

**Views & Forms**:
- [x] T017 [US2] Create device_checkin view in apps/devices/views.py: GET returns form, POST processes asset lookup and check-in (tech_staff only, FR-007)
- [x] T018 [US2] Add device check-in fail-safe logic: If RT API fails, don't update student status, show error (FR-017)
- [x] T019 [US2] Add re-check-in logic: If device_checked_in=True, show warning and require confirmation before updating (FR-018)
- [x] T020 [US2] Create API endpoint in apps/devices/views.py: POST /devices/api/check-in with asset lookup and student update

**Templates**:
- [x] T021 [US2] Create templates/devices/checkin.html with: asset input form (FR-007), device details display, student confirmation, status messages, organized like old Flask `/devices/check-in`
- [x] T022 [US2] Create templates/students/checkin_status.html with: summary cards (total, checked in %, pending %), grade filter, student list table, export CSV button (FR-009, FR-016)

**Views & Filtering**:
- [x] T023 [US2] Add checkin_status view in apps/students/views.py: lists all students with grade filter, sort by name/grade/status (FR-016, SC-008 <2s load time)
- [x] T024 [US2] Add export to CSV functionality for checkin_status view

**URLs & Access Control**:
- [x] T025 [US2] Add URL patterns to apps/devices/urls.py: `/check-in` (GET/POST), `/api/check-in` (POST)
- [x] T026 [US2] Add URL patterns to apps/students/urls.py: `/check-in-status` (GET with grade filter)
- [x] T027 [US2] Add role-based access: tech_staff_required decorator to device check-in and status views

**Testing**:
- [x] T028 [US2] Test device check-in: scan asset, student auto-updates, RT API failure handling, re-check-in with confirmation (FR-018, FR-017)
- [x] T029 [US2] Verify checkin_status loads <2 seconds for <500 students, filters work correctly
- [x] T030 [US2] Test CSV export of filtered student list

**Checkpoint**: User Story 2 complete - device check-in views functional with auto-student updates

---

## Phase 5: User Story 3 - Teacher Device Audit Session (Priority: P3)

**Goal**: Teachers can verify student device possession through audit sessions using unified Student data via end-user web interface at `/audit/`

**Independent Test**: Navigate to `/audit/`, view/create audit session, mark students as audited with filters (grade, advisor), view completion summary. Verify filters work (FR-008a). Confirm admin-only session closure (FR-020).

### Implementation for User Story 3

**Models & Data**:
- [x] T031 [US3] Modify AuditSession model in apps/audit/models.py: add created_by (User), closed_at (nullable), status (active/closed), ensure global/shared across teachers (FR-020)
- [x] T032 [US3] Modify AuditStudent model in apps/audit/models.py: add audited (boolean), audit_timestamp (nullable), auditor_name (string), FK to Student, audited_count field
- [x] T033 [US3] Add migration for AuditSession and AuditStudent model changes

**Views & Session Management**:
- [x] T034 [US3] Create audit_list view in apps/audit/views.py: shows active audit session(s) with summary stats (FR-008, FR-008c)
- [x] T035 [US3] Create audit_session_detail view in apps/audit/views.py: shows student list with filters (grade, advisor), mark-audited functionality (FR-008b, FR-008a)
- [x] T036 [US3] Create API endpoint POST /audit/api/mark-audited/<student_id> to mark student as audited with teacher name (FR-008b)
- [x] T037 [US3] Auto-populate audit session with students filtered by teacher's advisor field and is_active=True (FR-008a)
- [x] T038 [US3] Add session closure logic (admin-only): POST /audit/api/close-session/<session_id> sets closed_at, status=closed (FR-020)

**Templates - Session List**:
- [x] T039 [US3] Create templates/audit/session_list.html with: active session summary cards (total students, audited %, completion %), create session button (admin), organized like old Flask `/devices/audit`

**Templates - Session Detail**:
- [x] T040 [US3] Create templates/audit/session_detail.html with:
  - Summary cards: students in session, audited count, %, completion %
  - Grade filter dropdown
  - Advisor filter dropdown (pre-selected to teacher's advisees)
  - Student list table: Name, Grade, Advisor, Audited checkbox + timestamp
  - Batch actions: "Mark all [filtered] as audited" button
  - Color-coded rows: Green (audited), Gray (pending)
  - Export button → CSV with audit results
  - Organized like old Flask audit pages

**Filtering & Updates**:
- [x] T041 [US3] Implement grade + advisor filtering in session_detail view (filters update summary cards + student list in real-time or page reload)
- [x] T042 [US3] Implement real-time checkbox updates: mark audited → records timestamp + teacher name, updates summary % automatically
- [x] T043 [US3] Implement batch action: "Mark all [filtered]" button marks all visible students as audited at once

**URLs & Access Control**:
- [x] T044 [US3] Add URL patterns to apps/audit/urls.py: `/` (list), `/session/<id>` (detail), `/api/mark-audited/<id>` (API), `/api/close-session/<id>` (admin-only API)
- [x] T045 [US3] Add role-based access: teacher_required decorator to audit views, admin_required for session closure
- [x] T046 [US3] Auto-filter audit sessions by teacher's advisees (only show students matching teacher's advisor field)

**Data Preservation & Auditing**:
- [x] T047 [US3] Ensure audit history preserved: keep all AuditSession/AuditStudent records indefinitely, never auto-delete (FR-019, SC-010)
- [x] T048 [US3] Record auditor_name for each student marked: capture teacher name who audited

**Testing & Admin Features**:
- [x] T049 [US3] Test teacher audit workflow: view session, filter by grade/advisor, mark students, see % update
- [x] T050 [US3] Test admin session closure: verify only admins can close sessions, closed sessions still visible
- [x] T051 [US3] Test batch marking: "Mark all" button marks all filtered students, updates summary
- [x] T052 [US3] Test CSV export of audit results with all student data and audit status

**Checkpoint**: User Story 3 complete - audit sessions use unified Student data with teacher + admin interface

---

## Phase 6: User Story 4 - Admin Manual Editing (Priority: P4)

**Goal**: Admins can manually edit student records for corrections and staff-triggered interventions via Django admin interface

**Independent Test**: Login as admin, open Student admin, verify editable fields (grade, advisor, rt_user_id), test readonly fields, verify device_checked_in toggle, test delete confirmation

### Implementation for User Story 4

**Admin Interface Enhancements**:
- [x] T053 [US4] Configure StudentAdmin in apps/students/admin.py: mark device_checked_in as editable toggle (FR-020a)
- [x] T054 [US4] Configure StudentAdmin: set rt_user_id as readonly after creation (FR-020b)
- [x] T055 [US4] Configure StudentAdmin: add delete confirmation with warning message (FR-020c)
- [x] T056 [US4] Configure StudentAdmin: add bulk action "Reset device check-in status" to clear device_checked_in + check_in_date (FR-020d)

**Checkpoint**: User Story 4 complete - manual editing via Django admin

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and validation

- [x] T057 [P] Export functionality to StudentAdmin for CSV download of student check-in status (FR-015)
- [x] T058 [P] Verify database indexes exist for Student model fields: (grade, is_active), (advisor, is_active), (device_checked_in, is_active) - defined in data-model.md for query performance (FR-016)
- [x] T059 [P] Verify ROLE_ACCESS_RULES in rtutils/settings.py restricts teachers to /audit/* only (already configured, no changes needed - FR-010)
- [x] T060 [P] Run quickstart.md validation checklist: all features work, CSV import functional, device check-in works, audit sessions work
- [x] T061 [P] Create sample test CSV file in specs/007-unified-student-data/test_data/sample_students.csv with 5-10 students for testing/demo

**Checkpoint**: Polish complete - system validated and ready for deployment

---

## Phase 8: Navigation & UI Integration

**Purpose**: Wire up user-facing interfaces with consistent navigation and styling

- [x] T062 [UI] Create templates/base.html with role-aware navigation: show Device Check-in, Check-in Status, Audit Sessions links based on user role (tech-staff vs teacher)
- [x] T063 [UI] Create templates/includes/alerts.html for flash messages and status alerts (success, warning, error) with Bootstrap styling
- [x] T064 [UI] Create templates/includes/pagination.html for paginated student lists (if needed)
- [x] T065 [UI] Test responsive design for mobile devices (barcode scanner use case - asset tag input should be large on mobile)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can proceed in priority order (P1 → P2 → P3 → P4)
  - Some stories can proceed in parallel if staffed
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses Student model from US1 setup but no code dependencies
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses Student model, independent of US1/US2
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Enhances admin created in US1

### Within Each User Story

- Models before services/resources
- Admin resources before admin registration
- Core implementation before UI integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003 can run in parallel with T001/T002 (different directories)
- T004 and T005 can run in parallel (same file but separate models)
- All User Stories can technically start after Phase 2, but sequential by priority is recommended
- T031 and T032 can run in parallel (different aspects of polish)

---

## Parallel Example: Foundational Phase

```bash
# Can run in parallel after T004:
Task T005: "Create DeviceInfo model in apps/students/models.py"
Task T006: "Update AuditStudent model in apps/audit/models.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T014)
4. **STOP and VALIDATE**: Import test CSV via Django admin, verify students created
5. Deploy/demo if ready - CSV import is functional MVP

### Incremental Delivery

1. Complete Setup + Foundational → Database ready
2. Add User Story 1 → CSV Import works → Demo (MVP!)
3. Add User Story 2 → Device check-in updates students → Demo
4. Add User Story 3 → Audit sessions use unified data → Demo
5. Add User Story 4 → Manual editing available → Demo
6. Each story adds value without breaking previous stories

---

## Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|----------------|
| Phase 1: Setup | 3 | 1 (T003) |
| Phase 2: Foundational | 4 | 1 (T005) |
| Phase 3: US1 - CSV Import | 7 | 0 |
| Phase 4: US2 - Check-In | 16 | 0 |
| Phase 5: US3 - Audit | 22 | 0 |
| Phase 6: US4 - Manual Edit | 4 | 0 |
| Phase 7: Polish | 5 | 0 |
| Phase 8: UI/Navigation | 4 | 0 |
| **Total** | **65** | **2** |

### Tasks by User Story

| User Story | Tasks | Description |
|------------|-------|-------------|
| US1 | T008-T014 (7 tasks) | CSV Import via Django Admin |
| US2 | T015-T030 (16 tasks) | Device Check-In Interface + Status Dashboard |
| US3 | T031-T052 (22 tasks) | Teacher Audit Sessions + Admin Closure |
| US4 | T053-T056 (4 tasks) | Admin Manual Data Editing |
| Polish | T057-T061 (5 tasks) | Validation & Sample Data |
| UI/Navigation | T062-T065 (4 tasks) | Navigation & Responsive Design |

### Independent Test Criteria

| Story | How to Verify |
|-------|---------------|
| US1 | Upload CSV at /admin/students/student/import/, verify data imported correctly |
| US2 | Check in device at /devices/check-in, verify student marked as checked in |
| US3 | Create audit session, verify students from unified table, complete audit |
| US4 | Edit student in admin, verify changes persist and display correctly |

### Suggested MVP Scope

**User Story 1 only** (Tasks T001-T014):
- Setup: Install django-import-export, configure settings
- Foundational: Create Student/DeviceInfo models, migrations
- US1: StudentResource with CSV import/export in admin

This delivers the core value: technology staff can import and manage student data from SIS CSV.
