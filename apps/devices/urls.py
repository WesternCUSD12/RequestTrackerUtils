from django.urls import path
from . import views

app_name = 'devices'

urlpatterns = [
    path('check-in', views.asset_checkin, name='check_in'),
    path('check-in/<str:asset_name>', views.asset_details, name='check_in_asset'),
    path('api/asset/<str:asset_name>', views.get_asset_info, name='asset_info'),
    path('api/update-asset', views.update_asset, name='update_asset'),
    path('checkin-logs', views.checkin_logs, name='logs'),
    path('download-checkin-log/<str:filename>', views.download_log, name='download_log'),
    path('preview-checkin-log/<str:filename>', views.preview_log, name='preview_log'),
]
