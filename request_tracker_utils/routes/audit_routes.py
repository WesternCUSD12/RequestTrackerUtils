"""Audit routes for student device verification.

Blueprint: audit
URL Prefix: /devices (set during registration in __init__.py)
Routes accessible at: /devices/audit/*
"""

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app
import os
import tempfile
import time
from werkzeug.utils import secure_filename
from ..utils.csv_validator import parse_audit_csv, validate_required_columns, detect_duplicates, detect_encoding
from ..utils.audit_tracker import AuditTracker
from ..utils.rt_api import get_assets_by_owner, fetch_user_data
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('audit', __name__)
tracker = AuditTracker()

@bp.route('/audit')
def audit_index():
    """Audit upload page with statistics - redirects to active session if one exists"""
    # Allow forcing upload form with ?upload=true query parameter
    force_upload = request.args.get('upload', '').lower() == 'true'
    
    stats = tracker.get_statistics()
    
    # If there's an active session with students, redirect to it (unless forced to show upload)
    if not force_upload and stats.get('session_id') and stats.get('total_students', 0) > 0:
        return redirect(url_for('audit.view_session', session_id=stats['session_id']))
    
    return render_template('audit_upload.html', stats=stats)

@bp.route('/audit/upload', methods=['POST'])
def upload_csv():
    """
    POST /audit/upload
    Accepts CSV file upload, validates, creates audit session
    Returns: JSON with session_id and student_count or error details
    """
    # Check if file is in request
    if 'file' not in request.files:
        logger.warning("CSV upload failed: No file in request")
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.warning("CSV upload failed: Empty filename")
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        logger.warning(f"CSV upload failed: Invalid file type {file.filename}")
        return jsonify({'error': 'Invalid file type. Only CSV files are allowed'}), 400
    
    # Get creator name from form (default to 'Unknown' if not provided)
    creator_name = request.form.get('creator_name', 'Unknown')
    
    # Sanitize creator name
    import html
    creator_name = html.escape(creator_name.strip())
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        # Check file size (<5MB)
        file_size = os.path.getsize(tmp_path)
        if file_size > 5 * 1024 * 1024:  # 5MB in bytes
            os.unlink(tmp_path)
            logger.warning(f"CSV upload failed: File too large ({file_size} bytes)")
            return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400
        
        # Parse CSV with max 1000 students (encoding detection happens inside parse_audit_csv)
        students, errors = parse_audit_csv(tmp_path, max_rows=1000)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if errors:
            logger.error(f"CSV validation failed for {creator_name}: {errors}")
            return jsonify({'error': 'CSV validation failed', 'details': errors}), 400
        
        if not students:
            logger.warning(f"CSV upload failed: No valid students found for {creator_name}")
            return jsonify({'error': 'No valid student records found in CSV'}), 400
        
        # Check row count
        if len(students) > 1000:
            logger.warning(f"CSV upload failed: Too many students ({len(students)}) for {creator_name}")
            return jsonify({'error': f'Too many students. Maximum is 1000, found {len(students)}'}), 400
        
        # Validate required columns
        if students:
            headers = list(students[0].keys())
            is_valid, error_msg = validate_required_columns(headers)
            if not is_valid:
                logger.error(f"CSV validation failed: {error_msg}")
                return jsonify({'error': error_msg}), 400
        
        # Detect duplicates
        duplicates = detect_duplicates(students)
        
        # If duplicates found, return for user confirmation
        if duplicates:
            logger.warning(f"Duplicate students detected in upload from {creator_name}: {len(duplicates)} duplicates")
            return jsonify({
                'warning': 'Duplicate students detected',
                'duplicates': duplicates,
                'students': students,
                'require_confirmation': True
            }), 200
        
        # Create or get active audit session (single session model)
        session_id = tracker.get_or_create_active_session(creator_name)
        
        # Replace students in the active session
        tracker.replace_students(session_id, students, creator_name)
        
        logger.info(f"Audit session {session_id} updated by {creator_name} with {len(students)} students")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'student_count': len(students)
        }), 201
        
    except Exception as e:
        # Clean up temp file if it exists
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        logger.error(f"CSV upload error for {creator_name}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/audit/session/<session_id>')
def view_session(session_id):
    """
    GET /audit/session/<session_id>
    Renders main audit interface template with student list
    """
    try:
        session = tracker.get_session(session_id)
        if not session:
            return "Session not found", 404
        
        stats = tracker.get_statistics()
        return render_template('audit_upload.html', session=session, session_id=session_id, stats=stats)
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        return f"Server error: {str(e)}", 500

@bp.route('/audit/session/<session_id>/students')
def get_students(session_id):
    """
    GET /audit/session/<session_id>/students
    Returns JSON student list with optional filtering
    Query params:
    - search: filter by name/grade/advisor
    - audited: 'true' or 'false' to filter by audit status (default: 'false')
    """
    try:
        session = tracker.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get query parameters
        search_query = request.args.get('search', '').strip().lower()
        audited_filter = request.args.get('audited', 'false').lower() == 'true'
        
        # Get all students for this session
        students = tracker.get_students_by_session(session_id)
        
        # Filter by audited status
        students = [s for s in students if s.get('audited', 0) == (1 if audited_filter else 0)]
        
        # Apply search filter if provided
        if search_query:
            students = [
                s for s in students
                if search_query in s.get('name', '').lower()
                or search_query in s.get('grade', '').lower()
                or search_query in s.get('advisor', '').lower()
            ]
        
        return jsonify({
            'students': students,
            'total_count': len(students),
            'session_id': session_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/audit/student/<int:student_id>')
def view_student(student_id):
    """
    GET /audit/student/<student_id>
    Renders audit verification template with student info
    """
    try:
        student = tracker.get_student(student_id)
        if not student:
            return "Student not found", 404
        
        return render_template('audit_verify.html', student=student)
    except Exception as e:
        logger.error(f"Error viewing student {student_id}: {e}")
        return f"Server error: {str(e)}", 500

@bp.route('/audit/student/<int:student_id>/devices')
def get_student_devices(student_id):
    """
    GET /audit/student/<student_id>/devices
    Queries RT for student's assigned devices with retry logic
    Returns: JSON device list or error
    """
    try:
        student = tracker.get_student(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        logger.debug(f"Student record: {dict(student)}")
        
        # Use username field for RT lookup (e.g., 'asurratt'), fallback to name if username is empty
        rt_username = student.get('username', '').strip()
        student_name = student.get('name')
        
        logger.debug(f"rt_username='{rt_username}', student_name='{student_name}'")
        
        if not rt_username:
            # If no username provided, try to use the name (legacy behavior)
            if not student_name:
                return jsonify({'error': 'No username or name found for student'}), 400
            lookup_value = student_name
        else:
            lookup_value = rt_username
        
        logger.info(f"Using lookup_value='{lookup_value}' for RT API")
        
        # Resolve student username to RT user ID with retries
        user_data = None
        retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
        
        for attempt, delay in enumerate(retry_delays + [0], start=1):
            try:
                logger.info(f"Attempt {attempt} to fetch user data for {lookup_value}")
                user_data = fetch_user_data(lookup_value)
                if user_data:
                    break
                else:
                    logger.warning(f"User {lookup_value} not found in RT (attempt {attempt})")
                    if attempt < len(retry_delays) + 1:
                        time.sleep(delay)
            except Exception as e:
                logger.error(f"RT API error fetching user {lookup_value} (attempt {attempt}): {e}")
                if attempt < len(retry_delays) + 1:
                    time.sleep(delay)
                else:
                    raise
        
        if not user_data:
            return jsonify({
                'error': 'Student not found in Request Tracker',
                'student_name': student_name,
                'username': rt_username,
                'devices': []
            }), 200
        
        # Get assets assigned to this user with retries
        devices = None
        for attempt, delay in enumerate(retry_delays + [0], start=1):
            try:
                logger.info(f"Attempt {attempt} to fetch devices for user {user_data.get('id')}")
                devices = get_assets_by_owner(user_data.get('Name'))
                if devices is not None:
                    break
                if attempt < len(retry_delays) + 1:
                    time.sleep(delay)
            except Exception as e:
                logger.error(f"RT API error fetching devices (attempt {attempt}): {e}")
                if attempt < len(retry_delays) + 1:
                    time.sleep(delay)
                else:
                    # Return 502 Bad Gateway for RT unavailable
                    return jsonify({
                        'error': 'Request Tracker unavailable',
                        'details': str(e)
                    }), 502
        
        if devices is None:
            return jsonify({
                'error': 'Failed to fetch devices after retries',
                'devices': []
            }), 504  # Gateway timeout
        
        # Format devices for response
        formatted_devices = []
        for device in devices:
            formatted_devices.append({
                'id': device.get('id'),
                'asset_tag': device.get('Name', 'Unknown'),
                'serial_number': device.get('CF.{Serial Number}', 'Unknown'),
                'device_type': device.get('CF.{Asset Type}', 'Unknown'),
                'verified': False  # Default to unverified
            })
        
        return jsonify({
            'devices': formatted_devices,
            'student_name': student_name,
            'rt_user_id': user_data.get('id')
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching devices for student {student_id}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/audit/student/<int:student_id>/verify', methods=['POST'])
def verify_student(student_id):
    """
    POST /audit/student/<student_id>/verify
    Accepts verified device IDs and notes, marks student as audited
    Request body:
    {
        "auditor_name": "Teacher Name",
        "device_records": [
            {"asset_id": "123", "asset_tag": "W12-00001", "serial_number": "ABC123", "device_type": "Chromebook", "verified": true}
        ],
        "notes": "Optional notes"
    }
    """
    try:
        # Validate session_id format (UUID)
        import re
        if not re.match(r'^\d+$', str(student_id)):
            logger.warning(f"Invalid student_id format: {student_id}")
            return jsonify({'error': 'Invalid student ID format'}), 400
        
        student = tracker.get_student(student_id)
        if not student:
            logger.warning(f"Student not found: {student_id}")
            return jsonify({'error': 'Student not found'}), 404
        
        data = request.get_json()
        if not data:
            logger.warning(f"No data provided for student {student_id}")
            return jsonify({'error': 'No data provided'}), 400
        
        auditor_name = data.get('auditor_name', 'Unknown')
        device_records = data.get('device_records', [])
        notes = data.get('notes', '')
        
        # Sanitize inputs
        import html
        auditor_name = html.escape(auditor_name.strip())
        notes = html.escape(notes.strip())
        
        # Validate all devices are verified if devices exist
        if device_records:
            unverified = [d for d in device_records if not d.get('verified')]
            if unverified:
                logger.warning(f"Incomplete audit submission for student {student_id}: {len(unverified)} unverified devices")
                return jsonify({
                    'error': 'All devices must be verified',
                    'unverified_count': len(unverified)
                }), 400
        
        # Mark student as audited
        tracker.mark_student_audited(
            student_id=student_id,
            auditor_name=auditor_name,
            device_records=device_records,
            notes=notes
        )
        
        logger.info(f"Audit completed for student {student_id} ({student.get('name')}) by {auditor_name} with {len(device_records)} devices")
        
        return jsonify({
            'success': True,
            'message': 'Audit submitted successfully',
            'student_id': student_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error verifying student {student_id}: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/audit/session/<session_id>/completed')
def view_completed(session_id):
    """
    GET /audit/session/<session_id>/completed
    View completed audits for a session (User Story 3)
    """
    try:
        session = tracker.get_session(session_id)
        if not session:
            return "Session not found", 404
        
        completed_students = tracker.get_completed_audits(session_id)
        
        return render_template('audit_history.html', 
                             session=session, 
                             session_id=session_id,
                             students=completed_students)
        
    except Exception as e:
        logger.error(f"Error viewing completed audits for session {session_id}: {e}")
        return f"Server error: {str(e)}", 500

@bp.route('/audit/student/<int:student_id>/re-audit', methods=['POST'])
def reaudit_student(student_id):
    """
    POST /audit/student/<student_id>/re-audit
    Restore a student for re-audit
    """
    try:
        student = tracker.get_student(student_id)
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        if not student.get('audited'):
            return jsonify({'error': 'Student is not marked as audited'}), 400
        
        tracker.restore_student_for_reaudit(student_id)
        
        logger.info(f"Student {student_id} restored for re-audit")
        
        return jsonify({
            'success': True,
            'message': 'Student restored for re-audit',
            'student_id': student_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error restoring student {student_id} for re-audit: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@bp.route('/audit/notes')
def view_notes():
    """
    GET /audit/notes
    View IT staff notes report (User Story 4)
    Query params: session_id, date_from, date_to
    """
    try:
        session_id = request.args.get('session_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Get all notes with optional filtering
        notes = tracker.get_all_notes(
            session_id=session_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return render_template('audit_report.html', notes=notes)
        
    except Exception as e:
        logger.error(f"Error fetching notes: {e}")
        return f"Server error: {str(e)}", 500

@bp.route('/audit/notes/export')
def export_notes():
    """
    GET /audit/notes/export
    Export IT notes as CSV
    Query params: session_id, date_from, date_to
    """
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        session_id = request.args.get('session_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        notes = tracker.get_all_notes(
            session_id=session_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Create CSV in memory
        si = StringIO()
        writer = csv.writer(si)
        
        # Write header
        writer.writerow(['Student', 'Grade', 'Advisor', 'Note', 'Devices', 'Missing Devices', 'Date', 'Auditor'])
        
        # Write data
        for note in notes:
            writer.writerow([
                note.get('student_name', ''),
                note.get('grade', ''),
                note.get('advisor', ''),
                note.get('note_text', ''),
                note.get('total_devices', 0),
                note.get('missing_devices', 0),
                note.get('created_at', ''),
                note.get('auditor_name', '')
            ])
        
        # Create response
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=audit_notes.csv"
        output.headers["Content-type"] = "text/csv"
        
        return output
        
    except Exception as e:
        logger.error(f"Error exporting notes: {e}")
        return f"Server error: {str(e)}", 500

@bp.route('/audit/clear', methods=['POST'])
def clear_audit_data():
    """
    POST /audit/clear
    Clear all audit-related data from the database
    Returns: JSON with counts of deleted records
    """
    try:
        result = tracker.clear_all_audit_data()
        
        if result.get('success'):
            logger.info(f"Audit data cleared: {result['sessions_deleted']} sessions, {result['students_deleted']} students, {result['devices_deleted']} devices, {result['notes_deleted']} notes")
            return jsonify(result), 200
        else:
            logger.error(f"Failed to clear audit data: {result.get('error')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error clearing audit data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

