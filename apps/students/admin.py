from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'grade', 'rt_user_id', 'device_checked_in', 'check_in_date')
    list_filter = ('grade', 'device_checked_in')
    search_fields = ('id', 'name', 'rt_user_id')
    readonly_fields = ('check_in_date',)
    fieldsets = (
        ('Student Information', {
            'fields': ('name', 'grade', 'rt_user_id')
        }),
        ('Device Check-in', {
            'fields': ('device_checked_in', 'check_in_date')
        }),
    )
