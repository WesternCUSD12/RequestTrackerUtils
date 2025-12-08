"""
Audit views for student device verification.

Phase 5: Teacher Device Audit Session

Implements teacher and admin workflows for verifying device possession through
unified Student data model.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
import logging
import csv
from apps.audit.models import AuditSession, AuditStudent
from apps.students.models import Student

logger = logging.getLogger(__name__)


def teacher_required(view_func):
    """Decorator to restrict access to teachers and admins"""
    def wrapper(request, *args, **kwargs):
        # Authentication is handled by middleware, check session
        user_role = request.session.get('user_role')
        username = request.session.get('username')
        
        # Allow technology_staff (admins)
        if user_role == 'technology_staff':
            return view_func(request, *args, **kwargs)
        
        # Allow teachers
        if user_role == 'teacher':
            return view_func(request, *args, **kwargs)
        
        logger.warning(f"Access denied to audit for user {username} (role: {user_role})")
        return JsonResponse({'error': 'Access denied. Teachers and admins only.'}, status=403)
    
    return wrapper


def admin_required(view_func):
    """Decorator to restrict access to admins only"""
    def wrapper(request, *args, **kwargs):
        # Authentication is handled by middleware, check session
        user_role = request.session.get('user_role')
        username = request.session.get('username')
        
        # Only technology_staff allowed
        if user_role == 'technology_staff':
            return view_func(request, *args, **kwargs)
        
        logger.warning(f"Admin access denied for user {username} (role: {user_role})")
        return JsonResponse({'error': 'Access denied. Admins only.'}, status=403)
    
    return wrapper


@teacher_required
def audit_list(request):
    """T034: View active audit sessions with summary stats
    
    GET /audit/ → Shows all active audit sessions
    - Summary cards: total students, audited count, completion %
    - Session list with timestamps and creator
    - Create session button (admin only)
    
    Requirements:
    - FR-008: Status display with summary
    - FR-008c: Global shared sessions across teachers
    """
    # Get active sessions (newest first)
    active_sessions = AuditSession.objects.filter(status='active').order_by('-created_at')
    
    # Calculate summary stats for each session
    sessions_with_stats = []
    for session in active_sessions:
        total = session.students.count()
        audited = session.students.filter(audited=True).count()
        percent = round((audited / total * 100)) if total > 0 else 0
        
        sessions_with_stats.append({
            'session': session,
            'total_students': total,
            'audited_count': audited,
            'audited_percent': percent,
            'pending_count': total - audited,
        })
    
    context = {
        'sessions': sessions_with_stats,
        'is_admin': request.session.get('user_role') == 'technology_staff',
        'page_title': 'Device Audit Sessions',
        'page_description': 'View and manage device audit sessions'
    }
    
    return render(request, 'audit/session_list.html', context)


@admin_required
@require_http_methods(["POST"])
def create_session(request):
    """Create a new audit session - admin only
    
    POST /audit/create/ → Creates a new active session
    
    Returns JSON response with session ID and redirect URL
    """
    try:
        # Create new session
        session = AuditSession.objects.create(
            created_by=None,  # Session-based auth, no User object
            creator_name=request.session.get('display_name') or request.session.get('username'),
            name=f"Audit {timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.session.get('display_name') or request.session.get('username')}",
            status='active'
        )
        
        # Get all active students
        active_students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Create AuditStudent records for each active student
        audit_students = [
            AuditStudent(
                session=session,
                student=student,
                name=student.full_name,
                grade=str(student.grade),
                advisor=student.advisor or '',
                audited=False
            )
            for student in active_students
        ]
        AuditStudent.objects.bulk_create(audit_students)
        
        logger.info(f"Admin {request.session.get('username')} created audit session {session.session_id}")
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.session_id),
            'redirect_url': f'/devices/audit/session/{session.session_id}/'
        })
    except Exception as e:
        logger.error(f"Error creating audit session: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@teacher_required
def audit_session_detail(request, session_id):
    """T035: View audit session with student list and filters
    
    GET /audit/session/<id> → Shows students in session with filters
    - Grade filter dropdown
    - Advisor filter dropdown (pre-filtered to teacher's advisees)
    - Student table: Name, Grade, Advisor, Audited checkbox
    - Summary cards: total, audited, pending, % complete
    
    Query params:
    - ?grade=10 - Filter by grade
    - ?advisor=name - Filter by advisor
    
    Requirements:
    - FR-008a: Filter by grade and advisor
    - FR-008b: Mark students as audited
    - FR-008c: Teacher sees only their advisees (if teacher)
    """
    session = get_object_or_404(AuditSession, session_id=session_id, status='active')
    
    # Get base queryset
    queryset = AuditStudent.objects.filter(session=session).select_related('student')
    
    # If teacher (not admin), filter to their advisees
    user_role = request.session.get('user_role')
    if user_role != 'technology_staff':
        # Teachers see only their advisees (not implemented yet - would need advisor field in session)
        # For now, teachers see all students in the session
        pass
    
    # Apply grade filter
    grade = request.GET.get('grade', '').strip()
    if grade:
        queryset = queryset.filter(grade=grade)
    
    # Apply advisor filter
    advisor = request.GET.get('advisor', '').strip()
    if advisor:
        queryset = queryset.filter(advisor=advisor)
    
    # Get available grades and advisors for filters
    all_students = AuditStudent.objects.filter(session=session)
    available_grades = sorted(set(all_students.filter(grade__isnull=False).values_list('grade', flat=True)))
    available_advisors = sorted(set(all_students.filter(advisor__isnull=False).values_list('advisor', flat=True)))
    
    # Calculate summary stats
    total = all_students.count()
    audited = all_students.filter(audited=True).count()
    pending = total - audited
    audited_percent = round((audited / total * 100)) if total > 0 else 0
    
    context = {
        'session': session,
        'students': queryset.order_by('name'),
        'summary': {
            'total_students': total,
            'audited_count': audited,
            'pending_count': pending,
            'audited_percent': audited_percent,
            'checked_in': audited,  # For stats card
            'pending': pending,
            'completion_rate': audited_percent,
        },
        'filters': {
            'grade': grade,
            'advisor': advisor,
        },
        'available_grades': available_grades,
        'available_advisors': available_advisors,
        'grades': [6,7,8,9,10,11,12],
        'page_title': session.name or f'Audit Session {str(session.session_id)[:8]}',
        'page_description': 'Review and mark students as audited'
    }
    
    return render(request, 'audit/session_detail.html', context)


@teacher_required
@require_http_methods(["POST"])
def mark_audited(request, session_id):
    """T036: API endpoint to mark student as audited
    
    POST /audit/api/mark-audited/<session_id>
    
    Body: {
        'student_id': 'S001',
        'auditor_name': 'John Smith',
        'notes': 'Device verified and working'
    }
    
    Response: {
        'success': True,
        'student_id': 'S001',
        'audited': True,
        'timestamp': '2025-12-05T14:30:00Z'
    }
    
    Requirements:
    - FR-008b: Mark students as audited with timestamp
    - FR-019: Preserve audit history
    """
    import json
    
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    
    session = get_object_or_404(AuditSession, session_id=session_id, status='active')
    student_id = data.get('student_id', '').strip()
    auditor_name = data.get('auditor_name', request.session.get('display_name') or request.session.get('username'))
    notes = data.get('notes', '').strip()
    
    if not student_id:
        return JsonResponse({'success': False, 'error': 'student_id required'}, status=400)
    
    try:
        audit_student = AuditStudent.objects.get(session=session, student__student_id=student_id)
    except AuditStudent.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Student not found in session'}, status=404)
    
    # Mark as audited
    audit_student.audited = True
    audit_student.audit_timestamp = timezone.now()
    audit_student.auditor_name = auditor_name
    audit_student.save()
    
    logger.info(f"[Audit] {auditor_name} marked {student_id} as audited in session {session.session_id}")
    
    return JsonResponse({
        'success': True,
        'student_id': student_id,
        'audited': True,
        'timestamp': audit_student.audit_timestamp.isoformat(),
        'auditor_name': auditor_name,
    })


@admin_required
@require_http_methods(["POST"])
def rename_session(request, session_id):
    """API endpoint to rename an audit session (admin only)
    
    POST /audit/api/rename-session/<session_id>
    Body: {"name": "New Name"}
    
    Response: {"success": True, "session_id": "...", "name": "..."}
    """
    import json
    
    try:
        data = json.loads(request.body)
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return JsonResponse({'success': False, 'error': 'Name is required'}, status=400)
        
        session = get_object_or_404(AuditSession, session_id=session_id)
        session.name = new_name
        session.save()
        
        logger.info(f"[Audit] Admin {request.session.get('username')} renamed session {session.session_id} to '{new_name}'")
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.session_id),
            'name': session.name
        })
    except Exception as e:
        logger.error(f"Error renaming session {session_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@admin_required
@require_http_methods(["POST"])
def delete_session(request, session_id):
    """API endpoint to delete an audit session (admin only)
    
    POST /audit/api/delete-session/<session_id>
    
    Response: {"success": True, "session_id": "..."}
    """
    try:
        session = get_object_or_404(AuditSession, session_id=session_id)
        session_id_str = str(session.session_id)
        
        # Delete associated audit students first (cascade should handle this, but being explicit)
        session.students.all().delete()
        
        # Delete the session
        session.delete()
        
        logger.info(f"[Audit] Admin {request.session.get('username')} deleted session {session_id_str}")
        
        return JsonResponse({
            'success': True,
            'session_id': session_id_str
        })
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@admin_required
@require_http_methods(["POST"])
def close_session(request, session_id):
    """T038: API endpoint for admin-only session closure
    
    POST /audit/api/close-session/<session_id>
    
    Response: {
        'success': True,
        'session_id': '...',
        'status': 'closed',
        'closed_at': '2025-12-05T14:30:00Z'
    }
    
    Requirements:
    - FR-020: Admin-only session closure
    - FR-019: Keep closed sessions visible (never delete)
    """
    session = get_object_or_404(AuditSession, session_id=session_id, status='active')
    
    # Close the session
    session.status = 'closed'
    session.closed_at = timezone.now()
    session.save()
    
    logger.info(f"[Audit] Admin {request.session.get('username')} closed session {session.session_id}")
    
    return JsonResponse({
        'success': True,
        'session_id': str(session.session_id),
        'status': session.status,
        'closed_at': session.closed_at.isoformat(),
    })


@teacher_required
def export_session_csv(request, session_id):
    """T052: Export audit results to CSV
    
    GET /audit/session/<id>/export-csv → CSV download
    
    Columns: Student ID, Name, Grade, Advisor, Audited, Audit Timestamp, Auditor
    
    Requirements:
    - FR-019: Export audit history
    """
    session = get_object_or_404(AuditSession, session_id=session_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_session_{session.session_id}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student ID', 'Name', 'Grade', 'Advisor', 'Audited', 'Audit Timestamp', 'Auditor Name'])
    
    for audit_student in session.students.all().order_by('name'):
        writer.writerow([
            audit_student.student.student_id if audit_student.student else '',
            audit_student.name,
            audit_student.grade or '',
            audit_student.advisor or '',
            'Yes' if audit_student.audited else 'No',
            audit_student.audit_timestamp.strftime('%Y-%m-%d %H:%M:%S') if audit_student.audit_timestamp else '',
            audit_student.auditor_name or '',
        ])
    
    return response
