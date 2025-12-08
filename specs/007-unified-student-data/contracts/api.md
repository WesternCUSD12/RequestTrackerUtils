# API Contracts - Unified Student Data

## Overview

This document defines the API contracts for the unified student data management feature. The primary interface is Django Admin for CSV import; internal APIs support check-in integration and audit workflows.

---

## 1. Django Admin CSV Import Interface

### Import Endpoint (Admin Action)

Django Admin provides built-in import functionality via `django-import-export`.

**Admin URL**: `/admin/students/student/import/`

**Method**: POST (multipart/form-data)

**Required Permissions**: `students.add_student`, `students.change_student`

**CSV Format**:
```csv
student_id,first_name,last_name,grade,advisor,username
12345,John,Doe,9,Smith,jdoe
12346,Jane,Smith,10,Johnson,jsmith
```

**Required Columns** (FR-003):
| Column | Type | Required | Description |
|--------|------|----------|-------------|
| student_id | string | Yes | Primary identifier (SIS ID) |
| first_name | string | Yes | Student's first name |
| last_name | string | Yes | Student's last name |
| grade | integer | Yes | Grade level (K=0, 1-12) |
| advisor | string | Yes | Advisor/homeroom teacher name |
| username | string | Yes | Network/Google username |

**Import Behavior**:
- `student_id` is the unique identifier for upsert operations
- Existing records matched by `student_id` are updated
- New records are created if `student_id` not found
- `is_active` defaults to `True` for new imports
- Students NOT in import file are marked `is_active=False` (FR-004a)

**Response**: Django Admin redirect with success/error message

---

## 2. Student Lookup API (Internal)

Used by device check-in views to find students.

### GET /api/students/lookup/

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | Yes | Search query (student_id, username, or name) |
| active_only | boolean | No | Filter to active students only (default: true) |

**Response** (200 OK):
```json
{
  "students": [
    {
      "id": 1,
      "student_id": "12345",
      "first_name": "John",
      "last_name": "Doe",
      "grade": 9,
      "advisor": "Smith",
      "username": "jdoe",
      "is_active": true,
      "device_checked_in": false,
      "check_in_date": null
    }
  ],
  "count": 1
}
```

**Response** (404 Not Found):
```json
{
  "error": "No students found matching query",
  "query": "q value"
}
```

**Access Control**: Requires authentication, `technology_staff` role

---

## 3. Student Check-In API (Internal)

Used by device check-in workflow to update student device status.

### POST /api/students/{student_id}/checkin/

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| student_id | string | Student's SIS ID |

**Request Body**:
```json
{
  "device_checked_in": true,
  "asset_tag": "CHR-001234"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "student": {
    "student_id": "12345",
    "first_name": "John",
    "last_name": "Doe",
    "device_checked_in": true,
    "check_in_date": "2025-01-15T14:30:00Z"
  }
}
```

**Response** (404 Not Found):
```json
{
  "error": "Student not found",
  "student_id": "12345"
}
```

**Response** (400 Bad Request):
```json
{
  "error": "Student is inactive",
  "student_id": "12345"
}
```

**Access Control**: Requires authentication, `technology_staff` role

---

## 4. Audit Student List API (Internal)

Used by audit views to display students for a session.

### GET /api/audit/sessions/{session_id}/students/

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| session_id | integer | Audit session ID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| grade | integer | No | Filter by grade level |
| advisor | string | No | Filter by advisor name |
| status | string | No | Filter: `verified`, `missing`, `pending` |

**Response** (200 OK):
```json
{
  "session": {
    "id": 1,
    "name": "2025 Device Audit",
    "date": "2025-01-15"
  },
  "students": [
    {
      "audit_student_id": 101,
      "student": {
        "student_id": "12345",
        "first_name": "John",
        "last_name": "Doe",
        "grade": 9,
        "advisor": "Smith"
      },
      "status": "verified",
      "verified_at": "2025-01-15T10:30:00Z",
      "device_records": [
        {
          "asset_tag": "CHR-001234",
          "verified": true
        }
      ]
    }
  ],
  "count": 1
}
```

**Access Control**: Requires authentication, `technology_staff` OR `teacher` role

---

## 5. Model Contracts

### Student Model

```python
class Student(models.Model):
    student_id = models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    grade = models.IntegerField()
    advisor = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    rt_user_id = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    device_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### AuditStudent Model (Updated)

```python
class AuditStudent(models.Model):
    session = models.ForeignKey('AuditSession', on_delete=models.CASCADE)
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('missing', 'Missing'),
    ], default='pending')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
```

---

## 6. Permission Matrix

| Endpoint | technology_staff | teacher | unauthenticated |
|----------|-----------------|---------|-----------------|
| Admin CSV Import | ✅ | ❌ | ❌ |
| Student Lookup | ✅ | ❌ | ❌ |
| Student Check-In | ✅ | ❌ | ❌ |
| Audit Student List | ✅ | ✅ | ❌ |
| Device Check-In Views | ✅ | ❌ | ❌ |

**Note**: Per user requirements, `teacher` role has access to `/audit/*` routes only, not check-in routes.
