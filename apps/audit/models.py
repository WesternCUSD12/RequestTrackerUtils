from django.db import models
import uuid


class AuditSession(models.Model):
    """Audit session for device verification."""

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    session_id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=False)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='audit_sessions',
        null=True,
        blank=True,
        help_text="Teacher or admin who created the session"
    )
    creator_name = models.CharField(max_length=255)  # Denormalized for display
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    student_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'audit_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Audit {self.session_id} ({self.status})"
    
    @property
    def is_closed(self):
        """Check if session is closed"""
        return self.status == 'closed'


class AuditStudent(models.Model):
    """Student in an audit session. References unified Student table for core data."""

    session = models.ForeignKey(
        AuditSession,
        on_delete=models.CASCADE,
        related_name='students',
        to_field='session_id'
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_records'
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

