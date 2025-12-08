"""
URL configuration for audit views.

Phase 5: Teacher Device Audit Sessions
"""
from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    # T034: Session list view
    path('', views.audit_list, name='session_list'),
    
    # Create new session (admin only)
    path('create/', views.create_session, name='create_session'),
    
    # T035: Session detail view with student list
    path('session/<str:session_id>/', views.audit_session_detail, name='session_detail'),
    
    # T036: Mark student as audited API endpoint
    path('api/mark-audited/<str:session_id>/', views.mark_audited, name='mark_audited'),
    
    # Rename session API endpoint (admin only)
    path('api/rename-session/<str:session_id>/', views.rename_session, name='rename_session'),
    
    # Delete session API endpoint (admin only)
    path('api/delete-session/<str:session_id>/', views.delete_session, name='delete_session'),
    
    # T038: Close session API endpoint (admin only)
    path('api/close-session/<str:session_id>/', views.close_session, name='close_session'),
    
    # T052: Export audit results to CSV
    path('session/<str:session_id>/export-csv/', views.export_session_csv, name='export_session_csv'),
]
