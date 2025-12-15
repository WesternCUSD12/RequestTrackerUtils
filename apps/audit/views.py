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
import threading
from concurrent.futures import ThreadPoolExecutor
from apps.audit.models import (
    AuditSession,
    AuditStudent,
    AuditDeviceRecord,
    AuditChangeLog,
)
from apps.students.models import Student

logger = logging.getLogger(__name__)


def teacher_required(view_func):
    """Decorator to restrict access to teachers and admins"""

    def wrapper(request, *args, **kwargs):
        # Authentication is handled by middleware, check session
        user_role = request.session.get("user_role")
        username = request.session.get("username")

        # Allow technology_staff (admins)
        if user_role == "technology_staff":
            return view_func(request, *args, **kwargs)

        # Allow teachers
        if user_role == "teacher":
            return view_func(request, *args, **kwargs)

        logger.warning(
            f"Access denied to audit for user {username} (role: {user_role})"
        )
        return JsonResponse(
            {"error": "Access denied. Teachers and admins only."}, status=403
        )

    return wrapper


def admin_required(view_func):
    """Decorator to restrict access to admins only"""

    def wrapper(request, *args, **kwargs):
        # Authentication is handled by middleware, check session
        user_role = request.session.get("user_role")
        username = request.session.get("username")

        # Only technology_staff allowed
        if user_role == "technology_staff":
            return view_func(request, *args, **kwargs)

        logger.warning(f"Admin access denied for user {username} (role: {user_role})")
        return JsonResponse({"error": "Access denied. Admins only."}, status=403)

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
    active_sessions = AuditSession.objects.filter(status="active").order_by(
        "-created_at"
    )

    # Calculate summary stats for each session
    sessions_with_stats = []
    for session in active_sessions:
        total = session.students.count()
        audited = session.students.filter(audited=True).count()
        percent = round((audited / total * 100)) if total > 0 else 0

        sessions_with_stats.append(
            {
                "session": session,
                "total_students": total,
                "audited_count": audited,
                "audited_percent": percent,
                "pending_count": total - audited,
            }
        )

    context = {
        "sessions": sessions_with_stats,
        "is_admin": request.session.get("user_role") == "technology_staff",
        "page_title": "Device Audit Sessions",
        "page_description": "View and manage device audit sessions",
    }

    return render(request, "audit/session_list.html", context)


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
            creator_name=request.session.get("display_name")
            or request.session.get("username"),
            name=f"Audit {timezone.now().strftime('%Y-%m-%d %H:%M')} - {request.session.get('display_name') or request.session.get('username')}",
            status="active",
        )

        # Get all active students
        active_students = Student.objects.filter(is_active=True).order_by(
            "last_name", "first_name"
        )

        # Create AuditStudent records for each active student
        audit_students = [
            AuditStudent(
                session=session,
                student=student,
                name=student.full_name,
                grade=str(student.grade),
                advisor=student.advisor or "",
                username=student.username or "",
                audited=False,
            )
            for student in active_students
        ]
        AuditStudent.objects.bulk_create(audit_students)

        logger.info(
            f"Admin {request.session.get('username')} created audit session {session.session_id}"
        )
        # Dispatch background prefetch of RT devices so teachers see devices immediately
        try:
            thread = threading.Thread(
                target=prefetch_session_devices,
                args=(str(session.session_id),),
                daemon=True,
            )
            thread.start()
            logger.info(
                f"Dispatched background prefetch for session {session.session_id}"
            )
        except Exception as e:
            logger.error(f"Failed to dispatch prefetch thread: {e}")

        return JsonResponse(
            {
                "success": True,
                "session_id": str(session.session_id),
                "redirect_url": f"/devices/audit/session/{session.session_id}/",
            }
        )
    except Exception as e:
        logger.error(f"Error creating audit session: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def prefetch_session_devices(session_id):
    """Background worker: fetch devices for all AuditStudents in a session using ThreadPoolExecutor.

    This runs in a daemon thread and uses parallel workers to fetch RT data for multiple
    students concurrently. Errors for individual students are logged and do not stop the overall run.
    """
    from django.db import close_old_connections

    close_old_connections()

    print(f"\n{'=' * 80}")
    print(f"[PREFETCH] Starting device prefetch for session {session_id}")
    print(f"{'=' * 80}\n")
    logger.info(f"[prefetch] Starting device prefetch for session {session_id}")

    try:
        session = AuditSession.objects.get(session_id=session_id)
        print(f"[PREFETCH] ✓ Found session: {session}")

        audit_students = list(
            AuditStudent.objects.filter(session=session).select_related("student")
        )
        student_count = len(audit_students)
        print(f"[PREFETCH] ✓ Found {student_count} audit students")

        # Import RT API helpers lazily
        try:
            from common.rt_api import fetch_user_data, get_assets_by_owner

            print(f"[PREFETCH] ✓ RT API helpers imported")
        except Exception as import_err:
            logger.error(f"[prefetch] Could not import RT API helpers: {import_err}")
            print(f"[PREFETCH] ✗ Import error: {import_err}")
            return

        # Process students in parallel using ThreadPoolExecutor (5 worker threads)
        print(f"[PREFETCH] Starting parallel fetch with 5 workers...\n")
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    _prefetch_student_devices,
                    audit_student,
                    fetch_user_data,
                    get_assets_by_owner,
                )
                for audit_student in audit_students
            ]
            # Wait for all futures to complete
            for future in futures:
                try:
                    future.result()  # Blocks until complete, propagates exceptions if any
                except Exception as e:
                    logger.error(f"[prefetch] Task error: {e}")

        logger.info(f"[prefetch] Completed device prefetch for session {session_id}")
        print(
            f"\n[PREFETCH] ✓ Completed device prefetch for session {session_id} ({student_count} students)\n"
        )
    except AuditSession.DoesNotExist:
        logger.error(f"[prefetch] AuditSession not found: {session_id}")
        print(f"[PREFETCH] ✗ AuditSession not found: {session_id}\n")
    except Exception as e:
        logger.error(f"[prefetch] Unexpected error during prefetch: {e}")
        print(f"[PREFETCH] ✗ Unexpected error: {e}\n")
    finally:
        close_old_connections()


