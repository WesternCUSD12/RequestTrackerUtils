from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, send_file
from ..utils.student_check_tracker import StudentDeviceTracker
from ..utils.rt_api import find_asset_by_name, get_assets_by_owner, fetch_asset_data, rt_api_request
import logging
import json
import traceback
import os
import datetime
import io

bp = Blueprint('students', __name__)
logger = logging.getLogger(__name__)

@bp.route('/student-devices', strict_slashes=False)
def student_device_list():
    """Display the list of students and their device check-in status with grade filtering"""
    try:
        # Initialize student tracker
        tracker = StudentDeviceTracker()
        
        # Get statistics
        stats = tracker.get_statistics()
        
        # Get all students
        students = tracker.get_all_students()
        
        # Fetch RT devices for students who have rt_user_id - using numeric ID
        for student in students:
            if 'rt_user_id' in student and student['rt_user_id']:
                try:
                    # Use numeric ID directly if it's a number, otherwise try to fetch user to get numeric ID
                    if student['rt_user_id'].isdigit():
                        numeric_id = student['rt_user_id']
                        rt_devices = get_assets_by_owner(numeric_id)
                    else:
                        # For usernames, try to fetch the user first to get numeric ID
                        user_data = fetch_user_data(student['rt_user_id'])
                        
                        # Extract numeric ID from hyperlinks
                        numeric_id = None
                        hyperlinks = user_data.get('_hyperlinks', [])
                        for link in hyperlinks:
                            if link.get('ref') == 'self' and link.get('type') == 'user':
                                numeric_id = str(link.get('id'))
                                logger.info(f"Found numeric user ID: {numeric_id} for username: {student['rt_user_id']}")
                                break
                        
                        if numeric_id:
                            # Use numeric ID to fetch assets
                            rt_devices = get_assets_by_owner(numeric_id)
                        else:
                            # Fallback to username if numeric ID not found
                            rt_devices = get_assets_by_owner(student['rt_user_id'])
                            
                    student['rt_devices'] = rt_devices
                except Exception as device_err:
                    logger.warning(f"Failed to fetch RT devices for student {student.get('id')}: {device_err}")
                    student['rt_devices'] = []
            else:
                student['rt_devices'] = []
        
        # Get available grades from students
        grades = sorted(set(student.get('grade') for student in students if student.get('grade')))
        
        return render_template(
            'student_devices.html', 
            students=students, 
            stats=stats,
            grades=grades,
            current_year=tracker.current_school_year
        )
    except Exception as e:
        logger.error(f"Error loading student device list: {e}")
        logger.error(traceback.format_exc())
        
        # Check if error.html template exists
        template_exists = os.path.exists(os.path.join(
            current_app.root_path, 'templates', 'error.html'
        ))
        
        if template_exists:
            return render_template('error.html', error=f"Failed to load student device list: {str(e)}")
        else:
            return f"<h1>Error</h1><p>Failed to load student device list: {str(e)}</p>", 500

# Add a route alias for backward compatibility
@bp.route('/student-checkin', strict_slashes=False)
def student_checkin_list():
    """Redirect to the student device list for backward compatibility"""
    return redirect(url_for('students.student_device_list'))

@bp.route('/api/students', methods=['GET'])
def get_students():
    """API endpoint to get all students"""
    try:
        tracker = StudentDeviceTracker()
        students = tracker.get_all_students()
        
        # Fetch RT devices for students who have rt_user_id
        for student in students:
            if 'rt_user_id' in student and student['rt_user_id']:
                try:
                    # Use numeric ID directly if it's a number, otherwise try to fetch user to get numeric ID
                    if student['rt_user_id'].isdigit():
                        numeric_id = student['rt_user_id']
                        rt_devices = get_assets_by_owner(numeric_id)
                    else:
                        # For usernames, try to fetch the user first to get numeric ID
                        user_data = fetch_user_data(student['rt_user_id'])
                        
                        # Extract numeric ID from hyperlinks
                        numeric_id = None
                        hyperlinks = user_data.get('_hyperlinks', [])
                        for link in hyperlinks:
                            if link.get('ref') == 'self' and link.get('type') == 'user':
                                numeric_id = str(link.get('id'))
                                logger.info(f"Found numeric user ID: {numeric_id} for username: {student['rt_user_id']}")
                                break
                        
                        if numeric_id:
                            # Use numeric ID to fetch assets
                            rt_devices = get_assets_by_owner(numeric_id)
                        else:
                            # Fallback to username if numeric ID not found
                            rt_devices = get_assets_by_owner(student['rt_user_id'])
                            
                    student['rt_devices'] = rt_devices
                except Exception as device_err:
                    logger.warning(f"Failed to fetch RT devices for student {student.get('id')}: {device_err}")
                    student['rt_devices'] = []
            else:
                student['rt_devices'] = []
        
        return jsonify({
            "students": students,
            "statistics": tracker.get_statistics()
        })
        
    except Exception as e:
        logger.error(f"Error getting student list: {e}")
        return jsonify({
            "error": "Failed to get student list",
            "details": str(e)
        }), 500

