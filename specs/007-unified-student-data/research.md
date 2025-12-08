# Research: Unified Student Data Management

**Feature**: 007-unified-student-data  
**Date**: 2025-12-04

## Research Questions Resolved

### Q1: What is the best approach for CSV import in Django admin?

**Decision**: Use `django-import-export` library

**Rationale**: 
- Mature, well-maintained library specifically designed for Django admin CSV/Excel import/export
- Provides transaction support (all-or-nothing imports)
- Built-in duplicate handling via `import_id_fields`
- Customizable validation with clear error reporting
- No custom admin views needed - integrates seamlessly

**Alternatives Considered**:
- Custom admin action with CSV parsing: More work, less robust error handling
- django-csvimport: Less active development, fewer features
- Manual management command: Not user-friendly for admin staff

### Q2: How should the unified Student model relate to AuditStudent?

**Decision**: AuditStudent has optional ForeignKey to Student (null=True)

**Rationale**:
- Allows audit sessions to be created for students not yet in main table
- Preserves audit history even if Student record is modified/deleted
- AuditStudent stores snapshot of student data at audit time (name, grade, advisor)
- ForeignKey enables lookups but doesn't create hard dependency

**Alternatives Considered**:
- Required ForeignKey: Would block audit imports for students not in system
- No relationship: Would lose ability to cross-reference audit with check-in data
- Through table: Unnecessary complexity for this use case

### Q3: How to handle the "mark inactive" requirement for transferred students?

**Decision**: Add `is_active` boolean field with CSV import callback

**Rationale**:
- Simple boolean is sufficient (no complex status workflow needed)
- Import callback marks all students not in CSV as inactive
- Default to `is_active=True` for new imports
- Admin can filter by active/inactive status
- Preserves historical data for device check-in records

**Implementation**:
```python
class StudentResource(resources.ModelResource):
    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        # Mark all students as inactive before import
        if not dry_run:
            Student.objects.all().update(is_active=False)
    
    def after_save_instance(self, instance, using_transactions, dry_run):
        # Students in CSV are automatically active
        instance.is_active = True
        instance.save()
```

### Q4: What device details should be stored with student check-in?

**Decision**: Create DeviceInfo model with one-to-one relationship to Student

**Rationale**:
- Keeps Student model clean (focused on student identity)
- Device details are optional (student may not have device)
- Allows easy clearing/updating when device changes
- Stores: asset_id, asset_tag, serial_number, device_type, check_in_timestamp

**Fields from RT Custom Fields**:
- `asset_id`: RT asset ID (for API lookups)
- `asset_tag`: RT asset Name field (e.g., "W12-0123")
- `serial_number`: From CustomFields "Serial Number"
- `device_type`: From CustomFields "Type" (e.g., "Chromebook")

### Q5: How should device check-in integration work?

**Decision**: Lookup by rt_user_id from RT asset owner

**Rationale**:
- RT assets have an Owner field containing RT user ID
- Student.rt_user_id maps to RT user
- When device checked in, lookup student by RT user ID match
- If match found, update student's device_checked_in and create DeviceInfo

**Flow**:
1. Device scanned → RT API returns asset with Owner ID
2. Query: `Student.objects.filter(rt_user_id=owner_id).first()`
3. If found: Set `device_checked_in=True`, create/update DeviceInfo
4. If not found: Continue device check-in without student update

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| CSV Import | django-import-export | Best Django admin integration, validation, transactions |
| Student-Device relation | One-to-One (DeviceInfo) | Clean separation, optional device data |
| Audit-Student relation | Optional FK | Flexibility for audit imports |
| Inactive tracking | Boolean field | Simple, sufficient for use case |
| Admin filtering | list_filter + search_fields | Built-in Django admin features |

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    ...
    "django-import-export>=3.3.0",
]
```

## Database Schema Summary

```
Student (unified table)
├── student_id (PK, from SIS)
├── first_name, last_name
├── username
├── grade (integer)
├── advisor
├── rt_user_id (for RT integration)
├── is_active (for transfer tracking)
├── device_checked_in (boolean)
└── check_in_date (datetime)

DeviceInfo (one-to-one with Student)
├── student (FK to Student)
├── asset_id, asset_tag
├── serial_number, device_type
└── check_in_timestamp

AuditStudent (modified)
├── session (FK to AuditSession)
├── student (optional FK to Student) ← NEW
├── name, grade, advisor, username (snapshot)
├── audited, audit_timestamp, auditor_name
└── ... existing fields
```
