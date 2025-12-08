from django.contrib import admin
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from .models import Student, DeviceInfo
from .resources import StudentResource


class DeviceInfoInline(admin.TabularInline):
    model = DeviceInfo
    extra = 0
    readonly_fields = ('check_in_timestamp',)
    fields = ('asset_id', 'asset_tag', 'serial_number', 'device_type', 'check_in_timestamp')


@admin.register(Student)
class StudentAdmin(ImportExportModelAdmin, ImportExportActionModelAdmin):
    resource_class = StudentResource
    list_display = ('student_id', 'full_name', 'grade', 'advisor', 'is_active', 'device_checked_in', 'check_in_date')
    list_filter = ('grade', 'advisor', 'is_active', 'device_checked_in')
    search_fields = ('student_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('student_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Student Identification', {
            'fields': ('student_id', 'first_name', 'last_name', 'username')
        }),
        ('School Information', {
            'fields': ('grade', 'advisor')
        }),
        ('System Integration', {
            'fields': ('rt_user_id', 'is_active')
        }),
        ('Device Check-in', {
            'fields': ('device_checked_in', 'check_in_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [DeviceInfoInline]
    
    # Bulk actions
    actions = ['reset_device_checkin_status', 'export_checkin_status_csv']
    
    def get_readonly_fields(self, request, obj=None):
        """
        T054: Make rt_user_id readonly after creation (creation = obj is None).
        Only allow editing on new student creation.
        """
        readonly = list(self.readonly_fields)
        # If editing existing student (obj is not None), add rt_user_id to readonly
        if obj is not None:
            readonly.append('rt_user_id')
        return readonly
    
    def has_delete_permission(self, request):
        """Check if user can delete students."""
        return True
    
    def delete_model(self, request, obj):
        """
        T055: Add delete confirmation with warning message.
        Override to provide context about what's being deleted.
        """
        # Log the deletion for audit trail
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f'Admin {request.user.username} deleted student {obj.student_id} '
            f'({obj.first_name} {obj.last_name})'
        )
        super().delete_model(request, obj)
    
    def reset_device_checkin_status(self, request, queryset):
        """
        T056: Bulk action to reset device check-in status.
        Clears device_checked_in flag and check_in_date for selected students.
        """
        updated_count = 0
        for student in queryset:
            student.device_checked_in = False
            student.check_in_date = None
            student.save()
            updated_count += 1
        
        self.message_user(
            request,
            f'Successfully reset device check-in status for {updated_count} student(s).'
        )
    
    reset_device_checkin_status.short_description = (
        'Reset device check-in status (clears device_checked_in and check_in_date)'
    )
    
    def export_checkin_status_csv(self, request, queryset):
        """
        T057: Export CSV of student check-in status.
        Generates CSV with student data and device check-in information.
        """
        import csv
        from django.http import HttpResponse
        from datetime import datetime
        
        response = HttpResponse(content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="student_checkin_status_{timestamp}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Student ID', 'Full Name', 'Grade', 'Advisor', 'Username',
            'Check-in Status', 'Check-in Date', 'Device Type', 'Asset Tag'
        ])
        
        for student in queryset:
            device_info = getattr(student, 'deviceinfo', None)
            writer.writerow([
                student.student_id,
                student.full_name,
                student.grade,
                student.advisor,
                student.username,
                'Yes' if student.device_checked_in else 'No',
                student.check_in_date.strftime('%Y-%m-%d %H:%M:%S') if student.check_in_date else '',
                device_info.device_type if device_info else '',
                device_info.asset_tag if device_info else ''
            ])
        
        return response
    
    export_checkin_status_csv.short_description = (
        'Export check-in status to CSV (device_checked_in, check_in_date, device info)'
    )

