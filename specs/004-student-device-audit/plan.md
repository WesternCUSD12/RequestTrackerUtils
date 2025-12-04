# Implementation Plan: Student Device Audit

**Branch**: `004-student-device-audit` | **Date**: December 1, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-student-device-audit/spec.md`

**Note**: This plan follows the `/speckit.plan` command workflow.

## Summary

Create a web-based student device audit interface at `/devices/audit` that enables teachers to verify student device possession through CSV upload, RT integration for device lookup, verification tracking, and IT communication via notes. The system manages audit sessions, maintains completion history, and supports re-audit capabilities.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 2.2+, requests 2.28+ (RT API), SQLite3 (audit storage), CSV module (file parsing)
**Storage**: SQLite database (existing `database.sqlite` in instance path) + session-based audit state
**Testing**: pytest for unit/integration tests
**Target Platform**: Web application (Linux/macOS server, browser-based UI)
**Project Type**: Web application with backend API routes and frontend templates
**Performance Goals**:

- CSV upload processing: <10 seconds for 500 students
- RT device query: <3 seconds per student (95th percentile)
- Concurrent users: 10 simultaneous auditors without degradation
  **Constraints**:
- Existing RT API integration patterns must be preserved
- Database schema additions only (no modifications to existing tables)
- Must integrate with existing student tracking utilities
- Browser-based UI with no external frontend framework requirements
  **Scale/Scope**:
- 500 students per audit session
- Multiple concurrent audit sessions
- Audit history retention (indefinite)
- 3 new database tables, 2 new route files, 4-6 new templates

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

Constitution file is a template placeholder - no specific project principles defined. No violations to check.

## Project Structure

### Documentation (this feature)

```text
specs/004-student-device-audit/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
│   └── api.yaml        # OpenAPI spec for audit endpoints
└── checklists/
    └── requirements.md  # Quality checklist (completed)
```

### Source Code (repository root)

```text
request_tracker_utils/
├── routes/
│   ├── __init__.py
│   ├── audit_routes.py           # NEW: Audit interface routes
│   ├── device_routes.py           # Existing device check-in routes
│   ├── student_routes.py          # Existing student routes
│   ├── asset_routes.py
│   ├── label_routes.py
│   └── tag_routes.py
├── templates/
│   ├── audit_upload.html          # NEW: CSV upload & student list
│   ├── audit_verify.html          # NEW: Device verification form
│   ├── audit_history.html         # NEW: Completed audits view
│   ├── audit_report.html          # NEW: IT staff notes review
│   ├── base.html                  # Existing base template
│   └── [other existing templates]
├── static/
│   ├── js/
│   │   └── audit.js              # NEW: Client-side audit logic
│   └── css/
│       └── [existing styles]
├── utils/
│   ├── audit_tracker.py           # NEW: Audit session management
│   ├── csv_validator.py           # NEW: CSV parsing & validation
│   ├── rt_api.py                  # Existing RT API client
│   ├── db.py                      # Existing database utilities
│   └── [other existing utils]
├── __init__.py                    # Update to register audit_routes
└── config.py                      # Existing configuration

tests/
├── unit/
│   ├── test_audit_tracker.py     # NEW: Audit logic tests
│   ├── test_csv_validator.py     # NEW: CSV validation tests
│   └── [existing unit tests]
├── integration/
│   ├── test_audit_workflow.py    # NEW: End-to-end audit tests
│   └── [existing integration tests]
└── fixtures/
    ├── sample_audit.csv           # NEW: Test CSV data
    └── [existing fixtures]
