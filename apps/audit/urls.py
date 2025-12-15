"""
URL configuration for audit views.

Phase 5: Teacher Device Audit Sessions
"""

from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    # T034: Session list view
    path("", views.audit_list, name="session_list"),
    # Create new session (admin only)
    path("create/", views.create_session, name="create_session"),
    # T035: Session detail view with student list
    path(
        "session/<str:session_id>/", views.audit_session_detail, name="session_detail"
    ),
    # T036: Mark student as audited API endpoint
    path("api/mark-audited/<str:session_id>/", views.mark_audited, name="mark_audited"),
    # Rename session API endpoint (admin only)
    path(
        "api/rename-session/<str:session_id>/",
        views.rename_session,
        name="rename_session",
    ),
    # Delete session API endpoint (admin only)
    path(
        "api/delete-session/<str:session_id>/",
        views.delete_session,
        name="delete_session",
    ),
    # T038: Close session API endpoint (admin only)
    path(
        "api/close-session/<str:session_id>/", views.close_session, name="close_session"
    ),
    # T052: Export audit results to CSV
    path(
        "session/<str:session_id>/export-csv/",
        views.export_session_csv,
        name="export_session_csv",
    ),
    # Device audit endpoints
    path(
        "api/device/<str:session_id>/<int:student_id>/<int:device_id>/save/",
        views.save_device_audit,
        name="save_device_audit",
    ),
    path(
        "api/student/<str:session_id>/<int:student_id>/complete/",
        views.mark_student_completed,
        name="mark_student_completed",
    ),
    path(
        "api/student/<str:session_id>/<int:audit_student_id>/devices/",
        views.get_audit_student_devices,
        name="get_audit_student_devices",
    ),
    path(
        "api/lock-session/<str:session_id>/",
        views.lock_audit_session,
        name="lock_audit_session",
    ),
    path(
        "api/prefetch-devices/<str:session_id>/",
        views.prefetch_session_devices_manual,
        name="prefetch_devices",
    ),
    # Async prefetch start
    path(
        "api/prefetch-devices-async/<str:session_id>/",
        views.prefetch_session_devices_async,
        name="prefetch_devices_async",
    ),
    # Prefetch job status
    path(
        "api/prefetch-status/<str:job_id>/",
        views.prefetch_status,
        name="prefetch_status",
    ),
    path(
        "api/lookup-device/<str:asset_id>/",
        views.lookup_device_owner,
        name="lookup_device_owner",
    ),
]
