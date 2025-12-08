# Feature Specification: Unified Student Data Management

**Feature Branch**: `007-unified-student-data`  
**Created**: 2025-12-04  
**Status**: Draft  
**Input**: User description: "student device checkin and student device audit should be more unified. They should use a shared student table to collate all necessary data with a management interface (can be in django admin) to load data from a csv exported from my SIS and edit data if needed"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import Student Data from SIS CSV (Priority: P1)

**Access Level**: Technology staff only (Django admin interface)

Technology staff need to import student rosters from the Student Information System (SIS) at the beginning of each school year to set up device tracking and audit capabilities.

**Why this priority**: This is the foundation - without student data imported, neither device checkin nor audit workflows can function. This must work first to enable all other features.

**Independent Test**: Can be fully tested by exporting a student CSV from SIS, accessing Django admin at `/admin/students/student/`, uploading the CSV file, and verifying all students appear in the system with correct data (name, grade, advisor, username).

**Acceptance Scenarios**:

1. **Given** Django admin is accessible and user is logged in as tech staff, **When** user navigates to Student management (`/admin/students/student/`) and uploads a CSV with columns (student_id, first_name, last_name, grade, advisor, username), **Then** all students are created/updated in the database with matching data
2. **Given** a student already exists in the database, **When** user uploads a CSV with updated information for that student (e.g., different grade or advisor), **Then** the existing student record is updated rather than creating a duplicate
3. **Given** CSV contains invalid data (missing required fields, malformed rows), **When** user attempts to upload, **Then** system displays clear error messages identifying which rows failed and why

---

### User Story 2 - Unified Device Check-In with Student Tracking (Priority: P2)

**Access Level**: Technology staff (end-user web interface at `/devices/check-in`)

Technology staff check in devices at end of school year and want the student who owned that device to automatically be marked as "checked in" without having to separately update two different systems.

**Why this priority**: This eliminates duplicate work and ensures data consistency between device returns and student audit status. It's the most frequent daily operation during device collection season.

**Independent Test**: Can be fully tested by navigating to `/devices/check-in`, scanning a device asset tag, verifying the device owner is set to "Nobody" in RT, and confirming the student record shows "checked in" status with device details populated.

**Acceptance Scenarios**:

1. **Given** a device is assigned to a student in RT, **When** tech staff accesses `/devices/check-in` and scans the device asset tag, **Then** device owner is cleared in RT AND the associated student record is marked as checked in with device details (asset ID, tag, serial number, type)
2. **Given** a device has no associated student in the database, **When** device is checked in, **Then** device check-in succeeds normally but no student record is updated
3. **Given** multiple devices are batch-checked in, **When** the batch process completes, **Then** all associated students are automatically marked as checked in and a summary shows how many students were updated

---

### User Story 3 - Teacher Device Audit Session (Priority: P3)

**Access Level**: Teachers (end-user web interface at `/audit/`)

Teachers need to verify which students in their advisory class have returned devices by conducting an audit session, marking students as audited as they verify device possession.

**Why this priority**: This provides an alternative verification workflow for teachers who don't have access to device scanning equipment. Less frequent than check-in but important for verification.

