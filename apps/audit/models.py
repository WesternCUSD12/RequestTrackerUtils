from django.db import models
import uuid


class AuditSession(models.Model):
    """Audit session for device verification."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=False)
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="audit_sessions",
        null=True,
        blank=True,
        help_text="Teacher or admin who created the session",
    )
    creator_name = models.CharField(max_length=255)  # Denormalized for display
    # Human-friendly session name for teachers/admins to see instead of raw UUID
    name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    student_count = models.IntegerField(default=0)

    class Meta:
        db_table = "audit_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        if self.name:
            return f"{self.name} ({self.status})"
        return f"Audit {self.session_id} ({self.status})"

    @property
    def is_closed(self):
        """Check if session is closed"""
        return self.status == "closed"


class AuditStudent(models.Model):
    """Student in an audit session. References unified Student table for core data."""

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="students",
        to_field="session_id",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_records",
    )
    name = models.CharField(max_length=255)
    grade = models.CharField(max_length=20, blank=True)
    advisor = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=100, blank=True)
    audited = models.BooleanField(default=False)
    audit_timestamp = models.DateTimeField(null=True, blank=True)
    auditor_name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "audit_students"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - {'Audited' if self.audited else 'Pending'}"


class AuditDeviceRecord(models.Model):
    """Device record found during audit verification."""

    AUDIT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("correct", "Correct"),
        ("extra", "Extra Device"),
        ("other", "Other"),
    ]

    audit_student = models.ForeignKey(
        AuditStudent, on_delete=models.CASCADE, related_name="device_records"
    )
    asset_id = models.CharField(max_length=50)
    asset_tag = models.CharField(max_length=50)
    asset_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=100)
    model_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    audit_status = models.CharField(
        max_length=20, choices=AUDIT_STATUS_CHOICES, default="pending"
    )
    audit_notes = models.TextField(
        blank=True, help_text="Notes about device condition or discrepancies"
    )
    verified = models.BooleanField(default=False)
    verification_timestamp = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "audit_device_records"

    def __str__(self):
        return f"{self.asset_tag} - {self.audit_status}"


class AuditNote(models.Model):
    """Note captured during audit session."""

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="notes",
        to_field="session_id",
    )
    audit_student = models.ForeignKey(
        AuditStudent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    note_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    creator_name = models.CharField(max_length=255)

    class Meta:
        db_table = "audit_notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.creator_name} ({self.created_at})"


class AuditChangeLog(models.Model):
    """Track all changes made during audit sessions for compliance and transparency."""

    ACTION_CHOICES = [
        ("device_status_changed", "Device Status Changed"),
        ("device_notes_added", "Device Notes Added"),
        ("device_notes_updated", "Device Notes Updated"),
        ("student_audit_completed", "Student Audit Completed"),
        ("session_locked", "Session Locked"),
        ("session_unlocked", "Session Unlocked"),
    ]

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name="change_logs",
        to_field="session_id",
    )
    audit_student = models.ForeignKey(
        AuditStudent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs",
    )
    device_record = models.ForeignKey(
        AuditDeviceRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs",
    )
    user_name = models.CharField(
        max_length=255, help_text="Teacher or admin who made the change"
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    device_info = models.CharField(
        max_length=255, blank=True, help_text="Device asset ID/tag for quick reference"
    )
    old_value = models.TextField(blank=True, help_text="Previous value")
    new_value = models.TextField(blank=True, help_text="New value")
    notes = models.TextField(
        blank=True, help_text="Additional context about the change"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_change_logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["session", "-timestamp"]),
            models.Index(fields=["audit_student", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.user_name} ({self.timestamp})"
