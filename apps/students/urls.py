from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('student-devices', views.student_devices, name='devices'),
    path('import', views.import_students, name='import'),
    
    # Phase 4: Unified Device Check-In (007-unified-student-data)
    path('check-in-status/', views.checkin_status, name='checkin_status'),
]
