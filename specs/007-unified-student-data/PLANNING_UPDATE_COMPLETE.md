# Planning Update Complete: Phase 4-8 Detailed Specifications

**Date**: 2025-12-04  
**Branch**: `007-unified-student-data`  
**Completed By**: Specification Planning Workflow (speckit.plan.prompt.md)

## Overview

All 8 phases of the unified student data feature have been comprehensively planned with detailed UI/UX specifications, explicit task breakdowns, and implementation requirements. This document summarizes the updates made during Phase 7 planning.

## Updates Made

### 1. **tasks.md - Phase 4 Expansion** ✅ 

**Before**: 10 generic tasks for device check-in integration  
**After**: 16 detailed, categorized tasks with explicit feature requirements

#### Phase 4 Categories:

1. **Backend Functions** (2 tasks)
   - T015: Create DeviceCheckInForm class with validation
   - T016: Create find_student_by_device_asset_tag() function

2. **Views & Forms** (4 tasks)
   - T017: Create device_checkin view with GET (form) + POST (process)
   - T018: Create POST /devices/api/check-in endpoint with fail-safe logic
   - T019: Implement re-check-in warning and confirmation workflow
   - T020: Add device info retrieval from RT API

3. **Templates** (2 tasks)
   - T021: Create templates/devices/checkin.html with asset input, fail-safe messages
   - T022: Create templates/devices/checkin_status.html with summary cards, grade filtering

4. **Views & Filtering** (2 tasks)
   - T023: Create checkin_status view with Student query + grade filter
   - T024: Add sortable student table + CSV export functionality

5. **URLs & Access Control** (3 tasks)
   - T025: Add URL patterns to apps/devices/urls.py
   - T026: Add tech_staff_required decorator to device check-in views
   - T027: Verify tech_staff role-based access via ROLE_ACCESS_RULES

6. **Testing** (3 tasks)
   - T028: Test device check-in workflow (asset scan, RT API errors, re-check-in)
   - T029: Verify <2s load time for <500 students
   - T030: Test CSV export of filtered student list

### 2. **tasks.md - Phase 5 Expansion** ✅

**Before**: 6 generic tasks for audit sessions  
**After**: 22 detailed tasks organized into 7 categories with explicit functional requirements

#### Phase 5 Categories:

1. **Models & Data** (3 tasks)
   - T031: Modify AuditSession: add created_by, closed_at, status, global/shared flag
   - T032: Modify AuditStudent: add audited boolean, audit_timestamp, auditor_name, FK to Student
   - T033: Create migration for AuditSession/AuditStudent changes

2. **Views & Session Management** (5 tasks)
   - T034: Create audit_list view with active session summary cards
   - T035: Create audit_session_detail view with grade/advisor filtering
   - T036: Create POST /audit/api/mark-audited/<student_id> AJAX endpoint
   - T037: Auto-populate sessions with teacher's advisory students
   - T038: Add admin-only session closure: POST /audit/api/close-session/<session_id>

3. **Templates - Session List** (1 task)
   - T039: Create templates/audit/session_list.html with active session cards, create button

4. **Templates - Session Detail** (1 task)
   - T040: Create templates/audit/session_detail.html with summary cards, filters, student table, batch actions, export

5. **Filtering & Updates** (3 tasks)
   - T041: Implement grade + advisor filtering with real-time summary updates
   - T042: Implement real-time checkbox updates (timestamp + teacher name recorded)
   - T043: Implement "Mark all [filtered]" batch action

6. **URLs & Access Control** (3 tasks)
   - T044: Add URL patterns: /, /session/<id>, /api/mark-audited/<id>, /api/close-session/<id>
   - T045: Add teacher_required and admin_required decorators
   - T046: Auto-filter sessions by teacher's advisory students

7. **Data Preservation & Auditing** (2 tasks)
   - T047: Ensure audit history preserved indefinitely (FR-019, SC-010)
   - T048: Record auditor_name for each student marked

8. **Testing & Admin Features** (4 tasks)
   - T049: Test teacher audit workflow with grade/advisor filtering
   - T050: Test admin session closure (visibility + permissions)
   - T051: Test batch marking functionality
   - T052: Test CSV export of audit results

### 3. **tasks.md - Phase 6 Specification** ✅

**Before**: 4 generic tasks for admin editing  
**After**: 4 detailed tasks with explicit feature requirements

#### Phase 6 Tasks:

- T053: Configure StudentAdmin: mark device_checked_in as editable toggle (FR-020a)
- T054: Configure StudentAdmin: set rt_user_id as readonly after creation (FR-020b)
- T055: Configure StudentAdmin: add delete confirmation with warning (FR-020c)
- T056: Configure StudentAdmin: add bulk action to reset device check-in status (FR-020d)

