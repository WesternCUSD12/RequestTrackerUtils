"""
URL configuration for the audit app
"""
from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.audit_home, name='home'),
    path('upload', views.upload_csv, name='upload'),
    path('session/<str:session_id>', views.view_session, name='session'),
    path('session/<str:session_id>/students', views.session_students, name='students'),
    path('student/<int:student_id>', views.student_detail, name='student'),
    path('student/<int:student_id>/devices', views.student_devices, name='devices'),
    path('student/<int:student_id>/verify', views.verify_student, name='verify'),
    path('student/<int:student_id>/re-audit', views.re_audit_student, name='re_audit'),
    path('session/<str:session_id>/completed', views.completed_students, name='completed'),
    path('notes', views.audit_notes, name='notes'),
    path('notes/export', views.export_notes, name='export'),
    path('clear', views.clear_audit, name='clear'),
]