@bp.route('/api/students/<student_id>', methods=['GET'])
def get_student(student_id):
    """API endpoint to get a specific student"""
    try:
        tracker = StudentDeviceTracker()
        student = tracker.get_student(student_id)
        
        if student:
            # If the student has an RT user ID, fetch their devices
            if 'rt_user_id' in student and student['rt_user_id']:
                try:
                    # Use numeric ID directly if it's a number, otherwise try to fetch user to get numeric ID
                    if student['rt_user_id'].isdigit():
                        numeric_id = student['rt_user_id']
                        rt_devices = get_assets_by_owner(numeric_id)
                    else:
                        # For usernames, try to fetch the user first to get numeric ID
                        user_data = fetch_user_data(student['rt_user_id'])
                        
                        # Extract numeric ID from hyperlinks
                        numeric_id = None
                        hyperlinks = user_data.get('_hyperlinks', [])
                        for link in hyperlinks:
                            if link.get('ref') == 'self' and link.get('type') == 'user':
                                numeric_id = str(link.get('id'))
                                logger.info(f"Found numeric user ID: {numeric_id} for username: {student['rt_user_id']}")
                                break
                        
                        if numeric_id:
                            # Use numeric ID to fetch assets
                            rt_devices = get_assets_by_owner(numeric_id)
                        else:
                            # Fallback to username if numeric ID not found
                            rt_devices = get_assets_by_owner(student['rt_user_id'])
                            
                    student['rt_devices'] = rt_devices
                except Exception as device_err:
                    logger.warning(f"Failed to fetch RT devices for student {student_id}: {device_err}")
                    student['rt_devices'] = []
            else:
                student['rt_devices'] = []
                
            return jsonify(student)
        else:
            return jsonify({
                "error": f"Student not found with ID: {student_id}"
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting student {student_id}: {e}")
        return jsonify({
            "error": f"Failed to get student information",
            "details": str(e)
        }), 500

@bp.route('/api/students', methods=['POST'])
def add_student():
    """API endpoint to add or update a student"""
    try:
        data = request.json
        student_id = data.get('id')
        
        if not student_id:
            return jsonify({
                "error": "Student ID is required"
            }), 400
            
        tracker = StudentDeviceTracker()
        
        # Create or update the student
        if tracker.add_update_student(student_id, data):
            return jsonify({
                "success": True,
                "id": student_id,
                "message": "Student added/updated successfully"
            })
        else:
            return jsonify({
                "error": "Failed to add/update student"
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding/updating student: {e}")
        return jsonify({
            "error": "Failed to add/update student",
            "details": str(e)
        }), 500

@bp.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """API endpoint to delete a student"""
    try:
        tracker = StudentDeviceTracker()
        
        if tracker.remove_student(student_id):
            return jsonify({
                "success": True,
                "message": f"Student {student_id} deleted successfully"
            })
        else:
            return jsonify({
                "error": f"Failed to delete student {student_id}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        return jsonify({
            "error": f"Failed to delete student",
            "details": str(e)
        }), 500

@bp.route('/api/students/<student_id>/check-in', methods=['POST'])
def check_in_student_device(student_id):
    """API endpoint to mark a student's device as checked in"""
    try:
        data = request.json
        asset_data = data.get('asset_data')
        
        tracker = StudentDeviceTracker()
        
        if tracker.mark_device_checked_in(student_id, asset_data):
            return jsonify({
                "success": True,
                "message": f"Device for student {student_id} marked as checked in"
            })
        else:
            return jsonify({
                "error": f"Failed to mark device as checked in for student {student_id}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error marking device checked in for student {student_id}: {e}")
        return jsonify({
            "error": "Failed to mark device as checked in",
            "details": str(e)
        }), 500

@bp.route('/api/students/<student_id>/check-out', methods=['POST'])
def check_out_student_device(student_id):
    """API endpoint to mark a student's device as not checked in"""
    try:
        tracker = StudentDeviceTracker()
        
        if tracker.mark_device_not_checked_in(student_id):
            return jsonify({
                "success": True,
                "message": f"Device for student {student_id} marked as not checked in"
            })
        else:
            return jsonify({
                "error": f"Failed to mark device as not checked in for student {student_id}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error marking device not checked in for student {student_id}: {e}")
        return jsonify({
            "error": "Failed to mark device as not checked in",
            "details": str(e)
        }), 500

@bp.route('/student-import', methods=['GET', 'POST'])
def student_import():
    """Import students from a CSV file"""
    if request.method == 'GET':
        # Show the import form
        return render_template('student_import.html')
    else:
        try:
            # Process the uploaded file
            if 'file' not in request.files:
                return render_template('student_import.html', error="No file part")
                
            file = request.files['file']
            
            if file.filename == '':
                return render_template('student_import.html', error="No file selected")
                
            if not file.filename.endswith('.csv'):
                return render_template('student_import.html', error="File must be a CSV")
            
            # Save the file to a temporary location
            temp_file = os.path.join(current_app.instance_path, 'tmp_import.csv')
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            file.save(temp_file)
            
            # Process the file
            tracker = StudentDeviceTracker()
            result = tracker.import_students_from_csv(temp_file)
            
            # Remove the temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            if result.get('success'):
                return render_template(
                    'student_import.html', 
                    success=True, 
                    added=result.get('added', 0),
                    updated=result.get('updated', 0),
                    failed=result.get('failed', 0)
                )
            else:
                return render_template('student_import.html', error=result.get('error', 'Unknown error'))
                
        except Exception as e:
            logger.error(f"Error importing students: {e}")
            logger.error(traceback.format_exc())
            return render_template('student_import.html', error=str(e))

@bp.route('/student-export', methods=['GET'])
def student_export():
    """Export students to a CSV file"""
    try:
        include_device_info = request.args.get('include_device_info', 'true').lower() == 'true'
        
        tracker = StudentDeviceTracker()
        csv_data = tracker.export_students_to_csv(include_device_info)
        
        if not csv_data:
            return "No student data available", 404
            
        # Create an in-memory file
        buffer = io.BytesIO()
        buffer.write(csv_data.encode('utf-8'))
        buffer.seek(0)
        
        # Generate a filename with the current date
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        filename = f"student_device_checkins_{today}.csv"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error exporting students: {e}")
        return jsonify({
            "error": "Failed to export student data",
            "details": str(e)
        }), 500

@bp.route('/api/rt-lookup/student/<student_id>', methods=['GET'])
def rt_lookup_student_devices(student_id):
    """API endpoint to look up a student's devices in RT"""
    try:
        # Get the RT user ID from query parameters
        rt_user_id = request.args.get('rt_user_id')
        
        if not rt_user_id:
            return jsonify({
                "error": "RT user ID is required"
            }), 400
            
        # Use numeric ID directly if it's a number, otherwise try to fetch user to get numeric ID
        if rt_user_id.isdigit():
            numeric_id = rt_user_id
            assets = get_assets_by_owner(numeric_id)
            logger.info(f"Using provided numeric ID: {numeric_id}")
        else:
            try:
                # For usernames, try to fetch the user first to get numeric ID
                from ..utils.rt_api import fetch_user_data
                logger.info(f"Looking up numeric ID for username: {rt_user_id}")
                user_data = fetch_user_data(rt_user_id)
                
                # Extract numeric ID from hyperlinks
                numeric_id = None
                hyperlinks = user_data.get('_hyperlinks', [])
                for link in hyperlinks:
                    if link.get('ref') == 'self' and link.get('type') == 'user':
                        numeric_id = str(link.get('id'))
                        logger.info(f"Found numeric user ID: {numeric_id} for username: {rt_user_id}")
                        break
                
                if numeric_id:
                    # Use numeric ID to fetch assets
                    logger.info(f"Using numeric ID {numeric_id} to fetch assets for {rt_user_id}")
                    assets = get_assets_by_owner(numeric_id)
                else:
                    # Fallback to username if numeric ID not found
                    logger.warning(f"Could not find numeric ID for {rt_user_id}, falling back to username")
                    assets = get_assets_by_owner(rt_user_id)
            except Exception as user_err:
                logger.error(f"Error fetching user data for {rt_user_id}: {user_err}")
                # Fallback to username
                assets = get_assets_by_owner(rt_user_id)
        
        # Return the assets
        return jsonify({
            "student_id": student_id,
            "rt_user_id": rt_user_id,
            "assets": assets
        })
        
    except Exception as e:
        logger.error(f"Error looking up RT devices for student {student_id}: {e}")
        return jsonify({
            "error": "Failed to look up devices in RT",
            "details": str(e)
        }), 500

@bp.route('/api/students/clear-all', methods=['POST'])
def clear_all_students():
    """API endpoint to clear all students"""
    try:
        tracker = StudentDeviceTracker()
        result = tracker.clear_all_students()
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "message": f"Successfully cleared {result.get('count', 0)} students",
                "count": result.get('count', 0)
            })
        else:
            return jsonify({
                "error": result.get('error', 'Unknown error occurred')
            }), 500
            
    except Exception as e:
        logger.error(f"Error clearing students: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Failed to clear student data",
            "details": str(e)
        }), 500

@bp.route('/api/students/filter', methods=['GET'])
def filter_students():
    """API endpoint to filter students by multiple grades"""
    try:
        # Get filter parameters
        grades = request.args.getlist('grade')
        status = request.args.get('status')
        search = request.args.get('search')
        
        tracker = StudentDeviceTracker()
        all_students = tracker.get_all_students()
        
        # Filter students based on parameters
        filtered_students = []
        for student in all_students:
            # Filter by grade (if specified)
            if grades and student.get('grade') not in grades:
                continue
                
            # Filter by status (if specified)
            if status == 'checked_in' and not student.get('device_checked_in'):
                continue
            elif status == 'not_checked_in' and student.get('device_checked_in'):
                continue
                
            # Filter by search term (if specified)
            if search:
                search_lower = search.lower()
                first_name = student.get('first_name', '').lower()
                last_name = student.get('last_name', '').lower()
                student_id = str(student.get('id', '')).lower()
                
                if (search_lower not in first_name and 
                    search_lower not in last_name and
                    search_lower not in student_id and
                    search_lower not in f"{first_name} {last_name}"):
                    continue
            
            filtered_students.append(student)
        
        return jsonify({
            "students": filtered_students,
            "count": len(filtered_students),
            "total": len(all_students)
        })
        
    except Exception as e:
        logger.error(f"Error filtering students: {e}")
        return jsonify({
            "error": "Failed to filter students",
            "details": str(e)
        }), 500

@bp.route('/api/students/check-rt-assignments', methods=['POST'])
def check_rt_assignments():
    """
    Check all students in RT to see if they have devices assigned to them.
    If a student has no devices in RT, mark them as 'Checked In'.
    """
    try:
        tracker = StudentDeviceTracker()
        students = tracker.get_all_students()
        
        # Track students who were updated
        updated_count = 0
        
        # Process each student who has an RT user ID and is not already checked in
        for student in students:
            # Skip students who are already checked in
            if student.get('device_checked_in'):
                continue
                
            # Skip students without an RT user ID
            if not student.get('rt_user_id'):
                continue
                
            try:
                # Get student's RT devices
                rt_user_id = student.get('rt_user_id')
                
                # Use numeric ID directly if it's a number, otherwise try to fetch user to get numeric ID
                if rt_user_id.isdigit():
                    numeric_id = rt_user_id
                    rt_devices = get_assets_by_owner(numeric_id)
                else:
                    # For usernames, try to fetch the user first to get numeric ID
                    try:
                        from ..utils.rt_api import fetch_user_data
                        user_data = fetch_user_data(rt_user_id)
                        
                        # Extract numeric ID from hyperlinks
                        numeric_id = None
                        hyperlinks = user_data.get('_hyperlinks', [])
                        for link in hyperlinks:
                            if link.get('ref') == 'self' and link.get('type') == 'user':
                                numeric_id = str(link.get('id'))
                                logger.info(f"Found numeric user ID: {numeric_id} for username: {rt_user_id}")
                                break
                        
                        if numeric_id:
                            # Use numeric ID to fetch assets
                            rt_devices = get_assets_by_owner(numeric_id)
                        else:
                            # Fallback to username if numeric ID not found
                            rt_devices = get_assets_by_owner(rt_user_id)
                    except Exception as user_err:
                        logger.error(f"Error fetching user data for {rt_user_id}: {user_err}")
                        # Fallback to username
                        rt_devices = get_assets_by_owner(rt_user_id)
                
                # If student has no devices in RT, mark them as checked in
                if not rt_devices:
                    logger.info(f"Student {student.get('id')} has no devices in RT - marking as checked in")
                    if tracker.mark_device_checked_in(student.get('id'), None, is_auto_checkin=True):
                        updated_count += 1
                        
            except Exception as e:
                logger.warning(f"Error processing RT devices for student {student.get('id')}: {e}")
                continue
        
        return jsonify({
            "success": True,
            "updated": updated_count,
            "message": f"Updated {updated_count} students with no devices in RT"
        })
        
    except Exception as e:
        logger.error(f"Error checking RT assignments: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Failed to check RT assignments",
            "details": str(e)
        }), 500