def _prefetch_student_devices(audit_student, fetch_user_data, get_assets_by_owner):
    """Fetch and create device records for a single student. Called by ThreadPoolExecutor workers."""
    from django.db import close_old_connections

    close_old_connections()

    try:
        username = None
        if audit_student.student and getattr(audit_student.student, "username", None):
            username = audit_student.student.username
        elif audit_student.username:
            username = audit_student.username

        if not username:
            logger.debug(
                f"[prefetch] Skipping student {audit_student.id} - no username"
            )
            return

        print(f"[PREFETCH]   → {audit_student.name} (username={username})")

        try:
            user_data = fetch_user_data(username)
        except Exception as e:
            logger.error(f"[prefetch] Error fetching user data for {username}: {e}")
            print(f"[PREFETCH]     ✗ Fetch error: {e}")
            return

        numeric_id = None
        hyperlinks = (
            user_data.get("_hyperlinks", []) if isinstance(user_data, dict) else []
        )
        for link in hyperlinks:
            if link.get("ref") == "self" and link.get("type") == "user":
                numeric_id = str(link.get("id"))
                break

        if not numeric_id:
            logger.debug(f"[prefetch] No numeric RT id for username={username}")
            return

        try:
            assets = get_assets_by_owner(numeric_id)
        except Exception as e:
            logger.error(f"[prefetch] Error getting assets for owner {numeric_id}: {e}")
            print(f"[PREFETCH]     ✗ Assets error: {e}")
            return

        device_count = 0
        for asset in assets:
            try:
                asset_id = asset.get("id") or asset.get("asset_id") or ""
                asset_name = asset.get("Name") or asset.get("asset_name") or ""
                asset_tag = asset.get("Name") or asset.get("asset_tag") or ""

                device_type = "Unknown"
                custom_fields = asset.get("CustomFields", [])
                if isinstance(custom_fields, list):
                    for cf in custom_fields:
                        if isinstance(cf, dict) and cf.get("name") == "Device Type":
                            device_type = cf.get("value", "Unknown")
                            break
                elif isinstance(custom_fields, dict):
                    device_type = custom_fields.get("Device Type", "Unknown")

                AuditDeviceRecord.objects.get_or_create(
                    audit_student=audit_student,
                    asset_id=asset_id,
                    defaults={
                        "asset_tag": asset_tag,
                        "asset_name": asset_name,
                        "device_type": device_type,
                    },
                )
                device_count += 1
            except Exception as asset_err:
                logger.error(
                    f"[prefetch] Error creating device record for asset {asset}: {asset_err}"
                )

        print(f"[PREFETCH]     ✓ Created {device_count} device records")
    except Exception as e:
        logger.error(
            f"[prefetch] Error processing audit_student {audit_student.id}: {e}"
        )
        print(f"[PREFETCH]     ✗ Processing error: {e}")