**Independent Test**: Can be fully tested by navigating to `/audit/`, creating an audit session (students auto-loaded from unified Student table filtered by teacher's advisory), marking students as audited through the interface, and reviewing the audit completion report showing completion percentage and unaudited students.

**Acceptance Scenarios**:

1. **Given** teacher is logged in and navigates to `/audit/`, **When** teacher creates a new audit session, **Then** system loads all active students assigned to teacher's advisory (filtered by grade level and advisor field) and creates an AuditSession with linked AuditStudent records
2. **Given** an active audit session with students displayed, **When** teacher marks a student as "audited", **Then** student status changes to "audited" with timestamp and auditor name (teacher) recorded in AuditStudent record
3. **Given** audit session is complete, **When** teacher views the session summary, **Then** system shows total students, number audited, percentage complete, and list of students not yet audited

---

### User Story 4 - Manually Edit Student Data in Django Admin (Priority: P4)

**Access Level**: Technology staff only (Django admin interface)

Technology staff need to manually correct student information (name spelling, grade level, advisor assignment) when SIS data contains errors or when handling edge cases.

**Why this priority**: Data cleanup and corrections are necessary but less frequent than daily operations. Can be done on an as-needed basis.

**Independent Test**: Can be fully tested by accessing Django admin at `/admin/students/student/`, editing a student's fields (name, grade, advisor), saving, and verifying the changes persist and display correctly in check-in and audit interfaces.

**Acceptance Scenarios**:

1. **Given** user is logged into Django admin as tech staff, **When** user edits a student record at `/admin/students/student/<id>/change/` and saves, **Then** changes are immediately reflected in device check-in and audit workflows
2. **Given** student has existing device check-in history, **When** user updates the student's name or grade, **Then** historical check-in records remain intact and show updated student information
3. **Given** user attempts to delete a student with associated device records, **When** user confirms deletion, **Then** system shows warning about related device records and allows choice to cascade delete or prevent deletion

---

### Edge Cases

- What happens when CSV upload contains duplicate student IDs within the same file?
- How does system handle CSV with different column names or order than expected? → Strict matching required: columns must be named exactly student_id, first_name, last_name, grade, advisor, username (order flexible)
- What if a student is marked as "checked in" but then needs to exchange a device (check out new one)?
- How are students handled who appear in audit CSV but not in the main student table?
- What happens when device is checked in but the student's RT user ID has changed since assignment?
- How does system handle students who transfer mid-year (removed from SIS export)? → Students not in new CSV import are marked as "inactive" status, preserving historical records
- What if audit session CSV contains students not in the main student database?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single Student model/table that serves both device check-in and audit workflows
- **FR-002**: System MUST provide Django admin interface for Student model with CSV import capability (tech staff only)
- **FR-002a**: System MUST restrict Django admin access to `/admin/` to technology staff only (no audit/check-in operations)
- **FR-003**: System MUST support CSV import with exact column names: student_id (primary key), first_name, last_name, grade, advisor, username (column order is flexible)
- **FR-004**: System MUST update existing student records when CSV contains matching student_id rather than creating duplicates
- **FR-004a**: System MUST mark students as "inactive" when they no longer appear in a new SIS CSV import, preserving historical device check-in data
- **FR-005**: System MUST validate CSV data and provide clear error messages for invalid rows
- **FR-006**: System MUST allow manual editing of all student fields through Django admin
- **FR-007**: System MUST provide end-user web interface for device check-in at `/devices/check-in` (technology staff, organized similarly to old Flask UI)
- **FR-007a**: System MUST integrate device check-in with student table - when device is checked in, associated student is automatically marked as checked in
- **FR-007b**: System MUST populate student device details (asset ID, asset tag, serial number, device type) when device is checked in
- **FR-007c**: System MUST display device check-in status and confirmation messages in web interface
- **FR-008**: System MUST provide end-user web interface for audit sessions at `/audit/` (teachers only)
- **FR-008a**: System MUST auto-populate audit sessions with students from unified Student table (filtered by teacher's advisory/grade)
- **FR-008b**: System MUST allow teachers to mark students as audited with timestamp and auditor name
- **FR-008c**: System MUST display audit session completion status and summary
- **FR-008d**: System MUST support audit CSV uploads that create AuditStudent records linked to the main Student table
- **FR-009**: System MUST provide web interface to view student device check-in status at `/students/check-in-status` with filters by grade and advisor
- **FR-010**: System MUST prevent deletion of students who have associated device check-in or audit records without confirmation
- **FR-011**: System MUST track check-in date/time and device information for each student
- **FR-012**: System MUST support filtering and searching students by grade, advisor, check-in status in Django admin
- **FR-013**: System MUST maintain referential integrity between Student table and AuditStudent/DeviceCheckIn records
- **FR-014**: System MUST provide export capability to generate CSV reports of student check-in status
- **FR-015**: System MUST enforce role-based access control: tech staff access check-in/admin views, teachers access audit views only
- **FR-016**: System MUST optimize check-in status view for small deployments (<500 students) with no pagination requirement and <2 second load time target
- **FR-017**: System MUST fail entire device check-in operation if RT API call fails (fail-safe consistency: don't update student status or create DeviceInfo if RT update fails)
- **FR-018**: System MUST display warning when re-checking in an already-checked-in device and require confirmation before updating check_in_date and DeviceInfo
- **FR-019**: System MUST preserve complete audit trail - keep all AuditSession and AuditStudent records indefinitely (no automatic deletion or archival)
- **FR-020**: System MUST restrict audit session closure to admins only; audit sessions are global/shared with multiple teachers participating in a single session

### Key Entities

- **Student**: Central student record containing identification (student_id as primary key, username for display/login), demographics (first_name, last_name, grade), assignment (advisor), RT integration (rt_user_id), status (is_active for tracking transfers), and check-in status (device_checked_in, check_in_date)
- **DeviceInfo**: Device details associated with student check-in including asset_id, asset_tag, serial_number, device_type, and check_in_timestamp. Has one-to-one relationship with Student
- **AuditSession**: Global/shared teacher-led audit session for verifying student device possession across multiple teachers. Contains session_id, creator_name (initiating teacher), created_at, closed_at (null until admin closes), status (active/closed), and student_count. Closure is admin-only action (FR-020). Multiple teachers can mark students as audited within a single session (FR-008b).
- **AuditStudent**: Student record within an audit session. References main Student table for core data, adds audit-specific fields (audited status, audit_timestamp, auditor_name). Has many-to-one relationship with AuditSession
- **AuditDeviceRecord**: Device verification records found during audit. Has many-to-one relationship with AuditStudent

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Technology staff can import 500+ student records from SIS CSV in under 30 seconds with zero data loss
- **SC-002**: Device check-in automatically updates student status in 100% of cases where student-device association exists in RT
- **SC-003**: Teachers can complete audit sessions for 30-student advisory classes in under 5 minutes
- **SC-004**: Eliminate duplicate student data entry - single CSV import populates both check-in and audit workflows
- **SC-005**: Reduce data inconsistencies by 90% - device check-in and student tracking remain synchronized
- **SC-006**: CSV import error reporting identifies 100% of invalid rows with specific error messages before committing data
- **SC-007**: Django admin allows tech staff to correct student data errors in under 1 minute per record
- **SC-008**: Check-in status view loads in under 2 seconds for <500 student deployments with full student data visible
- **SC-009**: Device check-in fails gracefully on RT API errors with clear error message (zero partial updates)
- **SC-010**: Re-check-in workflow with confirmation prevents accidental duplicate scans while allowing intentional device exchanges

## Interface Architecture

### Admin Interface (Django Admin - `/admin/`)
**Access**: Technology staff only (via LDAP group Tech-Team)
**Purpose**: Student data management and configuration
**Features**:
- CSV import/export at `/admin/students/student/`
- Manual student record editing
- View associated DeviceInfo records
- View related audit records
- Bulk actions: mark active/inactive, clear check-in status

### End-User Interface (Django Templates)
**Access**: Based on user role (LDAP groups)
**Purpose**: Operational workflows (not administration)

#### Device Check-In Interface (`/devices/check-in`)
- **Access**: Technology staff (LDAP: Tech-Team)
- **Purpose**: Quick device return scanning and student status updates
- **Features**:
  - Asset tag/name input field (keyboard or barcode scanner)
  - Device lookup and display
  - Confirmation of device check-in
  - Student status updated automatically
  - Status messages (success/error)
  - Check-in history/summary
  - Organized similarly to old Flask `/devices/check-in` UI

#### Audit Session Interface (`/audit/`)
- **Access**: Teachers (LDAP: TEACHERS)
- **Purpose**: Device possession verification for advisory classes
- **Features**:
  - View list of audit sessions
  - Create new audit session (auto-populate with students from advisor's class)
  - Mark students as audited (checkbox/button)
  - View completion status and summary
  - Download audit report
  - Organized similarly to old Flask `/devices/audit/` UI

#### Check-In Status Interface (`/students/check-in-status`)
- **Access**: Technology staff (LDAP: Tech-Team)
- **Purpose**: View overall device check-in progress
- **Features**:
  - List all students with check-in status
  - Filter by grade, advisor, is_active status
  - Display device information if checked in
  - Export to CSV
  - Sort by name, grade, advisor
  - Organized similarly to old Flask `/student-devices` UI

## Clarifications

### Session 2025-12-04 (Initial)

- Q: What is the primary student identifier for matching records during CSV import? → A: student_id (numeric SIS ID)
- Q: When a student no longer appears in a new SIS CSV import, what should happen to their existing record? → A: Keep record, mark as "inactive" status (preserve history)
- Q: How should the CSV import handle column name variations? → A: Strict - require exact column names (student_id, first_name, last_name, grade, advisor, username)
- Q: How does the teacher audit workflow select students? → A: Teachers select students from the existing unified Student table (filtered by grade/advisor); no separate CSV upload for audit sessions. AuditStudent records are created by linking to existing Student records.
- Q: What happens when CSV upload contains duplicate student_ids within the same file? → A: Reject the import with an error listing the duplicate student_ids; no partial import occurs.
- Q: What if a student is marked "checked in" but needs to exchange a device (check out new one)? → A: Device checkout clears device_checked_in=False and removes DeviceInfo; new check-in creates fresh record.
- Q: What happens when device is checked in but the student's RT user ID has changed since assignment? → A: Match by current RT asset Owner ID; if no Student has matching rt_user_id, device check-in succeeds but no student update occurs.
- Q: What if audit session contains students not in the main student database? → A: Display warning for unmatched students; only create AuditStudent records for students that exist in unified Student table.

### Session 2025-12-04 (Workflow Clarification)

- Q: What is the expected student dataset size and performance target? → A: Small deployments (<500 students, no pagination required, <2 second load time)
- Q: How should device check-in handle RT API failures? → A: Fail entire check-in - don't update student status or create DeviceInfo if RT fails (strict consistency)
- Q: How should the device check-in interface handle already-checked-in devices? → A: Warn but allow re-check-in with confirmation (handles device exchanges while preventing accidental duplicate scans)
- Q: What data should persist when an audit session is marked complete? → A: Preserve everything - keep AuditSession and all AuditStudent records indefinitely for historical audit trail
- Q: Who can close an audit session and is it per-teacher or global? → A: Only admins can close sessions. Audit sessions are global/shared - multiple teachers complete a single audit session together.
- Q: Relationship between Tech-Team LDAP group and technology staff roles? → A: Tech-Team group = all technology staff with full device check-in + admin access (both `/admin/` and `/devices/check-in`)
