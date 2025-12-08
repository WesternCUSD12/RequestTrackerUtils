from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    # Old Flask-compatible routes
    path('check-in', views.asset_checkin, name='check_in'),
    path('check-in/<str:asset_name>', views.asset_details, name='check_in_asset'),
    path('api/asset/<str:asset_name>', views.get_asset_info, name='asset_info'),
    path('api/update-asset', views.update_asset, name='update_asset'),
    path('checkin-logs', views.checkin_logs, name='logs'),
    path('download-checkin-log/<str:filename>', views.download_checkin_log, name='download_log'),
    path('preview-checkin-log/<str:filename>', views.preview_checkin_log, name='preview_log'),
    
    # Phase 4: Unified Device Check-In (007-unified-student-data)
    path('check-in-unified/', views.device_checkin, name='device_checkin'),
    path('api/check-in', views.device_checkin_api, name='device_checkin_api'),
]