```

**Structure Decision**: Web application structure selected. This follows the existing Flask application pattern with:

- Blueprint-based routing in `request_tracker_utils/routes/`
- Jinja2 templates in `request_tracker_utils/templates/`
- Utility modules in `request_tracker_utils/utils/`
- SQLite database managed via `utils/db.py`
- Integration with existing RT API client patterns

The audit feature will be mounted at `/devices/audit` (as specified) by registering the audit blueprint with prefix `/devices` and creating routes under `/audit`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations identified. Standard Flask web application patterns apply.

---

## Phase 0: Research & Discovery

**Goal**: Resolve all NEEDS CLARIFICATION items and establish technical patterns

### Research Tasks

1. **CSV Parsing Strategy**

   - Question: How to handle various CSV encodings (UTF-8, UTF-16, Latin-1) and special characters?
   - Research: Python `csv` module capabilities, `chardet` for encoding detection
   - Decision needed: Strict validation vs. flexible parsing with warnings

2. **Session Management**

   - Question: How to maintain audit state across page refreshes (which students uploaded, which audited)?
   - Research: Flask session storage, database-backed sessions vs. in-memory
   - Decision needed: Session timeout duration, cleanup strategy

3. **RT Device Query Optimization**

   - Question: How to minimize RT API calls when fetching devices for multiple students?
   - Research: Existing RT API caching patterns (PersistentAssetCache), batch query capabilities
   - Decision needed: Cache TTL, batch size for device lookups

4. **Duplicate Student Handling**

   - Question: How to detect and handle duplicate students in CSV (same name, different grade)?
   - Research: Identity criteria (name+grade vs. name+advisor vs. all fields)
   - **DECISION**: Students are uniquely identified by composite key (name + grade + advisor). Duplicates within same CSV file are flagged during upload with option to review/confirm. If user confirms, only first instance is imported. This allows for same-name students in different grades while preventing accidental duplicates.

5. **Partial Audit Recovery**

   - Question: Can teachers save partial audits and resume later?
   - Research: Database schema for in-progress audits, timeout handling
   - **DECISION**: Client-side auto-save to browser localStorage every 30 seconds during device verification. On page reload, detect unsaved state and display "Resume Previous Audit?" prompt. Server-side database stores completed audits only (not in-progress). This avoids database complexity while providing recovery from accidental navigation/refresh.

6. **Concurrent Audit Conflicts**

   - Question: What happens if two teachers audit the same student simultaneously?
   - Research: Database locking, optimistic concurrency, last-write-wins
   - Decision needed: Conflict detection strategy, user notification

7. **Audit History Retention**
   - Question: How long to retain audit records? Archive or delete old audits?
   - Research: Storage requirements, compliance needs
   - **DECISION**: Audit records retained indefinitely (no automatic deletion). Manual archive/export feature provided for records >1 year old. SQLite database size monitoring recommended. Cleanup utility `delete_old_sessions(days=90)` available for manual execution by IT staff via admin interface or scheduled cron job (documented in deployment guide).

### Output

Create `research.md` documenting:

- Decision for each research task
- Rationale for chosen approach
- Alternatives considered and rejected
- Links to relevant documentation

---

## Phase 1: Design & Contracts

**Prerequisites**: `research.md` complete

### Data Model

Create `data-model.md` with:

#### Entities

**AuditSession**

- Fields: session_id (UUID), creator_name, created_at, status (active/completed), student_count
- Relationships: Has many AuditStudents
- Validations: session_id unique, creator_name not empty
- State Transitions: active → completed (when all students audited or session closed)

**AuditStudent**

- Fields: id (auto-increment), session_id (FK), name, grade, advisor, audited (boolean), audit_timestamp, auditor_name
- Relationships: Belongs to AuditSession, Has many AuditDeviceRecords
- Validations: name required, grade required, advisor required; composite unique key (name + grade + advisor) within session
- State Transitions: unaudited → audited (when verification submitted)

**AuditDeviceRecord**

- Fields: id (auto-increment), audit_student_id (FK), asset_id, asset_tag, serial_number, device_type, verified (boolean), notes
- Relationships: Belongs to AuditStudent
- Validations: asset_id required from RT, verified boolean required
- State Transitions: unverified → verified (when checkbox marked)

**AuditNote**

- Fields: id (auto-increment), audit_student_id (FK), note_text, created_at, created_by
- Relationships: Belongs to AuditStudent
- Validations: note_text max 5000 characters

#### Database Schema (SQLite)

```sql
CREATE TABLE audit_sessions (
    session_id TEXT PRIMARY KEY,
    creator_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed')),
    student_count INTEGER DEFAULT 0
);

