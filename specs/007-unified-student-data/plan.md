# Implementation Plan: Unified Student Data Management

**Branch**: `007-unified-student-data` | **Date**: 2025-12-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-unified-student-data/spec.md`

## Summary

Consolidate student device check-in and audit workflows into a unified Django Student model with CSV import via Django admin. The unified model will serve as the single source of truth for student data, automatically integrating with device check-in (updating student status when devices are returned) and supporting teacher-led audit sessions. No existing data preservation required - fresh Django tables will be created.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Django 4.2 LTS, django-import-export (CSV import/export in admin)  
**Storage**: SQLite3 (database.sqlite via Django ORM)  
**Testing**: pytest with pytest-django  
**Target Platform**: Linux server (NixOS), macOS (development)
**Project Type**: Web application (Django)  
**Performance Goals**: Import 500+ students in <30 seconds, audit session completion <5 minutes  
**Constraints**: CSV columns must be exact names (student_id, first_name, last_name, grade, advisor, username)  
**Scale/Scope**: ~500-1000 students per school year, ~30 students per audit session

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Documentation-First | ✅ PASS | Spec completed with 4 user stories, edge cases resolved, clarifications recorded |
| II. Modular Routing | ✅ PASS | Uses existing `apps/students/` and `apps/audit/` Django apps |
| III. Specification-Driven Testing | ✅ PASS | Each user story has independent acceptance scenarios |
| IV. RT API Integration | ✅ PASS | Device check-in integration uses `common/rt_api.py` |
| V. Configuration Management | ✅ PASS | No new environment variables required |

**Authentication Requirement**: 
- TEACHERS: Access to `/audit/*` routes only (per ROLE_ACCESS_RULES)
- tech-team: Full access including `/devices/*`, `/admin/*`, `/students/*`

## Project Structure

### Documentation (this feature)

```text
specs/007-unified-student-data/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (affected paths)

```text
apps/
├── students/
│   ├── models.py        # MODIFY: Enhanced Student model with unified fields
│   ├── admin.py         # MODIFY: CSV import/export, filtering, search
│   ├── views.py         # MODIFY: API endpoints for device integration + check-in status view
│   ├── urls.py          # MODIFY: Add check-in status and API routes
│   └── migrations/      # NEW: Fresh migration for unified Student model
├── audit/
│   ├── models.py        # MODIFY: AuditStudent references unified Student, FK to AuditSession
│   ├── admin.py         # NEW: AuditSession admin interface
│   ├── views.py         # MODIFY: Use unified Student for audit sessions, session detail view
│   ├── urls.py          # MODIFY: Add audit session list/detail/API routes
│   └── migrations/      # NEW: Migration for AuditStudent FK to Student
└── devices/
    ├── views.py         # MODIFY: Auto-update student status on check-in, device check-in view
    ├── urls.py          # MODIFY: Add device check-in form view and API endpoints
    └── forms.py         # NEW: Device check-in form

templates/
├── base.html            # NEW: Base template with role-aware navigation
├── devices/
│   └── checkin.html     # NEW: Device check-in form (separate from Flask version)
├── students/
│   └── checkin_status.html    # NEW: Check-in status dashboard (ref: old `/student-devices`)
└── audit/
    ├── session_list.html       # NEW: Audit session list for teachers
    └── session_detail.html     # NEW: Audit session detail with students

common/
└── rt_api.py            # EXISTING: Used for RT asset lookups during check-in
```

## UI/UX Design Specifications

### 1. Device Check-In Interface (`/devices/check-in`)

**Access**: Tech-Team only  
**Frequency**: Used once per year during device collection season  
**Context**: Staff scanning devices with barcode scanners or manual entry

**Page Layout**:
- **Header**: "Device Check-In" title with brief description
- **Input Section**: Asset tag/name input field (for barcode scanner or manual entry)
- **Device Lookup**: Display device details from RT after lookup
- **Student Auto-Update**: Show student name and confirm status update automatically happens
- **Confirmation**: Show success/error messages
- **Check-In Log**: Optional summary of today's check-ins (TBD in Phase 4)

**Key Features** (based on user clarification):
- Fail-safe: If RT API fails, show error and don't update student
- Re-check-in: Warn if device already checked in, require confirmation to override (FR-018)
- Confirmation message showing which student was updated
- Status indicator: Show device_checked_in status for scanned device

**Technical Details**:
- Form POST to `/devices/api/check-in` 
- Response includes: device info, student name (if found), check_in status
- No pagination needed (small deployment, <500 students)

**Reference**: Current Flask `/devices/check-in` page provides styling/layout template

---

### 2. Check-In Status Dashboard (`/students/check-in-status`)

**Access**: Tech-Team only  
**Frequency**: Used during device collection season to track progress  
**Context**: Manager viewing overall check-in progress and identifying missing devices

**Page Layout**:
- **Header**: "Device Check-In Status" title
- **Summary Cards** at top:
  - Total students
  - Checked in (count + percentage)
  - Not yet checked in (count + percentage)
  - Last check-in timestamp
- **Filters**: 
  - Grade filter dropdown (all grades)
  - Student search box (by name/ID)
  - Apply filters button
- **Student List** (table):
  - Columns: Student ID, Name, Grade, Advisor, Check-in Status (Yes/No), Check-in Date, Device Info (if checked in)
  - Sortable by: Name, Grade, Check-in Status, Date
  - Rows color-coded: Green (checked in), Gray (pending)
- **Actions**:
  - Export to CSV button (downloads current filtered list)

**Performance** (FR-016):
- Optimized for <500 students, no pagination
- <2 second load time target
- Filters applied client-side or server-side with caching

**Reference**: Current Flask `/student-devices` page provides styling/layout template

---

### 3. Audit Session List (`/audit/`)

**Access**: Teachers only  
**Frequency**: Started at beginning of audit period, updated throughout  
**Context**: Teachers viewing active audit sessions and starting new ones

**Page Layout**:
- **Header**: "Device Audits" title with description
- **Summary Cards** for current active session (if exists):
  - Students in session
  - Audited count + percentage
  - Advisor (filter by)
  - Grade (filter by)
- **Active Session Section**:
  - Session info: Created date, created by teacher
  - Quick stats card
  - "View Full Session" button → links to session detail
- **Session History** (table):
  - Shows completed audit sessions (if any)
  - Columns: Session Date, Created By, Audited Count, Status (Active/Complete)
- **Actions**:
  - "Start New Audit Session" button (creates new session, admin approves before teacher uses)

**Role Enforcement**:
- Teachers see only their own advisor students (filtered automatically)
- Only admins can close sessions

**Reference**: Current Flask `/devices/audit/` page provides styling/layout template

---

### 4. Audit Session Detail (`/audit/session/<id>`)

**Access**: Teachers only (can mark students as audited)  
**Frequency**: Repeatedly throughout audit session (multiple times per year)  
**Context**: Teacher verifying student device possession and marking complete

**Page Layout**:
- **Header**: "Audit Session [Date]" with status indicator
- **Summary Cards** at top:
  - Total students in this session
  - Audited (count + percentage of current filter)
  - Not audited (count)
  - Completion percentage
- **Filters** (update the list below):
  - Grade filter dropdown (auto-populated from students in session)
  - Advisor filter dropdown (auto-populated from students in session, pre-selected to teacher's advisees)
  - Apply filters button
  - Shows "Filtered: X of Y students" when filters applied
- **Student List** (table):
  - Columns: Student Name, Grade, Advisor, Audited Status (Checkbox + date/time if complete)
  - Rows color-coded: Green (audited), Gray (pending)
  - Checkbox per student to mark as audited
  - Clicking checkbox records: timestamp, teacher name, status=audited
  - Can uncheck to remove audit status
- **Batch Actions**:
  - "Mark All [Filtered] as Audited" button
  - "Mark All [Filtered] as Not Audited" button
- **Export**:
  - "Download Report" button → CSV with audit results

**Key Features** (based on user clarification):
- Session is global/shared - multiple teachers see same session
- Filters are persistent within session (for teacher's context)
- Auto-save on checkbox: no "Save" button needed, updates immediately
- Real-time update of summary percentages as checkboxes change
- Show which teacher audited each student (auditor_name field)

**Admin Close Flow** (separate admin interface):
- Only admins can close audit session
- Closing records final_count, marks status=complete
- Closed sessions remain visible for historical reference (FR-019)

**Reference**: Current Flask audit pages provide styling/layout template

---

## Navigation & Access Control

### Base Template (`templates/base.html`)

**Role-Aware Navigation**:
```html
<!-- For Tech-Team users -->
<nav>
  - Device Check-In (/devices/check-in)
  - Check-In Status (/students/check-in-status)
  - Django Admin (/admin)

<!-- For Teachers -->
<nav>
  - Device Audits (/audit)

<!-- For Both -->
  - Home
  - Help
```

### ROLE_ACCESS_RULES Integration

- **Tech-Team** (LDAP): `/devices/check-in`, `/students/check-in-status`, `/admin`, `/devices/api/*`, `/students/api/*`
- **Teachers** (LDAP): `/audit`, `/audit/session/*`, `/audit/api/*`
- **Admins** (subset of Tech-Team): `/admin` (for closing audit sessions manually if needed)

---

## Data Model Relationships

### Check-In Flow

```
Student (unified)
  ├─ device_checked_in: boolean
  ├─ check_in_date: datetime
  └─ device_info: OneToOneField
     ├─ asset_id
     ├─ asset_tag
     ├─ serial_number
     └─ device_type
```

### Audit Flow

```
AuditSession (global, admin-created)
  ├─ created_by: user
  ├─ created_at: datetime
  ├─ closed_at: datetime (null until closed)
  ├─ status: active/closed
  └─ audit_students: reverse FK
     ├─ student: FK to Student
     ├─ audited: boolean
     ├─ audit_timestamp: datetime
     ├─ auditor_name: string (teacher name)
     └─ grade/advisor: cached from Student at time of audit
```



## Complexity Tracking

> **No violations detected** - All constitution principles satisfied.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CSV column mismatch | Medium | High | Validate columns before import, clear error messages |
| FK integrity on Student deletion | Low | High | Use PROTECT/SET_NULL for audit records |
| Import performance with large CSVs | Low | Medium | Batch processing in django-import-export |
| Teacher accessing check-in routes | Low | Medium | ROLE_ACCESS_RULES already restricts to `/audit/*` only |

## Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| API Contracts | [contracts/api.md](./contracts/api.md) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |
| Task Breakdown | [tasks.md](./tasks.md) | ✅ Complete |

## Next Steps

1. Run `speckit.tasks` to generate implementation task breakdown
2. Implement Phase 3 tasks in order:
   - Create unified Student model with django-import-export
   - Update AuditStudent FK relationship
   - Integrate device check-in with student status updates
   - Add admin filtering and search capabilities
3. Run tests to verify acceptance criteria

---

*Plan generated by speckit.plan | Ready for speckit.tasks*
