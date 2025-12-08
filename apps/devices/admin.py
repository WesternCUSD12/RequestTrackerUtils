from django.contrib import admin
from .models import DeviceLog


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ('asset_id', 'asset_tag', 'timestamp', 'student_name', 'needs_repair')
    list_filter = ('needs_repair', 'missing_charger', 'timestamp')
    search_fields = ('asset_id', 'asset_tag', 'student_name')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    fieldsets = (
        ('Log Entry', {
            'fields': ('asset_id', 'asset_tag', 'device_type', 'serial_number', 'timestamp')
        }),
        ('Student & Status', {
            'fields': ('student_name', 'previous_owner', 'ticket_id')
        }),
        ('Condition', {
            'fields': ('needs_repair', 'missing_charger', 'notes')
        }),
    )