@teacher_required
def audit_session_detail(request, session_id):
    logger.info(
        f"[audit_session_detail] Called by user={request.session.get('username')} (role={request.session.get('user_role')}) for session_id={session_id}"
    )
    try:
        session = get_object_or_404(
            AuditSession, session_id=session_id, status="active"
        )
        logger.info(f"[audit_session_detail] Loaded session: {session}")

        queryset = AuditStudent.objects.filter(session=session).select_related(
            "student"
        )
        logger.info(f"[audit_session_detail] Base queryset count: {queryset.count()}")

        user_role = request.session.get("user_role")
        if user_role != "technology_staff":
            logger.info(
                f"[audit_session_detail] User is not admin, user_role={user_role}"
            )
            # Teachers see all students for now

        grade = request.GET.get("grade", "").strip()
        if grade:
            queryset = queryset.filter(grade=grade)
            logger.info(
                f"[audit_session_detail] Applied grade filter: {grade}, count={queryset.count()}"
            )

        advisor = request.GET.get("advisor", "").strip()
        if advisor:
            queryset = queryset.filter(advisor=advisor)
            logger.info(
                f"[audit_session_detail] Applied advisor filter: {advisor}, count={queryset.count()}"
            )

        all_students = AuditStudent.objects.filter(session=session)
        available_grades = sorted(
            set(
                all_students.filter(grade__isnull=False).values_list("grade", flat=True)
            )
        )
        available_advisors = sorted(
            set(
                all_students.filter(advisor__isnull=False).values_list(
                    "advisor", flat=True
                )
            )
        )

        total = all_students.count()
        audited = all_students.filter(audited=True).count()
        pending = total - audited
        audited_percent = round((audited / total * 100)) if total > 0 else 0

        logger.info(
            f"[audit_session_detail] Summary: total={total}, audited={audited}, pending={pending}, percent={audited_percent}"
        )
        logger.info(f"[audit_session_detail] Final queryset count: {queryset.count()}")

        context = {
            "session": session,
            "students": queryset.order_by("name"),
            "summary": {
                "total_students": total,
                "audited_count": audited,
                "pending_count": pending,
                "audited_percent": audited_percent,
                "checked_in": audited,  # For stats card
                "pending": pending,
                "completion_rate": audited_percent,
            },
            "filters": {
                "grade": grade,
                "advisor": advisor,
            },
            "available_grades": available_grades,
            "available_advisors": available_advisors,
            "grades": [6, 7, 8, 9, 10, 11, 12],
            "page_title": session.name
            or f"Audit Session {str(session.session_id)[:8]}",
            "page_description": "Review and mark students as audited",
        }
        logger.info(
            f"[audit_session_detail] Rendering template with {len(context['students'])} students"
        )
        return render(request, "audit/session_detail.html", context)
    except Exception as e:
        logger.error(f"[audit_session_detail] ERROR: {e}", exc_info=True)
        return JsonResponse(
            {"error": "Internal server error", "details": str(e)}, status=500
        )


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
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    session = get_object_or_404(AuditSession, session_id=session_id, status="active")
    student_id = data.get("student_id", "").strip()
    auditor_name = data.get(
        "auditor_name",
        request.session.get("display_name") or request.session.get("username"),
    )
    notes = data.get("notes", "").strip()

    if not student_id:
        return JsonResponse(
            {"success": False, "error": "student_id required"}, status=400
        )

    try:
        audit_student = AuditStudent.objects.get(
            session=session, student__student_id=student_id
        )
    except AuditStudent.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Student not found in session"}, status=404
        )

    # Mark as audited
    audit_student.audited = True
    audit_student.audit_timestamp = timezone.now()
    audit_student.auditor_name = auditor_name
    audit_student.save()

    logger.info(
        f"[Audit] {auditor_name} marked {student_id} as audited in session {session.session_id}"
    )

    return JsonResponse(
        {
            "success": True,
            "student_id": student_id,
            "audited": True,
            "timestamp": audit_student.audit_timestamp.isoformat(),
            "auditor_name": auditor_name,
        }
    )


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
        new_name = data.get("name", "").strip()

        if not new_name:
            return JsonResponse(
                {"success": False, "error": "Name is required"}, status=400
            )

        session = get_object_or_404(AuditSession, session_id=session_id)
        session.name = new_name
        session.save()

        logger.info(
            f"[Audit] Admin {request.session.get('username')} renamed session {session.session_id} to '{new_name}'"
        )

        return JsonResponse(
            {
                "success": True,
                "session_id": str(session.session_id),
                "name": session.name,
            }
        )
    except Exception as e:
        logger.error(f"Error renaming session {session_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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

        logger.info(
            f"[Audit] Admin {request.session.get('username')} deleted session {session_id_str}"
        )

        return JsonResponse({"success": True, "session_id": session_id_str})
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


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
    session = get_object_or_404(AuditSession, session_id=session_id, status="active")

    # Close the session
    session.status = "closed"
    session.closed_at = timezone.now()
    session.save()

    logger.info(
        f"[Audit] Admin {request.session.get('username')} closed session {session.session_id}"
    )

    return JsonResponse(
        {
            "success": True,
            "session_id": str(session.session_id),
            "status": session.status,
            "closed_at": session.closed_at.isoformat(),
        }
    )


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
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="audit_session_{session.session_id}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Student ID",
            "Name",
            "Grade",
            "Advisor",
            "Audited",
            "Audit Timestamp",
            "Auditor Name",
        ]
    )

    for audit_student in session.students.all().order_by("name"):
        writer.writerow(
            [
                audit_student.student.student_id if audit_student.student else "",
                audit_student.name,
                audit_student.grade or "",
                audit_student.advisor or "",
                "Yes" if audit_student.audited else "No",
                audit_student.audit_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                if audit_student.audit_timestamp
                else "",
                audit_student.auditor_name or "",
            ]
        )

    return response


