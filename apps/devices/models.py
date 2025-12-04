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

