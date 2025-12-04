from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_http_methods
from apps.students.models import Student
import logging

logger = logging.getLogger(__name__)


def student_devices(request):
    """Display student device lookup page"""
    return render(request, 'students/student_devices.html')


def import_students(request):
    """Import students from CSV file"""
    if request.method == 'GET':
        return render(request, 'students/student_import.html')
    
    # POST handling - import students from uploaded CSV
    if request.method == 'POST':
        # TODO: Implement CSV import logic
        return JsonResponse({'status': 'not implemented'}, status=501)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
