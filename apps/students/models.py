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
        return f"{self.student.full_name} - {self.asset_tag}"
