from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from apps.students.models import Student, DeviceInfo
import logging

logger = logging.getLogger(__name__)



def student_devices(request):
    """Display student device lookup page"""
    return render(request, 'students/student_devices.html')


def import_students(request):
    """
    ⚠️ DEPRECATED: Student CSV import has been migrated to Django admin.
    
    Feature 007-unified-student-data uses django-import-export via the Django admin
    at /admin/students/student/import/ for CSV imports.
    
    This view is retained for backwards compatibility only.
    """
    return JsonResponse(
        {
            'error': 'CSV import has been moved to Django admin',
            'redirect': '/admin/students/student/import/',
            'message': 'Please use the Django admin interface to import students.'
        },
        status=410  # 410 Gone - resource no longer available
    )


def find_student_by_rt_user(rt_user_id):
    """
    Find a student by their RT user ID.
    
    Used during device check-in to match device owner to student record.
    Returns the Student object if found, None otherwise.
    
    Args:
        rt_user_id (int): RT user ID to search for
        
    Returns:
        Student or None: Student record if found and active, None otherwise
    """
    if not rt_user_id:
        return None
    
    try:
        student = Student.objects.filter(
            rt_user_id=rt_user_id,
            is_active=True  # Only return active students
        ).first()
        return student
    except Exception as e:
        logger.error(f"Error looking up student by RT user {rt_user_id}: {str(e)}")
        return None


def update_student_checkin(student, asset_id, asset_tag, serial_number, device_type):
    """
    Update student record when device is checked in.
    
    Sets device_checked_in=True, updates check_in_date, and creates/updates DeviceInfo.
    
    Args:
        student (Student): Student object to update
        asset_id (str): RT asset ID
        asset_tag (str): Asset tag (e.g., W12-0123)
        serial_number (str): Device serial number
        device_type (str): Device type (e.g., Chromebook)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Update student status
        student.device_checked_in = True
        student.check_in_date = timezone.now()
        student.save()
        
        # Create or update DeviceInfo
        device_info, created = DeviceInfo.objects.update_or_create(
            student=student,
            defaults={
                'asset_id': asset_id,
                'asset_tag': asset_tag,
                'serial_number': serial_number,
                'device_type': device_type,
            }
        )
        
        logger.info(
            f"Student {student.student_id} ({student.full_name}) checked in device "
            f"{asset_tag} (created={created})"
        )
        return True
        
    except Exception as e:
        logger.error(f"Error updating student checkin for {student.student_id}: {str(e)}")
        return False


def checkin_status(request):
    """
    Device check-in status dashboard for tech staff.
    
    Shows summary cards (total, checked in %, pending %) and filterable student list.
    
    Requirements:
    - FR-009: Status dashboard with summary
    - FR-016: <2s load time for <500 students, no pagination
    - Filters: grade, search by name/ID
    
    Query parameters:
    - grade: Filter by grade (optional)
    - search: Search by student ID or name (optional)
    - sort: Sort by field (optional, default: last_name)
    """
    # Get all students
    queryset = Student.objects.all().select_related('device_info')
    
    # Apply grade filter if provided
    grade = request.GET.get('grade')
    if grade and grade != '':
        try:
            grade = int(grade)
            queryset = queryset.filter(grade=grade)
        except (ValueError, TypeError):
            pass
    
    # Apply search filter if provided
    search_term = request.GET.get('search', '').strip()
    if search_term:
        queryset = queryset.filter(
            Q(student_id__icontains=search_term) |
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(username__icontains=search_term)
        )
    
    # Apply sorting
    sort_field = request.GET.get('sort', 'last_name')
    allowed_sorts = ['student_id', 'first_name', 'last_name', 'grade', 'device_checked_in', 'check_in_date']
    if sort_field not in allowed_sorts:
        sort_field = 'last_name'
    queryset = queryset.order_by(sort_field)
    
    # Calculate summary statistics
    total_students = queryset.count()
    checked_in_count = queryset.filter(device_checked_in=True).count()
    pending_count = total_students - checked_in_count
    checked_in_percent = round((checked_in_count / total_students * 100)) if total_students > 0 else 0
    
    # Get list of unique grades for filter dropdown
    grades = sorted(set(Student.objects.filter(grade__gt=0).values_list('grade', flat=True)))
    
    # Handle CSV export if requested
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="check_in_status_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Student ID', 'First Name', 'Last Name', 'Grade', 'Advisor', 'Device Asset Tag', 'Device Type', 'Check-In Status', 'Check-In Date'])
        
        for student in queryset:
            writer.writerow([
                student.student_id,
                student.first_name,
                student.last_name,
                student.grade or '',
                student.advisor or '',
                student.device_info.device_asset_tag if student.device_info else '',
                student.device_info.device_type if student.device_info else '',
                'Checked In' if student.device_checked_in else 'Pending',
                student.check_in_date.strftime('%Y-%m-%d %H:%M:%S') if student.check_in_date else '',
            ])
        
        return response
    
    context = {
        'students': queryset,
        'summary': {
            'total_students': total_students,
            'checked_in_count': checked_in_count,
            'pending_count': pending_count,
            'checked_in_percent': checked_in_percent,
        },
        'filters': {
            'grade': grade or '',
            'search': search_term,
            'sort': sort_field,
        },
        'grades': grades,
        'page_title': 'Device Check-In Status',
        'page_description': 'View and filter student device check-in progress'
    }
    
    return render(request, 'students/checkin_status.html', context)

