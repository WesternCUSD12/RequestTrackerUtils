# Data Model: Unified Student Data Management

**Feature**: 007-unified-student-data  
**Date**: 2025-12-04

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Student                                      │
│  (Central student record - serves check-in AND audit workflows)          │
├─────────────────────────────────────────────────────────────────────────┤
│  student_id       : CharField(20) [PK, from SIS]                         │
│  first_name       : CharField(100)                                       │
│  last_name        : CharField(100)                                       │
│  username         : CharField(100)                                       │
│  grade            : IntegerField                                         │
│  advisor          : CharField(100)                                       │
│  rt_user_id       : IntegerField [nullable, for RT integration]          │
│  is_active        : BooleanField [default=True, for transfer tracking]   │
│  device_checked_in: BooleanField [default=False]                         │
│  check_in_date    : DateTimeField [nullable]                             │
│  created_at       : DateTimeField [auto_now_add]                         │
│  updated_at       : DateTimeField [auto_now]                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:1
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            DeviceInfo                                    │
│  (Device details captured at check-in time)                              │
├─────────────────────────────────────────────────────────────────────────┤
│  id               : AutoField [PK]                                       │
│  student          : OneToOneField(Student) [CASCADE]                     │
│  asset_id         : CharField(50) [RT asset ID]                          │
│  asset_tag        : CharField(50) [e.g., W12-0123]                       │
│  serial_number    : CharField(100)                                       │
│  device_type      : CharField(50) [e.g., Chromebook]                     │
│  check_in_timestamp: DateTimeField                                       │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                          AuditSession                                    │
│  (Teacher-led audit session, unchanged from existing)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  id               : AutoField [PK]                                       │
│  session_id       : UUIDField [unique]                                   │
│  creator_name     : CharField(255)                                       │
│  created_at       : DateTimeField [auto_now_add]                         │
│  status           : CharField [active/completed/cancelled]               │
│  student_count    : IntegerField                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AuditStudent                                    │
│  (Student record within an audit session)                                │
├─────────────────────────────────────────────────────────────────────────┤
│  id               : AutoField [PK]                                       │
│  session          : ForeignKey(AuditSession) [CASCADE]                   │
│  student          : ForeignKey(Student) [SET_NULL, nullable] ← NEW       │
│  name             : CharField(255) [snapshot at audit time]              │
│  grade            : CharField(20) [snapshot]                             │
│  advisor          : CharField(255) [snapshot]                            │
│  username         : CharField(100) [snapshot]                            │
│  audited          : BooleanField [default=False]                         │
│  audit_timestamp  : DateTimeField [nullable]                             │
│  auditor_name     : CharField(255)                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       AuditDeviceRecord                                  │
│  (Device found during audit, unchanged from existing)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  id               : AutoField [PK]                                       │
│  audit_student    : ForeignKey(AuditStudent) [CASCADE]                   │
│  asset_id         : CharField(50)                                        │
│  asset_tag        : CharField(50)                                        │
│  device_type      : CharField(100)                                       │
│  serial_number    : CharField(100)                                       │
│  verified         : BooleanField [default=False]                         │
│  verification_timestamp: DateTimeField [nullable]                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## Django Models

### Student Model (apps/students/models.py)

```python
from django.db import models


class Student(models.Model):
    """
    Unified student record for device check-in and audit workflows.
    Primary key is student_id from SIS (not auto-generated).
    """
    student_id = models.CharField(max_length=20, primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, db_index=True)
    grade = models.IntegerField(default=0)
    advisor = models.CharField(max_length=100, blank=True)
    rt_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    device_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['grade', 'is_active']),
            models.Index(fields=['advisor', 'is_active']),
            models.Index(fields=['device_checked_in', 'is_active']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.student_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class DeviceInfo(models.Model):
    """Device details captured when student checks in device."""
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name='device_info'
    )
    asset_id = models.CharField(max_length=50)
    asset_tag = models.CharField(max_length=50)
    serial_number = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    check_in_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_device_info'
        verbose_name = 'Device Info'
        verbose_name_plural = 'Device Info'

    def __str__(self):
        return f"{self.asset_tag} ({self.device_type})"
```

### AuditStudent Model Update (apps/audit/models.py)

```python
# Add to existing AuditStudent model:
from apps.students.models import Student

class AuditStudent(models.Model):
    # ... existing fields ...
    
    # NEW: Optional link to unified Student table
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_records'
    )
```

## CSV Import Format

### Required Columns (exact names, order flexible)

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| student_id | string | YES | SIS student ID (primary key) |
| first_name | string | YES | Student first name |
| last_name | string | YES | Student last name |
| grade | integer | YES | Grade level (0-12) |
| advisor | string | NO | Advisor/homeroom teacher name |
| username | string | YES | Login username (e.g., jsmith2028) |

### Example CSV

```csv
student_id,first_name,last_name,grade,advisor,username
12345,John,Smith,9,Ms. Johnson,jsmith2028
12346,Jane,Doe,10,Mr. Williams,jdoe2027
12347,Bob,Wilson,9,Ms. Johnson,bwilson2028
```

## Validation Rules

1. **student_id**: Required, unique, max 20 characters
2. **first_name**: Required, max 100 characters
3. **last_name**: Required, max 100 characters
4. **username**: Required, max 100 characters
5. **grade**: Required, integer 0-12
6. **advisor**: Optional, max 100 characters

## Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| students | student_id (PK) | Primary lookup |
| students | username | Login/search |
| students | rt_user_id | Device check-in integration |
| students | (grade, is_active) | Admin filtering |
| students | (advisor, is_active) | Admin filtering |
| students | (device_checked_in, is_active) | Status reports |