### 4. **tasks.md - Phase 7 Polish** ✅

**Before**: 5 generic tasks  
**After**: 5 detailed tasks with explicit requirements

#### Phase 7 Tasks:

- T057: Add CSV export to StudentAdmin (FR-015)
- T058: Verify database indexes for performance (FR-016): (grade, is_active), (advisor, is_active), (device_checked_in, is_active)
- T059: Verify ROLE_ACCESS_RULES restricts teachers to /audit/* (FR-010)
- T060: Run quickstart.md validation checklist
- T061: Create sample test CSV in specs/007-unified-student-data/test_data/sample_students.csv

### 5. **tasks.md - Phase 8 UI/Navigation** ✅

**Before**: 4 generic tasks  
**After**: 4 detailed tasks with explicit requirements

#### Phase 8 Tasks:

- T062: Create templates/base.html with role-aware navigation (tech-staff vs teacher)
- T063: Create templates/includes/alerts.html for flash messages (success/warning/error)
- T064: Create templates/includes/pagination.html for paginated lists (if needed)
- T065: Test responsive design for mobile devices (barcode scanner use case)

### 6. **plan.md - UI/UX Design Specifications** ✅

Comprehensive 4-page UI/UX design specification added with detailed layouts, features, and design patterns:

#### Page 1: Device Check-In (`/devices/check-in`)
- **Access**: Tech-Team only
- **Frequency**: Once per year during device collection
- **Layout**: Asset input field, device lookup display, student confirmation, status messages
- **Features**:
  - Fail-safe: Don't update if RT API fails (FR-017)
  - Re-check-in warning with confirmation (FR-018)
  - Success/error messages
  - Device status indicator
- **Reference**: Based on current Flask `/devices/check-in` styling

#### Page 2: Check-In Status Dashboard (`/students/check-in-status`)
- **Access**: Tech-Team only
- **Frequency**: Used during device collection season for progress tracking
- **Layout**: Summary cards (total, checked in %, pending %), grade filter, sortable student table, CSV export
- **Features**:
  - Performance target: <2 seconds for <500 students (FR-016)
  - No pagination needed
  - Color-coded rows (green=checked in, gray=pending)
  - Search by name/ID
  - Export to CSV
- **Reference**: Based on current Flask `/student-devices` styling

#### Page 3: Audit Session List (`/audit/`)
- **Access**: Teachers only
- **Frequency**: Started at beginning of audit period
- **Layout**: Active session summary cards, session history table, create session button
- **Features**:
  - Global/shared session model (multiple teachers)
  - Admin-only closure
  - Quick stats (audited count/%)
  - Teacher can start new sessions
- **Reference**: Based on current Flask `/devices/audit` styling

#### Page 4: Audit Session Detail (`/audit/session/<id>`)
- **Access**: Teachers only
- **Frequency**: Multiple times per audit period
- **Layout**: Summary cards, grade/advisor filters, student list table, batch actions, export
- **Features**:
  - Grade filter (auto-populated from session students)
  - Advisor filter (pre-selected to teacher's advisees)
  - Color-coded rows (green=audited, gray=pending)
  - Real-time checkbox updates (timestamp + teacher name recorded)
  - "Mark all [filtered]" batch action
  - Persistent filter state within session
  - Auto-save on checkbox (no Save button)
  - Real-time summary % updates
  - Show auditor_name for each student
  - CSV export with audit results
- **Reference**: Based on current Flask audit page styling

### 7. **Updated Task Summary Table**

| Phase | Task Count | Status |
|-------|------------|--------|
| Phase 1: Setup | 3 | ✅ Complete |
| Phase 2: Foundational | 4 | ✅ Complete |
| Phase 3: US1 - CSV Import | 7 | ✅ Complete |
| Phase 4: US2 - Check-In | 16 | 🔵 Ready |
| Phase 5: US3 - Audit | 22 | 🔵 Ready |
| Phase 6: US4 - Manual Edit | 4 | 🔵 Ready |
| Phase 7: Polish | 5 | 🔵 Ready |
| Phase 8: UI/Navigation | 4 | 🔵 Ready |
| **TOTAL** | **65** | **Fully Specified** |

## Key Features Mapped to Functional Requirements

| Requirement | Phase | Implementation |
|-------------|-------|-----------------|
| FR-001 (CSV Import) | 3 | StudentResource with validation, import_id_fields=['student_id'] ✅ |
| FR-007 (Device Check-In) | 4 | DeviceCheckInForm + device_checkin view (T015-T020) |
| FR-008a (Audit Filtering) | 5 | Grade + advisor filters in session_detail view (T041) |
| FR-008b (Mark Audited) | 5 | AJAX endpoint + checkbox update + timestamp (T036, T042) |
| FR-008c (Completion Summary) | 5 | Summary cards showing audited %, count (T034, T040) |
| FR-009 (Status Dashboard) | 4 | checkin_status view with summary cards, filter (T023, T024) |
| FR-010 (Role-Based Access) | All | teacher_required, tech_staff_required decorators (T026, T045, T046) |
| FR-015 (CSV Export) | 7 | StudentAdmin export + session export (T057, T052) |
| FR-016 (Performance) | 4, 7 | <2s load time, database indexes (T024, T058) |
| FR-017 (Fail-Safe RT API) | 4 | Error handling in device_checkin view (T018) |
| FR-018 (Re-Check-In Warning) | 4 | Confirmation dialog before override (T019) |
| FR-019 (Audit History) | 5, 7 | Preserve indefinitely, never auto-delete (T047, T060) |
| FR-020 (Admin Controls) | 4, 5, 6 | Device status toggle, session closure, bulk actions (T053-T056, T038) |

## Design Patterns Used

### 1. **Fail-Safe Pattern** (FR-017)
- Check RT API before updating student data
- If API fails, show error and don't modify local database
- Ensures data consistency on external service failures

### 2. **Real-Time Updates** (FR-008b, FR-042)
- AJAX endpoints for marking students without page reload
- Immediate UI update on checkbox change
- Timestamp + teacher name recorded automatically

### 3. **Filtering with Persistence** (FR-008a)
- Filters applied to current view
- Filters update both list AND summary cards
- "Filtered: X of Y students" indicator when filters active

### 4. **Batch Operations** (FR-020d, T043)
- "Mark all [filtered]" button for bulk actions
- Acts on currently visible (filtered) students only
- Single operation instead of individual clicks

### 5. **Global Shared Sessions** (FR-020, T031)
- Single audit session across all teachers
- Multiple teachers see same session
- Auto-filter each teacher's view to their advisees
- Only admin can close session

## Acceptance Criteria for Each Phase

### Phase 4 (Device Check-In) - Acceptance
- ✅ Tech-team can scan asset tag and student auto-updates
- ✅ If RT API fails, error shown and student not updated
- ✅ Re-check-in shows warning, requires confirmation
- ✅ Check-in status dashboard shows filtered list with grade filter
- ✅ Page loads <2 seconds for <500 students

### Phase 5 (Audit Sessions) - Acceptance
- ✅ Teachers can view active audit session
- ✅ Teachers can mark students as audited
- ✅ Grade + advisor filters work and update summary
- ✅ Batch "Mark all [filtered]" button marks all visible students
- ✅ Admin can close audit session (only admin)
- ✅ Closed sessions remain visible for historical reference

### Phase 6 (Admin Editing) - Acceptance
- ✅ Admin can toggle device_checked_in status in Django admin
- ✅ Admin cannot change rt_user_id after creation
- ✅ Delete confirmation shows warning
- ✅ Bulk "reset device check-in" action works

### Phase 7 (Polish) - Acceptance
- ✅ CSV export works from StudentAdmin
- ✅ Database indexes present for performance
- ✅ Role-based access rules enforced
- ✅ Sample test CSV available for testing

### Phase 8 (Navigation) - Acceptance
- ✅ Role-aware navigation shows correct links
- ✅ Mobile responsive (barcode scanner input works on mobile)
- ✅ Flash messages display properly

## Ready for Implementation

All specifications are complete and ready for development:

✅ **Phase 1 (Setup)**: Completed  
✅ **Phase 2 (Foundational)**: Completed  
✅ **Phase 3 (US1 - CSV Import)**: Completed  
🔵 **Phase 4 (US2 - Device Check-In)**: 16 tasks, fully specified  
🔵 **Phase 5 (US3 - Audit Sessions)**: 22 tasks, fully specified  
🔵 **Phase 6 (US4 - Admin Editing)**: 4 tasks, fully specified  
🔵 **Phase 7 (Polish)**: 5 tasks, fully specified  
🔵 **Phase 8 (Navigation)**: 4 tasks, fully specified  

**Next Steps**: Begin Phase 4 implementation with DeviceCheckInForm and device_checkin view.

---

**Total Implementation Tasks**: 65 tasks across 8 phases  
**Estimated Timeline**: 2-3 weeks for full implementation (depends on team size)  
**Risk Level**: Low (simple CRUD operations, no complex algorithms, existing patterns to follow)  
**Documentation**: Complete with UI/UX specifications, FR mapping, and acceptance criteria