@require_http_methods(["POST"])
@teacher_required
def save_device_audit(request, session_id, student_id, device_id):
    """Save device audit status and notes for a specific device"""
    try:
        session = get_object_or_404(AuditSession, session_id=session_id)

        # Check if session is locked
        if session.is_closed:
            return JsonResponse(
                {"error": "Session is locked. No further edits allowed."}, status=403
            )

        audit_student = get_object_or_404(AuditStudent, id=student_id, session=session)
        # device_id is the RT asset ID, not the Django PK - look up by asset_id
        device_record = get_object_or_404(
            AuditDeviceRecord, asset_id=device_id, audit_student=audit_student
        )

        data = request.POST or {}
        audit_status = data.get("audit_status", "pending")
        audit_notes = data.get("audit_notes", "")
        user_name = request.session.get("username", "Unknown")

        old_status = device_record.audit_status
        old_notes = device_record.audit_notes

        device_record.audit_status = audit_status
        device_record.audit_notes = audit_notes
        device_record.verified = True
        device_record.verification_timestamp = timezone.now()
        device_record.verified_by = user_name
        device_record.save()

        # Log the change
        if old_status != audit_status:
            AuditChangeLog.objects.create(
                session=session,
                audit_student=audit_student,
                device_record=device_record,
                user_name=user_name,
                action="device_status_changed",
                device_info=f"{device_record.asset_id} ({device_record.asset_tag})",
                old_value=old_status,
                new_value=audit_status,
                notes=audit_notes,
            )

        if old_notes != audit_notes:
            AuditChangeLog.objects.create(
                session=session,
                audit_student=audit_student,
                device_record=device_record,
                user_name=user_name,
                action="device_notes_updated" if old_notes else "device_notes_added",
                device_info=f"{device_record.asset_id} ({device_record.asset_tag})",
                old_value=old_notes,
                new_value=audit_notes,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Device audit saved successfully",
                "device_id": device_id,
                "audit_status": audit_status,
            }
        )

    except Exception as e:
        logger.error(f"Error saving device audit: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@teacher_required
def mark_student_completed(request, session_id, student_id):
    """Mark an AuditStudent as completed (audited=True) after all devices are verified.

    POST /devices/audit/api/student/<session_id>/<student_id>/complete/

    Response: {
        'success': True,
        'message': 'Student marked as completed',
        'student_id': <id>,
        'audited': True,
        'timestamp': '2025-12-05T14:30:00Z',
        'auditor_name': 'jmartin'
    }
    """
    try:
        session = get_object_or_404(AuditSession, session_id=session_id)
        audit_student = get_object_or_404(AuditStudent, id=student_id, session=session)

        # Check if session is locked
        if session.is_closed:
            return JsonResponse(
                {"error": "Session is locked. No further edits allowed."}, status=403
            )

        user_name = request.session.get("username", "Unknown")

        # Mark student as audited
        audit_student.audited = True
        audit_student.audit_timestamp = timezone.now()
        audit_student.auditor_name = user_name
        audit_student.save()

        logger.info(
            f"[Audit] {user_name} marked student {audit_student.name} (ID: {student_id}) as completed in session {session.session_id}"
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Student marked as completed",
                "student_id": student_id,
                "audited": True,
                "timestamp": audit_student.audit_timestamp.isoformat(),
                "auditor_name": user_name,
            }
        )

    except Exception as e:
        logger.error(f"Error marking student as completed: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@teacher_required
def get_audit_logs(request, session_id):
    """Get audit change logs for a session - viewable by all users"""
    try:
        session = get_object_or_404(AuditSession, session_id=session_id)

        logs = (
            AuditChangeLog.objects.filter(session=session)
            .select_related("audit_student", "device_record")
            .order_by("-timestamp")
        )

        log_data = []
        for log in logs:
            log_data.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "user": log.user_name,
                    "student": log.audit_student.name if log.audit_student else "N/A",
                    "device": log.device_info,
                    "action": log.get_action_display(),
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "notes": log.notes,
                }
            )

        return JsonResponse({"success": True, "logs": log_data})

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@admin_required
def lock_audit_session(request, session_id):
    """Lock an audit session to prevent further edits - admin only"""
    try:
        session = get_object_or_404(AuditSession, session_id=session_id)

        if session.is_closed:
            return JsonResponse({"error": "Session is already locked"}, status=400)

        user_name = request.session.get("username", "Unknown")

        session.status = "closed"
        session.closed_at = timezone.now()
        session.save()

        # Log the session lock
        AuditChangeLog.objects.create(
            session=session,
            user_name=user_name,
            action="session_locked",
            device_info="Session",
            new_value="Closed",
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Audit session locked successfully",
                "session_status": "closed",
            }
        )

    except Exception as e:
        logger.error(f"Error locking audit session: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@teacher_required
def get_audit_student_devices(request, session_id, audit_student_id):
    """Fetch all devices for a specific audit student using their username"""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"START: get_audit_student_devices called")
    logger.info(f"  session_id={session_id}, audit_student_id={audit_student_id}")
    logger.info(f"{'=' * 80}")

    try:
        logger.info(f"[1] Looking up AuditSession with session_id={session_id}")
        session = get_object_or_404(AuditSession, session_id=session_id)
        logger.info(f"[2] ✓ Found session: {session.name}")

        logger.info(f"[3] Looking up AuditStudent with id={audit_student_id}")
        audit_student = get_object_or_404(
            AuditStudent, id=audit_student_id, session=session
        )
        logger.info(f"[4] ✓ Found audit_student: {audit_student.name}")

        # Get username - first try linked Student, then fallback to AuditStudent's own username
        username = None
        if audit_student.student:
            username = audit_student.student.username
            logger.info(f"[5] Using username from linked Student: {username}")
        elif audit_student.username:
            username = audit_student.username
            logger.info(f"[5] Using username from AuditStudent: {username}")
        else:
            logger.warning(
                f"[5] ✗ NO USERNAME - audit_student.student={audit_student.student}, audit_student.username={audit_student.username}"
            )

        if not username:
            logger.warning(f"[6] ✗ NO USERNAME FOUND - returning empty devices")
            return JsonResponse({"devices": [], "error": "Student has no username"})

        logger.info(f"[6] ✓ Username to use for RT lookup: {username}")

        # Use the common RT API to get devices - use username to look up RT ID
        try:
            from common.rt_api import get_assets_by_owner, fetch_user_data

            logger.info(f"[7] ✓ RT API imported successfully")

            logger.info(f"[8] Calling fetch_user_data('{username}')")

            # Fetch user data using username to get numeric ID
            try:
                user_data = fetch_user_data(username)
                logger.info(
                    f"[9] ✓ fetch_user_data returned: {type(user_data).__name__}"
                )
                logger.info(
                    f"    - keys: {list(user_data.keys()) if isinstance(user_data, dict) else 'N/A'}"
                )

                numeric_id = None
                hyperlinks = user_data.get("_hyperlinks", [])
                logger.info(f"[10] Hyperlinks found: {len(hyperlinks)}")

                for idx, link in enumerate(hyperlinks):
                    logger.info(
                        f"     - hyperlink[{idx}]: ref={link.get('ref')}, type={link.get('type')}, id={link.get('id')}"
                    )
                    if link.get("ref") == "self" and link.get("type") == "user":
                        numeric_id = str(link.get("id"))
                        logger.info(f"     ✓ MATCH! Using numeric_id={numeric_id}")
                        break

                if numeric_id:
                    logger.info(f"[11] Calling get_assets_by_owner('{numeric_id}')")
                    assets = get_assets_by_owner(numeric_id)
                    logger.info(
                        f"[12] ✓ get_assets_by_owner returned {len(assets)} devices"
                    )
                    for asset_idx, asset in enumerate(assets[:3]):  # Log first 3
                        logger.info(f"     - asset[{asset_idx}]: {asset}")
                    if len(assets) > 3:
                        logger.info(f"     ... and {len(assets) - 3} more devices")

                    # Create AuditDeviceRecord entries for each asset if they don't exist
                    logger.info(f"[12a] Creating/updating AuditDeviceRecord entries")
                    for asset in assets:
                        asset_id = asset.get("id", "")
                        asset_name = asset.get("Name", "")
                        asset_tag = asset.get("Name", "")  # RT uses Name for asset tag

                        # CustomFields is a list, extract Device Type if available
                        device_type = "Unknown"
                        custom_fields = asset.get("CustomFields", [])
                        if isinstance(custom_fields, list):
                            for cf in custom_fields:
                                if (
                                    isinstance(cf, dict)
                                    and cf.get("name") == "Device Type"
                                ):
                                    device_type = cf.get("value", "Unknown")
                                    break
                        elif isinstance(custom_fields, dict):
                            device_type = custom_fields.get("Device Type", "Unknown")

                        # Use get_or_create to avoid duplicates
                        device_record, created = (
                            AuditDeviceRecord.objects.get_or_create(
                                audit_student=audit_student,
                                asset_id=asset_id,
                                defaults={
                                    "asset_tag": asset_tag,
                                    "asset_name": asset_name,
                                    "device_type": device_type,
                                },
                            )
                        )
                        if created:
                            logger.info(
                                f"     - Created AuditDeviceRecord for asset {asset_id}"
                            )
                        else:
                            logger.info(
                                f"     - AuditDeviceRecord already exists for asset {asset_id}"
                            )
                else:
                    logger.warning(
                        f"[11] ✗ Could not extract numeric ID from RT user {username}"
                    )
                    logger.warning(f"     Available hyperlinks: {hyperlinks}")
                    assets = []
            except Exception as user_err:
                logger.error(
                    f"[9] ✗ Exception calling fetch_user_data: {type(user_err).__name__}: {user_err}",
                    exc_info=True,
                )
                assets = []

            logger.info(f"[13] Returning JsonResponse with {len(assets)} devices")
            return JsonResponse(
                {
                    "student_id": audit_student.id,
                    "student_name": audit_student.name,
                    "devices": assets,
                }
            )

        except ImportError as e:
            logger.error(f"[7] ✗ Could not import RT API: {e}")
            return JsonResponse({"devices": [], "error": "RT API import failed"})

    except Exception as e:
        logger.error(
            f"[X] Exception in get_audit_student_devices: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return JsonResponse({"devices": [], "error": str(e)}, status=200)
        return JsonResponse({"error": str(e)}, status=500)
