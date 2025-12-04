from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('student-devices', views.student_devices, name='devices'),
    path('import', views.import_students, name='import'),
]
