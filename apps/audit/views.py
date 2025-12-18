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
import time
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

        # Build a safe serializable list of students for the template to avoid
        # accessing related objects directly (Student.device_info may not exist)
        safe_students = []
        for s in queryset.order_by("name"):
            # Build a nested 'student' mapping with 'device_info' if available
            student_mapping = None
            if s.student:
                try:
                    di = s.student.device_info
                    device_info = {
                        "asset_tag": getattr(di, "asset_tag", None),
                        "device_type": getattr(di, "device_type", None),
                        "asset_id": getattr(di, "asset_id", None),
                    }
                except Exception:
                    device_info = None

                student_mapping = {"device_info": device_info}

            safe_students.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "grade": s.grade,
                    "advisor": s.advisor,
                    "audited": s.audited,
                    "audit_timestamp": s.audit_timestamp,
                    "student": student_mapping,
                }
            )

        # Compute a safe current user name to avoid template lookups on session keys
        try:
            if getattr(request, "user", None) and getattr(
                request.user, "is_authenticated", False
            ):
                try:
                    current_user_name = (
                        request.user.get_full_name() or request.user.get_username()
                    )
                except Exception:
                    # Fallback if methods are unavailable
                    current_user_name = (
                        getattr(request.user, "get_username", lambda: None)() or "Guest"
                    )
            else:
                current_user_name = (
                    request.session.get("display_name")
                    or request.session.get("username")
                    or "Guest"
                )
        except Exception:
            current_user_name = "Guest"

        # Expose a base URL for client-side JS so the frontend can call the API
        try:
            base_url = f"{request.scheme}://{request.get_host()}"
        except Exception:
            base_url = None

        context = {
            "session": session,
            "students": safe_students,
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
            "user_role": user_role,
            "label_width": 100,  # Default label width in mm
            "label_height": 62,  # Default label height in mm
            "current_user_name": current_user_name,
            "base_url": base_url,
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
def lookup_device_owner(request, asset_id):
    """Lookup device owner by asset ID using RT API"""
    try:
        from common.rt_api import find_asset_by_name

        logger.info(f"Looking up device owner for asset_id: {asset_id}")

        device_info = find_asset_by_name(asset_id)

        if device_info:
            # Extract owner information
            owner_raw = device_info.get("Owner")
            owner_id = None
            owner_name = None
            owner_username = None

            if owner_raw:
                # Owner can be a dict with 'id', 'type', '_url' or just a string
                if isinstance(owner_raw, dict):
                    owner_id = owner_raw.get("id")
                else:
                    owner_id = str(owner_raw)

                if owner_id:
                    try:
                        from common.rt_api import fetch_user_data

                        owner_data = fetch_user_data(owner_id)
                        if owner_data:
                            owner_name = owner_data.get("Name", f"User {owner_id}")
                            owner_username = owner_data.get("Name", f"User {owner_id}")
                    except Exception as owner_err:
                        logger.warning(
                            f"Could not fetch owner details for {owner_id}: {owner_err}"
                        )
                        owner_name = f"User {owner_id}"
                        owner_username = f"User {owner_id}"

            # Extract device type from custom fields
            device_type = "Unknown"
            custom_fields = device_info.get("CustomFields", [])
            if isinstance(custom_fields, list):
                for cf in custom_fields:
                    if isinstance(cf, dict) and cf.get("name") == "Device Type":
                        device_type = cf.get("value", "Unknown")
                        break
            elif isinstance(custom_fields, dict):
                device_type = custom_fields.get("Device Type", "Unknown")

            return JsonResponse(
                {
                    "found": True,
                    "asset_id": device_info.get("id", asset_id),
                    "asset_name": device_info.get("Name")
                    or device_info.get("Description"),
                    "owner_name": owner_name,
                    "owner_username": owner_username,
                    "device_type": device_type,
                    "status": device_info.get("Status", "Unknown"),
                }
            )
        else:
            return JsonResponse({"found": False, "error": "Device not found"})

    except Exception as e:
        logger.error(f"Error looking up device {asset_id}: {e}")
        return JsonResponse({"found": False, "error": str(e)}, status=500)


# In-memory prefetch job registry
import uuid
import time

PREFETCH_JOBS = {}
PREFETCH_JOBS_LOCK = threading.RLock()


def _run_manual_prefetch(session_id, job=None):
    """Core manual prefetch logic extracted to a helper so it can run in background threads.

    Returns a result dict with keys: processed_students, total_students, total_devices, errors
    Updates `job` dict (if provided) with status/log/progress fields.
    """
    result = {
        "processed_students": 0,
        "total_students": 0,
        "total_devices": 0,
        "errors": [],
    }
    try:
        session = AuditSession.objects.get(session_id=session_id)

        # Get all audit students for this session
        audit_students = list(
            AuditStudent.objects.filter(session=session).select_related("student")
        )
        student_count = len(audit_students)
        result["total_students"] = student_count

        # Import RT API helpers
        from common.rt_api import (
            fetch_user_data,
            search_assets,
            fetch_all_assets_cached,
            build_asset_indexes,
            get_assets_by_owner,
            asset_cache,
        )

        # Fetch ALL assets in one query and build local indexes
        try:
            all_assets = fetch_all_assets_cached(config=None, force_refresh=True)
        except Exception as e:
            msg = f"Failed to fetch all assets: {e}"
            logger.error(f"[MANUAL PREFETCH] {msg}")
            if job is not None:
                job["status"] = "failed"
                job.setdefault("log", []).append(msg)
            result["errors"].append(msg)
            return result

        indexes = build_asset_indexes(all_assets)
        assets_by_owner = indexes.get("by_owner", {})

        # Prefetch live-fallback configuration
        import os

        fetch_on_miss = os.getenv("RTUTILS_PREFETCH_FETCH_ON_MISS", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        try:
            max_rt_calls = int(os.getenv("RTUTILS_PREFETCH_MAX_RT_CALLS", "50"))
        except Exception:
            max_rt_calls = 50
        rt_calls_made = 0

        # Map usernames to RT numeric IDs
        username_to_rt_id = {}
        for audit_student in audit_students:
            username = None
            if audit_student.student and getattr(
                audit_student.student, "username", None
            ):
                username = audit_student.student.username
            elif audit_student.username:
                username = audit_student.username

            if username and username not in username_to_rt_id:
                try:
                    user_data = fetch_user_data(username)
                    numeric_id = None
                    hyperlinks = user_data.get("_hyperlinks", [])
                    for link in hyperlinks:
                        if link.get("ref") == "self" and link.get("type") == "user":
                            numeric_id = str(link.get("id"))
                            break

                    if numeric_id:
                        username_to_rt_id[username] = numeric_id
                    else:
                        logger.warning(
                            f"[MANUAL PREFETCH] No RT ID found for username {username}"
                        )
                        result["errors"].append(f"No RT ID for {username}")
                except Exception as e:
                    logger.warning(
                        f"[MANUAL PREFETCH] Failed to get RT ID for {username}: {e}"
                    )
                    result["errors"].append(f"RT ID lookup failed for {username}: {e}")

        # Process students using the pre-fetched asset data
        processed_students = 0
        total_devices = 0

        for idx, audit_student in enumerate(audit_students):
            try:
                username = None
                if audit_student.student and getattr(
                    audit_student.student, "username", None
                ):
                    username = audit_student.student.username
                elif audit_student.username:
                    username = audit_student.username

                if not username:
                    continue

                numeric_id = username_to_rt_id.get(username)
                if not numeric_id:
                    result["errors"].append(
                        f"No RT ID mapping found for username {username}"
                    )
                    continue

                student_assets = assets_by_owner.get(numeric_id, [])

                # If no assets found in the bulk index, optionally fetch live per-owner
                # to cover cache misses. This will merge newly fetched assets into the
                # persistent `asset_cache` under its lock and rebuild indexes so
                # subsequent students benefit from the new data.
                if (
                    not student_assets
                    and fetch_on_miss
                    and rt_calls_made < max_rt_calls
                ):
                    try:
                        if job is not None:
                            job.setdefault("log", []).append(
                                f"Cache miss for {audit_student.name} (RT id={numeric_id}), fetching live"
                            )
                        live_assets = get_assets_by_owner(numeric_id)
                        rt_calls_made += 1

                        if live_assets:
                            try:
                                # Merge live_assets into persistent all_assets cache safely
                                with asset_cache.lock:
                                    try:
                                        existing_all = (
                                            asset_cache.get("all_assets")
                                            or all_assets
                                            or []
                                        )
                                    except Exception:
                                        existing_all = all_assets or []

                                    # Build map of existing ids to avoid duplicates
                                    existing_by_id = {
                                        str(a.get("id")): a
                                        for a in existing_all
                                        if a.get("id")
                                    }

                                    new_added = 0
                                    for a in live_assets:
                                        aid = a.get("id") or a.get("asset_id")
                                        aid = str(aid) if aid is not None else None
                                        if aid and aid not in existing_by_id:
                                            existing_all.append(a)
                                            existing_by_id[aid] = a
                                            new_added += 1

                                    if new_added > 0:
                                        try:
                                            asset_cache.set("all_assets", existing_all)
                                            if job is not None:
                                                job.setdefault("log", []).append(
                                                    f"Merged {new_added} live assets for owner {numeric_id} into cache"
                                                )
                                        except Exception as e:
                                            logger.warning(
                                                f"Failed to update asset_cache: {e}"
                                            )
                                            if job is not None:
                                                job.setdefault("log", []).append(
                                                    f"Warning: failed to save merged assets: {e}"
                                                )

                                    # Update local all_assets variable and rebuild indexes
                                    all_assets = existing_all
                                    try:
                                        indexes = build_asset_indexes(all_assets)
                                        assets_by_owner = indexes.get("by_owner", {})
                                        student_assets = assets_by_owner.get(
                                            numeric_id, live_assets
                                        )
                                    except Exception as e:
                                        logger.warning(
                                            f"Failed to rebuild indexes after merge: {e}"
                                        )
                                        # Fall back to using live_assets directly
                                        student_assets = live_assets
                            except Exception as merge_err:
                                logger.error(
                                    f"Error merging live assets into cache: {merge_err}"
                                )
                                result["errors"].append(
                                    f"Cache merge failed for owner {numeric_id}: {merge_err}"
                                )
                                student_assets = live_assets
                        else:
                            # No live assets returned
                            if job is not None:
                                job.setdefault("log", []).append(
                                    f"No live assets returned for owner {numeric_id}"
                                )
                    except Exception as live_err:
                        logger.warning(
                            f"Live fetch for owner {numeric_id} failed: {live_err}"
                        )
                        result["errors"].append(
                            f"Live fetch failed for owner {numeric_id}: {live_err}"
                        )

                student_device_count = 0
                for asset in student_assets:
                    try:
                        asset_id = asset.get("id") or asset.get("asset_id") or ""
                        asset_name = asset.get("Name") or asset.get("asset_name") or ""
                        asset_tag = asset.get("Name") or asset.get("asset_tag") or ""

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

                        AuditDeviceRecord.objects.get_or_create(
                            audit_student=audit_student,
                            asset_id=asset_id,
                            defaults={
                                "asset_tag": asset_tag,
                                "asset_name": asset_name,
                                "device_type": device_type,
                            },
                        )
                        student_device_count += 1
                        total_devices += 1
                    except Exception as asset_err:
                        logger.error(
                            f"[MANUAL PREFETCH] Error creating device record for asset {asset}: {asset_err}"
                        )

                processed_students += 1

                # Update job progress if provided
                if job is not None:
                    job["progress"] = int(
                        (processed_students / (student_count or 1)) * 100
                    )
                    job.setdefault("log", []).append(
                        f"Processed {audit_student.name}: {student_device_count} devices"
                    )

            except Exception as student_err:
                msg = f"Error processing student {getattr(audit_student, 'id', 'unknown')}: {student_err}"
                logger.error(f"[MANUAL PREFETCH] {msg}")
                result["errors"].append(msg)

        result["processed_students"] = processed_students
        result["total_devices"] = total_devices

        if job is not None:
            job["status"] = "completed"
            job.setdefault("log", []).append(
                f"Completed: {processed_students}/{student_count} students, {total_devices} devices"
            )

        return result

    except AuditSession.DoesNotExist:
        msg = f"AuditSession not found: {session_id}"
        logger.error(f"[MANUAL PREFETCH] {msg}")
        if job is not None:
            job["status"] = "failed"
            job.setdefault("log", []).append(msg)
        return result
    except Exception as e:
        logger.error(f"[MANUAL PREFETCH] Unexpected error: {e}", exc_info=True)
        if job is not None:
            job["status"] = "failed"
            job.setdefault("log", []).append(str(e))
        result["errors"].append(str(e))
        return result


@require_http_methods(["POST"])
@admin_required
def prefetch_session_devices_manual(request, session_id):
    """Manual trigger for device prefetch - admin/tech team only (synchronous)

    This endpoint still exists for synchronous admin use; it delegates to the
    shared helper above.
    """
    try:
        result = _run_manual_prefetch(session_id, job=None)
        return JsonResponse({"success": True, **result})
    except Exception as e:
        logger.error(f"[MANUAL PREFETCH] Unexpected error in sync endpoint: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["POST"])
@admin_required
def prefetch_session_devices_async(request, session_id):
    """Start an asynchronous prefetch job and return a job_id for status polling."""
    try:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "log": [],
            "created_at": time.time(),
        }
        with PREFETCH_JOBS_LOCK:
            PREFETCH_JOBS[job_id] = job

        def _worker():
            with PREFETCH_JOBS_LOCK:
                PREFETCH_JOBS[job_id]["status"] = "running"
            try:
                _run_manual_prefetch(session_id, job=PREFETCH_JOBS[job_id])
            except Exception as e:
                logger.error(f"Async prefetch job {job_id} failed: {e}")
                with PREFETCH_JOBS_LOCK:
                    PREFETCH_JOBS[job_id]["status"] = "failed"
                    PREFETCH_JOBS[job_id].setdefault("log", []).append(str(e))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        return JsonResponse(
            {
                "success": True,
                "job_id": job_id,
                "status_url": f"/devices/audit/api/prefetch-status/{job_id}/",
            }
        )
    except Exception as e:
        logger.error(f"Error starting async prefetch: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
@admin_required
def prefetch_status(request, job_id):
    """Return status and logs for a prefetch job."""
    with PREFETCH_JOBS_LOCK:
        job = PREFETCH_JOBS.get(job_id)
    if not job:
        return JsonResponse({"error": "Job not found"}, status=404)
    # Return a copy
    return JsonResponse(
        {
            "id": job.get("id"),
            "status": job.get("status"),
            "progress": job.get("progress"),
            "log": job.get("log", [])[-50:],
            "created_at": job.get("created_at"),
        }
    )


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

        # FIRST: Check for cached AuditDeviceRecord entries
        logger.info(f"[5] Checking for cached AuditDeviceRecord entries")
        cached_devices = AuditDeviceRecord.objects.filter(audit_student=audit_student)
        cached_count = cached_devices.count()
        logger.info(f"[6] ✓ Found {cached_count} cached device records")

        if cached_count > 0:
            logger.info(f"[7] ✓ Using CACHED data - no RT API call needed")
            # Convert cached records to the expected format
            devices_data = []
            for record in cached_devices:
                devices_data.append(
                    {
                        "id": record.asset_id,
                        "Name": record.asset_tag,
                        "Description": record.asset_name,
                        "CustomFields": [
                            {"name": "Device Type", "value": record.device_type}
                        ],
                        "asset_id": record.asset_id,
                        "asset_name": record.asset_name,
                        "model_number": record.device_type,
                        "audit_status": record.audit_status,
                        "audit_notes": record.audit_notes,
                    }
                )

            logger.info(f"[8] ✓ Returning {len(devices_data)} cached devices")
            return JsonResponse(
                {
                    "student_id": audit_student.id,
                    "student_name": audit_student.name,
                    "devices": devices_data,
                    "cached": True,
                    "cache_count": cached_count,
                }
            )

        # FALLBACK: No cached data found, fetch from RT API
        logger.info(f"[7] ✗ No cached data found, fetching from RT API")

        # Get username - first try linked Student, then fallback to AuditStudent's own username
        username = None
        if audit_student.student:
            username = audit_student.student.username
            logger.info(f"[8] Using username from linked Student: {username}")
        elif audit_student.username:
            username = audit_student.username
            logger.info(f"[8] Using username from AuditStudent: {username}")
        else:
            logger.warning(
                f"[8] ✗ NO USERNAME - audit_student.student={audit_student.student}, audit_student.username={audit_student.username}"
            )

        if not username:
            logger.warning(f"[9] ✗ NO USERNAME FOUND - returning empty devices")
            return JsonResponse({"devices": [], "error": "Student has no username"})

        logger.info(f"[9] ✓ Username to use for RT lookup: {username}")

        # Use the common RT API to get devices - use username to look up RT ID
        try:
            from common.rt_api import (
                get_assets_by_owner,
                fetch_user_data,
                fetch_all_assets_cached,
                build_asset_indexes,
            )

            logger.info(f"[10] ✓ RT API imported successfully")

            logger.info(f"[11] Calling fetch_user_data('{username}')")

            # Fetch user data using username to get numeric ID
            try:
                user_data = fetch_user_data(username)
                logger.info(
                    f"[12] ✓ fetch_user_data returned: {type(user_data).__name__}"
                )
                logger.info(
                    f"    - keys: {list(user_data.keys()) if isinstance(user_data, dict) else 'N/A'}"
                )

                numeric_id = None
                hyperlinks = user_data.get("_hyperlinks", [])
                logger.info(f"[13] Hyperlinks found: {len(hyperlinks)}")

                for idx, link in enumerate(hyperlinks):
                    logger.info(
                        f"     - hyperlink[{idx}]: ref={link.get('ref')}, type={link.get('type')}, id={link.get('id')}"
                    )
                    if link.get("ref") == "self" and link.get("type") == "user":
                        numeric_id = str(link.get("id"))
                        logger.info(f"     ✓ MATCH! Using numeric_id={numeric_id}")
                        break

                if numeric_id:
                    logger.info(f"[14] Calling get_assets_by_owner('{numeric_id}')")
                    assets = get_assets_by_owner(numeric_id)
                    logger.info(
                        f"[15] ✓ get_assets_by_owner returned {len(assets)} devices"
                    )
                    for asset_idx, asset in enumerate(assets[:3]):  # Log first 3
                        logger.info(f"     - asset[{asset_idx}]: {asset}")
                    if len(assets) > 3:
                        logger.info(f"     ... and {len(assets) - 3} more devices")

                    # Create AuditDeviceRecord entries for each asset if they don't exist
                    logger.info(f"[15a] Creating/updating AuditDeviceRecord entries")
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
                        f"[14] ✗ Could not extract numeric ID from RT user {username}"
                    )
                    logger.warning(f"     Available hyperlinks: {hyperlinks}")
                    assets = []
            except Exception as user_err:
                logger.error(
                    f"[12] ✗ Exception calling fetch_user_data: {type(user_err).__name__}: {user_err}",
                    exc_info=True,
                )
                assets = []

            logger.info(f"[16] Returning JsonResponse with {len(assets)} devices")

            # If the RT lookup returned no assets, allow a forced refresh
            # via query param ?force=1 which will attempt a bulk fetch and
            # another per-owner lookup before returning.
            force = False
            try:
                force = str(request.GET.get("force", "")).lower() in (
                    "1",
                    "true",
                    "yes",
                )
            except Exception:
                force = False

            if not assets and force and numeric_id:
                request_user = request.session.get("username") or "unknown"
                remote_addr = request.META.get("REMOTE_ADDR") or "unknown"
                logger.info(
                    f"[16a] Force-refresh requested by user={request_user} remote={remote_addr}; attempting bulk refresh and retry for account {username} (rt_id={numeric_id})"
                )
                try:
                    op_start = time.time()

                    # Attempt to refresh the all-assets cache and rebuild indexes
                    refreshed_all = None
                    try:
                        t0 = time.time()
                        refreshed_all = fetch_all_assets_cached(
                            config=None, force_refresh=True
                        )
                        t1 = time.time()
                        logger.info(
                            f"[16b] Refreshed all-assets; count={len(refreshed_all)}; elapsed={t1 - t0:.2f}s"
                        )
                    except Exception as e:
                        logger.warning(f"[16b] Failed to refresh all-assets: {e}")
                        refreshed_all = None

                    if refreshed_all is not None:
                        try:
                            t2 = time.time()
                            refreshed_indexes = build_asset_indexes(refreshed_all)
                            t3 = time.time()
                            refreshed_by_owner = refreshed_indexes.get("by_owner", {})
                            assets = refreshed_by_owner.get(numeric_id, []) or assets
                            logger.info(
                                f"[16c] After bulk refresh, found {len(assets)} assets for owner {numeric_id}; index_build_elapsed={t3 - t2:.2f}s"
                            )
                        except Exception as e:
                            logger.warning(
                                f"[16c] Failed to build indexes after refresh: {e}"
                            )

                    # If still empty, try direct per-owner call again
                    if not assets:
                        try:
                            t4 = time.time()
                            assets = get_assets_by_owner(numeric_id)
                            t5 = time.time()
                            logger.info(
                                f"[16d] get_assets_by_owner retry returned {len(assets)} assets; elapsed={t5 - t4:.2f}s"
                            )
                        except Exception as e:
                            logger.warning(
                                f"[16d] get_assets_by_owner retry failed: {e}"
                            )

                    # Create AuditDeviceRecord entries for any newly found assets
                    created_count = 0
                    if assets:
                        logger.info(
                            f"[16e] Creating/updating AuditDeviceRecord entries after forced fetch (count={len(assets)})"
                        )
                        for asset in assets:
                            asset_id = asset.get("id", "")
                            asset_name = asset.get("Name", "")
                            asset_tag = asset.get("Name", "")

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
                                device_type = custom_fields.get(
                                    "Device Type", "Unknown"
                                )

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
                                created_count += 1

                    op_end = time.time()
                    logger.info(
                        f"[16f] Forced refresh flow completed for rt_id={numeric_id}; total_elapsed={op_end - op_start:.2f}s; created_records={created_count}"
                    )

                except Exception as refresh_err:
                    logger.exception(
                        f"[16f] Forced refresh attempt failed (exception): {refresh_err}"
                    )

            return JsonResponse(
                {
                    "student_id": audit_student.id,
                    "student_name": audit_student.name,
                    "devices": assets,
                    "cached": False,
                    "cache_count": 0,
                }
            )

        except ImportError as e:
            logger.error(f"[10] ✗ Could not import RT API: {e}")
            return JsonResponse({"devices": [], "error": "RT API import failed"})

    except Exception as e:
        logger.error(
            f"[X] Exception in get_audit_student_devices: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return JsonResponse({"devices": [], "error": str(e)}, status=200)
