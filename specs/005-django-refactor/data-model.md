# Data Model: Django Application Refactor

**Feature**: 005-django-refactor  
**Date**: 2025-12-01  
**Status**: Complete

---

## Entity Overview

| Entity            | Django App | Table Name           | Description                          |
| ----------------- | ---------- | -------------------- | ------------------------------------ |
| Student           | students   | students             | Student records with RT user mapping |
| DeviceInfo        | devices    | device_info          | Devices assigned to students         |
| DeviceLog         | devices    | device_logs          | Device check-in activity logs        |
| AuditSession      | audit      | audit_sessions       | Audit session metadata               |
| AuditStudent      | audit      | audit_students       | Students in an audit session         |
| AuditDeviceRecord | audit      | audit_device_records | Device records during audit          |
| AuditNote         | audit      | audit_notes          | Notes captured during audit          |

---

## Django Models

### students/models.py

```python
from django.db import models

class Student(models.Model):
    """Student record with RT user mapping and device check-in status."""

    name = models.CharField(max_length=255)
    grade = models.IntegerField(default=0)
    rt_user_id = models.IntegerField(null=True, blank=True)
    device_checked_in = models.BooleanField(default=False)
    check_in_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'students'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Grade {self.grade})"
```

### devices/models.py

```python
from django.db import models

class DeviceInfo(models.Model):
    """Device assigned to a student."""

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='devices'
    )
    asset_id = models.CharField(max_length=50)
    asset_tag = models.CharField(max_length=50)
    device_type = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    check_in_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'device_info'
        verbose_name_plural = 'Device info'

    def __str__(self):
        return f"{self.asset_tag} ({self.device_type})"


class DeviceLog(models.Model):
    """Device check-in activity log entry."""

    timestamp = models.DateTimeField(auto_now_add=True)
    asset_id = models.CharField(max_length=50)
    asset_tag = models.CharField(max_length=50)
    device_type = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    previous_owner = models.CharField(max_length=255, blank=True)
    student_name = models.CharField(max_length=255)
    ticket_id = models.CharField(max_length=50, blank=True)
    needs_repair = models.BooleanField(default=False)
    missing_charger = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'device_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.asset_tag} - {self.student_name} ({self.timestamp})"
```

### audit/models.py

```python
from django.db import models
import uuid

class AuditSession(models.Model):
    """Audit session for device verification."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    creator_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    student_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'audit_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit {self.session_id} ({self.status})"


class AuditStudent(models.Model):
    """Student in an audit session."""

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name='students',
        to_field='session_id'
    )
    name = models.CharField(max_length=255)
    grade = models.CharField(max_length=20, blank=True)
    advisor = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=100, blank=True)
    audited = models.BooleanField(default=False)
    audit_timestamp = models.DateTimeField(null=True, blank=True)
    auditor_name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'audit_students'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {'Audited' if self.audited else 'Pending'}"


class AuditDeviceRecord(models.Model):
    """Device record found during audit verification."""

    audit_student = models.ForeignKey(
        AuditStudent,
        on_delete=models.CASCADE,
        related_name='device_records'
    )
    asset_id = models.CharField(max_length=50)
    asset_tag = models.CharField(max_length=50)
    device_type = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    verified = models.BooleanField(default=False)
    verification_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'audit_device_records'

    def __str__(self):
        return f"{self.asset_tag} - {'Verified' if self.verified else 'Unverified'}"


class AuditNote(models.Model):
    """Note captured during audit session."""

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name='notes',
        to_field='session_id'
    )
    audit_student = models.ForeignKey(
        AuditStudent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes'
    )
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    creator_name = models.CharField(max_length=255)

    class Meta:
        db_table = 'audit_notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.creator_name} ({self.created_at})"
```

---

## Migration Strategy

**Approach**: Fresh database creation (no Flask data migration required)

### Step 1: Create Models in App-Specific Files

Create models in each app's `models.py` as defined above:
- `apps/students/models.py` - Student
- `apps/devices/models.py` - DeviceInfo, DeviceLog  
- `apps/audit/models.py` - AuditSession, AuditStudent, AuditDeviceRecord, AuditNote

### Step 2: Generate Migrations

```bash
python manage.py makemigrations students
python manage.py makemigrations devices
python manage.py makemigrations audit
```

### Step 3: Apply Migrations

```bash
python manage.py migrate
```

This creates fresh database tables. No data migration from Flask is required.

---

## Validation Rules

| Entity         | Field         | Validation              |
| -------------- | ------------- | ----------------------- |
| Student        | name          | Required, max 255 chars |
| Student        | grade         | Integer 0-12            |
| DeviceInfo     | serial_number | Unique per device_type  |
| AuditSession   | session_id    | UUID, unique            |
| AuditStudent   | username      | Optional, for RT lookup |
| All timestamps |               | UTC timezone            |

---

## State Transitions

### AuditSession.status

```
active → completed  (all students audited)
active → cancelled  (session abandoned)
```

### AuditStudent.audited

```
False → True  (device verification complete)
True → False  (re-audit requested)
```

---

## Django Admin Registration

```python
# students/admin.py
from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade', 'device_checked_in', 'check_in_date']
    list_filter = ['grade', 'device_checked_in']
    search_fields = ['name']


# devices/admin.py
from django.contrib import admin
from .models import DeviceInfo, DeviceLog

@admin.register(DeviceInfo)
class DeviceInfoAdmin(admin.ModelAdmin):
    list_display = ['asset_tag', 'device_type', 'student', 'check_in_timestamp']
    list_filter = ['device_type']
    search_fields = ['asset_tag', 'serial_number']

@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'asset_tag', 'student_name', 'device_type']
    list_filter = ['device_type', 'needs_repair', 'missing_charger']
    search_fields = ['asset_tag', 'student_name']
    date_hierarchy = 'timestamp'


# audit/admin.py
from django.contrib import admin
from .models import AuditSession, AuditStudent, AuditDeviceRecord, AuditNote

@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'creator_name', 'status', 'student_count', 'created_at']
    list_filter = ['status']
    search_fields = ['creator_name']

@admin.register(AuditStudent)
class AuditStudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade', 'advisor', 'audited', 'auditor_name']
    list_filter = ['audited', 'grade']
    search_fields = ['name', 'username']

@admin.register(AuditDeviceRecord)
class AuditDeviceRecordAdmin(admin.ModelAdmin):
    list_display = ['asset_tag', 'device_type', 'verified']
    list_filter = ['verified', 'device_type']

@admin.register(AuditNote)
class AuditNoteAdmin(admin.ModelAdmin):
    list_display = ['creator_name', 'created_at', 'note_text']
    search_fields = ['note_text', 'creator_name']
```