CREATE TABLE audit_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    advisor TEXT NOT NULL,
    audited INTEGER DEFAULT 0,
    audit_timestamp TIMESTAMP,
    auditor_name TEXT,
    FOREIGN KEY (session_id) REFERENCES audit_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE audit_device_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_student_id INTEGER NOT NULL,
    asset_id TEXT NOT NULL,
    asset_tag TEXT,
    serial_number TEXT,
    device_type TEXT,
    verified INTEGER DEFAULT 0,
    FOREIGN KEY (audit_student_id) REFERENCES audit_students(id) ON DELETE CASCADE
);

CREATE TABLE audit_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audit_student_id INTEGER NOT NULL,
    note_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    FOREIGN KEY (audit_student_id) REFERENCES audit_students(id) ON DELETE CASCADE
);

CREATE INDEX idx_audit_students_session ON audit_students(session_id);
CREATE INDEX idx_audit_students_audited ON audit_students(audited);
CREATE INDEX idx_audit_device_records_student ON audit_device_records(audit_student_id);
CREATE INDEX idx_audit_notes_student ON audit_notes(audit_student_id);
```

### API Contracts

Create `contracts/api.yaml` (OpenAPI 3.0):

#### Endpoints

**POST /devices/audit/upload**

- Purpose: Upload CSV file and create audit session
- Request: multipart/form-data with CSV file
- Response: 201 Created with session_id, student list
- Errors: 400 (invalid CSV), 413 (file too large)

**GET /devices/audit/session/{session_id}/students**

- Purpose: Get students in audit session (with filtering)
- Query params: audited (true/false), search (name/grade/advisor)
- Response: 200 OK with student list
- Errors: 404 (session not found)

**GET /devices/audit/student/{student_id}/devices**

- Purpose: Query RT for student's devices
- Response: 200 OK with device list from RT
- Errors: 404 (student not found), 502 (RT unavailable), 504 (RT timeout)

**POST /devices/audit/student/{student_id}/verify**

- Purpose: Submit device verification for a student
- Request: JSON with verified device IDs, notes
- Response: 200 OK with updated audit status
- Errors: 400 (incomplete verification), 404 (student not found), 409 (already audited)

**GET /devices/audit/session/{session_id}/completed**

- Purpose: View completed audits in session
- Response: 200 OK with audited students
- Errors: 404 (session not found)

**POST /devices/audit/student/{student_id}/re-audit**

- Purpose: Restore student to active audit list
- Response: 200 OK with updated status
- Errors: 404 (student not found), 400 (not previously audited)

**GET /devices/audit/notes**

- Purpose: IT staff view of all audit notes
- Query params: session_id, date_from, date_to
- Response: 200 OK with notes list
- Errors: 403 (unauthorized - if auth added later)

### Quickstart Guide

Create `quickstart.md`:

````markdown
# Student Device Audit Quickstart

## Running the Feature

1. Start Flask server: `python run.py`
2. Navigate to `http://localhost:8080/devices/audit`
3. Upload CSV with columns: name, grade, advisor
4. Select student to verify devices
5. Check device possession and submit
6. View completed audits or IT notes

## CSV Format

