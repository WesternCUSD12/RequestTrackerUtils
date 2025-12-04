from django.contrib import admin
from .models import AuditSession, AuditStudent, AuditDeviceRecord, AuditNote


@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'created_at', 'creator_name', 'student_count', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('session_id', 'creator_name')
    readonly_fields = ('session_id', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(AuditStudent)
class AuditStudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'session', 'grade', 'audited', 'audit_timestamp')
    list_filter = ('audited', 'grade', 'session')
    search_fields = ('name', 'username', 'advisor')
    readonly_fields = ('audit_timestamp',)
    fieldsets = (
        ('Student Information', {
            'fields': ('name', 'grade', 'advisor', 'username')
        }),
        ('Audit Status', {
            'fields': ('session', 'audited', 'audit_timestamp', 'auditor_name')
        }),
    )


@admin.register(AuditDeviceRecord)
class AuditDeviceRecordAdmin(admin.ModelAdmin):
    list_display = ('asset_id', 'audit_student', 'device_type', 'serial_number', 'verified', 'verification_timestamp')
    list_filter = ('device_type', 'verified', 'verification_timestamp')
    search_fields = ('asset_id', 'asset_tag', 'serial_number')
    readonly_fields = ('verification_timestamp',)
    date_hierarchy = 'verification_timestamp'


@admin.register(AuditNote)
class AuditNoteAdmin(admin.ModelAdmin):
    list_display = ('audit_student', 'creator_name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('audit_student__name', 'note_text', 'creator_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Note Information', {
            'fields': ('audit_student', 'session', 'note_text')
        }),
        ('Metadata', {
            'fields': ('creator_name', 'created_at')
        }),
    )
