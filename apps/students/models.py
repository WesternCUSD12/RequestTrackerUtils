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