Required columns (order doesn't matter):

- `name`: Student full name
- `grade`: Grade level (e.g., "9", "10", "11", "12")
- `advisor`: Advisor/homeroom teacher name

Example:

```csv
name,grade,advisor
John Smith,9,Mr. Johnson
Jane Doe,10,Ms. Williams
```
````

## Testing

Run unit tests: `pytest tests/unit/test_audit_*.py`
Run integration tests: `pytest tests/integration/test_audit_workflow.py`

````

### Agent Context Update

Run: `.specify/scripts/bash/update-agent-context.sh copilot`

This will add to `.github/copilot-instructions.md`:
```markdown
## Active Technologies
- Python 3.11+ + Flask 2.2+, requests 2.28+ (RT API), SQLite3 (audit tracking), CSV module (file parsing)

## Project Structure
````

request*tracker_utils/routes/audit_routes.py (NEW)
request_tracker_utils/utils/audit_tracker.py (NEW)
request_tracker_utils/templates/audit*\*.html (NEW)

```

## Commands
pytest tests/unit/test_audit_*.py
pytest tests/integration/test_audit_workflow.py
```

---

## Phase 2: Task Breakdown

**Note**: Phase 2 (task creation) is handled by `/speckit.tasks` command and is NOT part of this plan output.

The implementation will follow this priority order based on user stories:

### P1: CSV Upload & Student List (MVP)

- Implement CSV parsing and validation
- Create audit session management
- Build upload UI and student list display
- Add search/filter functionality

### P2: Device Verification

- Integrate RT device query
- Build verification form UI
- Implement audit submission logic
- Add notes field

### P3: Completed Audits View

- Create completed audits display
- Implement re-audit functionality
- Add audit history tracking

### P4: IT Staff Notes View

- Build notes aggregation query
- Create IT staff review interface
- Add export/reporting capabilities

---

## Success Metrics Tracking

Map success criteria to measurable implementations:

- **SC-001** (Upload <10s for 500 students): Add timing logging to CSV upload endpoint
- **SC-002** (Audit <60s per student): Add client-side audit timer
- **SC-003** (95% RT queries <3s): Add RT query performance metrics to logs
- **SC-004** (40% productivity increase): Track audit completion rate (students/hour)
- **SC-005** (Zero data loss): Add database transaction logging and backup validation
- **SC-006** (IT review <5min): Add notes view load time metrics
- **SC-007** (80% satisfaction): Create post-audit feedback form
- **SC-008** (10 concurrent users): Add load testing with concurrent audit sessions

---

## Implementation Notes

### Integration Points

1. **Existing RT API Client** (`utils/rt_api.py`):

   - Use `get_assets_by_owner(owner_id)` to fetch student devices
   - Use `fetch_user_data(user_id)` to resolve student names to RT user IDs
   - Follow existing caching patterns with `PersistentAssetCache`

2. **Existing Database** (`utils/db.py`):

   - Extend `init_db()` to create audit tables
   - Follow existing connection pattern with `get_db_connection()`
   - Use SQLite row factory for dict-like results

3. **Blueprint Registration** (`__init__.py`):

   - Register audit blueprint: `app.register_blueprint(audit_routes.bp, url_prefix='/devices')`
   - Routes will be accessible at `/devices/audit/*`

4. **Template Inheritance**:
   - Extend `base.html` for consistent navigation
   - Reuse existing CSS styles from static folder

### Security Considerations

- CSV file size limit: 5MB (configurable)
- File type validation: Only .csv files accepted
- SQL injection prevention: Use parameterized queries
- Session hijacking prevention: Use Flask secure sessions with secret key
- Input sanitization: Escape user input in templates

### Error Handling

- CSV parsing errors: Display line number and error description
- RT API failures: Show user-friendly message, log details, allow retry
- Database errors: Roll back transactions, log error, notify user
- Session timeout: Preserve partial work, notify user, allow recovery

### Logging Strategy

- Info: Audit session creation, CSV upload success, student verification completion
- Warning: Duplicate students detected, RT query timeout, partial audit save
- Error: CSV validation failure, RT API error, database transaction failure
- Debug: RT cache hits/misses, query performance, session state changes

---

## Dependencies

### Python Packages (existing, no new dependencies required)

- Flask 2.2+
- requests 2.28+
- sqlite3 (built-in)
- csv (built-in)
- uuid (built-in)
- datetime (built-in)
- logging (built-in)

### Development Dependencies (existing)

- pytest
- pytest-flask
- pytest-cov

No new package installations required - feature uses existing project dependencies.
