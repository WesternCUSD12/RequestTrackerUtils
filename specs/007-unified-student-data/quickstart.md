# Quickstart Guide - Unified Student Data

## Prerequisites

- Python 3.11+
- Django 4.2+
- devenv/Nix environment (optional but recommended)

## Development Setup

### 1. Environment Setup

```bash
# Using devenv (recommended)
cd /path/to/RequestTrackerUtils
devenv shell

# Or using venv
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Install Dependencies

```bash
pip install django-import-export
```

Add to `INSTALLED_APPS` in `rtutils/settings.py`:
```python
INSTALLED_APPS = [
    ...
    'import_export',
    ...
]
```

### 3. Create Migrations

Since no existing data needs preservation (per requirements), we can safely recreate tables:

```bash
# Remove old migrations (if any conflicts)
rm -f apps/students/migrations/000*.py
rm -f apps/audit/migrations/000*.py

# Create fresh migrations
python manage.py makemigrations students
python manage.py makemigrations audit

# Apply migrations
python manage.py migrate
```

### 4. Create Superuser (if needed)

```bash
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

Access:
- Admin: http://localhost:8000/admin/
- Application: http://localhost:8000/

---

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Modules

```bash
# Unit tests for students app
pytest tests/unit/test_student_model.py

# Integration tests for CSV import
pytest tests/integration/test_csv_import.py

# Audit integration tests
pytest tests/integration/test_audit_workflow.py
```

### Test Coverage

```bash
pytest --cov=apps/students --cov=apps/audit --cov-report=html
```

---

## CSV Import Testing

### 1. Create Test CSV

Create `test_students.csv`:
```csv
student_id,first_name,last_name,grade,advisor,username
TEST001,Test,Student,9,TestAdvisor,tstudent
TEST002,Demo,User,10,TestAdvisor,duser
```

### 2. Import via Admin

1. Navigate to http://localhost:8000/admin/students/student/
2. Click "Import" button
3. Select CSV file
4. Preview changes
5. Confirm import

### 3. Verify Import

```bash
python manage.py shell
```

```python
from apps.students.models import Student
Student.objects.filter(student_id__startswith='TEST').values()
```

---

## Feature Verification Checklist

### CSV Import (FR-001 to FR-005)
- [ ] CSV upload via Django Admin works
- [ ] Required columns validated
- [ ] Upsert by student_id works
- [ ] Missing students marked inactive
- [ ] Import summary shows counts

### Check-In Integration (FR-006 to FR-008)
- [ ] Student lookup finds by student_id/username
- [ ] Check-in updates device_checked_in flag
- [ ] Check-in updates check_in_date timestamp

### Audit Integration (FR-009 to FR-011)
- [ ] Audit sessions use unified Student data
- [ ] No duplicate student records created
- [ ] Changes reflect immediately in audit view

### Access Control (FR-012 to FR-015)
- [ ] technology_staff can access all routes
- [ ] teacher can access /audit/* only
- [ ] teacher cannot access check-in routes
- [ ] Admin can edit individual students

---

## Troubleshooting

### Migration Conflicts

If you encounter migration conflicts:
```bash
# Reset migrations for affected apps
python manage.py migrate students zero
python manage.py migrate audit zero

# Recreate and apply
python manage.py makemigrations students audit
python manage.py migrate
```

### Import-Export Not Showing

Ensure `import_export` is in `INSTALLED_APPS` and the `StudentResource` class is defined in `apps/students/admin.py`.

### LDAP Authentication Issues

See `specs/006-ldap-auth/` for LDAP configuration details.

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/students/models.py` | Unified Student model |
| `apps/students/admin.py` | Admin with import-export |
| `apps/students/resources.py` | Import-export resource config |
| `apps/audit/models.py` | AuditStudent FK to Student |
| `apps/devices/views.py` | Check-in integration |
| `rtutils/settings.py` | Role access rules |
