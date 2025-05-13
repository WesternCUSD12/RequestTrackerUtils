import csv
import os
import time
import fcntl
import datetime
import logging
from pathlib import Path
from flask import current_app
import json
import io
from .db import get_db_connection

logger = logging.getLogger(__name__)

class StudentDeviceTracker:
    """Utility for tracking student device check-ins across the school year"""
    
    def __init__(self, data_dir=None):
        """Initialize the tracker"""
        # Determine the current school year (Aug-Jul)
        today = datetime.datetime.now()
        if today.month >= 8:  # August and later is new school year
            start_year = today.year
        else:
            start_year = today.year - 1
        self.current_school_year = f"{start_year}-{start_year + 1}"
        
        # Set up the data directory
        if data_dir is None:
            try:
                data_dir = Path(current_app.instance_path) / 'student_data'
                data_dir.mkdir(parents=True, exist_ok=True)
                self.student_data_path = data_dir
            except Exception as e:
                logger.error(f"Error setting up data directory from Flask app: {e}")
                try:
                    # Import is already at the top level, no need to import here again
                    instance_data_dir = Path(current_app.instance_path) / 'student_data'
                    instance_data_dir.mkdir(parents=True, exist_ok=True)
                    self.student_data_path = instance_data_dir
                    logger.info(f"Using alternative student data directory: {self.student_data_path}")
                except Exception as nested_e:
                    logger.error(f"Failed to create student data directory: {nested_e}")
                    raise
        else:
            self.student_data_path = Path(data_dir)
            self.student_data_path.mkdir(parents=True, exist_ok=True)
        
        # Define the path for the current school year's tracking file
        self._set_current_year_file()
        
        # If migrating from JSON, check if we need to import existing data
        self._migrate_json_to_sqlite_if_needed()
    
    def _set_current_year_file(self):
        """Set the current school year's tracking file"""
        filename = f"student_devices_{self.current_school_year}.json"
        self.current_tracker_file = str(self.student_data_path / filename)
        
        # Create the file if it doesn't exist
        if not os.path.exists(self.current_tracker_file):
            self._create_new_tracker_file()
    
    def _create_new_tracker_file(self):
        """Create a new student device tracker file"""
        try:
            # Initialize with an empty dictionary
            tracker_data = {
                "school_year": self.current_school_year,
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat(),
                "students": {}
            }
            
            with open(self.current_tracker_file, 'w') as f:
                json.dump(tracker_data, f, indent=2)
                
            logger.info(f"Created new student device tracker file: {self.current_tracker_file}")
        except Exception as e:
            logger.error(f"Error creating new tracker file: {e}")
            raise
    
    def _load_tracker_data(self):
        """Load the current tracker data (for compatibility or migration)"""
        try:
            with open(self.current_tracker_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tracker data: {e}")
            return None
    
    def _save_tracker_data(self, data):
        """Save tracker data to file with locking for concurrency (for compatibility)"""
        try:
            # Update the last updated timestamp
            data["last_updated"] = datetime.datetime.now().isoformat()
            
            # Write to file with file locking
            with open(self.current_tracker_file, 'w') as f:
                # Use file locking to prevent concurrent write issues
                fcntl.flock(f, fcntl.LOCK_EX)
                
                try:
                    json.dump(data, f, indent=2)
                finally:
                    # Always release the lock
                    fcntl.flock(f, fcntl.LOCK_UN)
                    
            logger.info(f"Saved student device tracker data")
            return True
        except Exception as e:
            logger.error(f"Error saving tracker data: {e}")
            return False
            
    def _migrate_json_to_sqlite_if_needed(self):
        """Check if we need to migrate data from JSON to SQLite"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if students table is empty
            cursor.execute("SELECT COUNT(*) FROM students")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Table is empty, check if we have JSON data to migrate
                json_data = self._load_tracker_data()
                if json_data and "students" in json_data and json_data["students"]:
                    logger.info("Migrating student data from JSON to SQLite")
                    
                    for student_id, student_data in json_data["students"].items():
                        # Extract device info from the student data
                        device_info = student_data.pop("device_info", None)
                        device_checked_in = 1 if student_data.get("device_checked_in", False) else 0
                        
                        # Insert student
                        cursor.execute(
                            """
                            INSERT INTO students (
                                id, first_name, last_name, grade, rt_user_id, 
                                device_checked_in, check_in_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                student_id,
                                student_data.get("first_name"),
                                student_data.get("last_name"),
                                student_data.get("grade"),
                                student_data.get("rt_user_id"),
                                device_checked_in,
                                student_data.get("check_in_date")
                            )
                        )
                        
                        # Insert device info if available
                        if device_info:
                            cursor.execute(
                                """
                                INSERT INTO device_info (
                                    student_id, asset_id, asset_tag, device_type,
                                    serial_number, check_in_timestamp
                                ) VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    student_id,
                                    device_info.get("asset_id"),
                                    device_info.get("asset_tag"),
                                    device_info.get("device_type"),
                                    device_info.get("serial_number"),
                                    device_info.get("check_in_timestamp")
                                )
                            )
                    
                    conn.commit()
                    logger.info(f"Successfully migrated {len(json_data['students'])} students from JSON to SQLite")
            else:
                logger.info(f"SQLite database already contains {count} students, no migration needed")
                
        except Exception as e:
            logger.error(f"Error checking/migrating JSON data to SQLite: {e}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
                
    def get_all_students(self):
        """
        Get all students in the tracking system
        
        Returns:
            list: List of student data dictionaries
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get all students
            cursor.execute("""
                SELECT s.*, 
                       d.asset_id, d.asset_tag, d.device_type, 
                       d.serial_number, d.check_in_timestamp 
                FROM students s
                LEFT JOIN device_info d ON s.id = d.student_id
            """)
            
            rows = cursor.fetchall()
            students = []
            
            # Process the results into a list of dictionaries
            for row in rows:
                student = dict(row)
                student['device_checked_in'] = bool(student['device_checked_in'])
                
                # Add device_info if available
                if student['asset_id']:
                    student['device_info'] = {
                        'asset_id': student['asset_id'],
                        'asset_tag': student['asset_tag'],
                        'device_type': student['device_type'],
                        'serial_number': student['serial_number'],
                        'check_in_timestamp': student['check_in_timestamp']
                    }
                
                # Remove the extra fields that were joined from device_info
                for field in ['asset_id', 'asset_tag', 'device_type', 'serial_number', 'check_in_timestamp']:
                    if field in student:
                        del student[field]
                
                students.append(student)
            
            # Sort by last name, then first name
            return sorted(students, key=lambda s: (s.get("last_name", ""), s.get("first_name", "")))
            
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_student(self, student_id):
        """
        Get a specific student's data
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            dict: Student data or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get the student
            cursor.execute("""
                SELECT s.*, 
                       d.asset_id, d.asset_tag, d.device_type, 
                       d.serial_number, d.check_in_timestamp 
                FROM students s
                LEFT JOIN device_info d ON s.id = d.student_id
                WHERE s.id = ?
            """, (student_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            student = dict(row)
            student['device_checked_in'] = bool(student['device_checked_in'])
            
            # Add device_info if available
            if student['asset_id']:
                student['device_info'] = {
                    'asset_id': student['asset_id'],
                    'asset_tag': student['asset_tag'],
                    'device_type': student['device_type'],
                    'serial_number': student['serial_number'],
                    'check_in_timestamp': student['check_in_timestamp']
                }
            
            # Remove the extra fields that were joined from device_info
            for field in ['asset_id', 'asset_tag', 'device_type', 'serial_number', 'check_in_timestamp']:
                if field in student:
                    del student[field]
            
            return student
            
        except Exception as e:
            logger.error(f"Error getting student {student_id}: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def add_update_student(self, student_id, student_data):
        """
        Add or update a student
        
        Args:
            student_id (str): Student ID or username
            student_data (dict): Student data
            
        Returns:
            bool: Success status
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if the student exists
            cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update the student
                update_fields = []
                params = []
                
                # Prepare update fields and params
                for field in ['first_name', 'last_name', 'grade', 'rt_user_id']:
                    if field in student_data:
                        update_fields.append(f"{field} = ?")
                        params.append(student_data[field])
                
                if update_fields:
                    # Add the student_id as the last parameter
                    params.append(student_id)
                    
                    # Execute the update
                    cursor.execute(
                        f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?",
                        params
                    )
            else:
                # Insert new student
                cursor.execute(
                    """
                    INSERT INTO students (
                        id, first_name, last_name, grade, rt_user_id, 
                        device_checked_in, check_in_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        student_data.get("first_name"),
                        student_data.get("last_name"),
                        student_data.get("grade"),
                        student_data.get("rt_user_id"),
                        0,  # Default to device not checked in
                        None  # Default to no check-in date
                    )
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error adding/updating student {student_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def remove_student(self, student_id):
        """
        Remove a student from the tracking system
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            bool: Success status
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Delete the student (device_info will be deleted via ON DELETE CASCADE)
            cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
            
            # Check if any rows were affected
            affected = cursor.rowcount > 0
            
            conn.commit()
            return affected
            
        except Exception as e:
            logger.error(f"Error removing student {student_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def mark_device_checked_in(self, student_id, asset_data=None):
        """
        Mark a student's device as checked in
        
        Args:
            student_id (str): Student ID or username
            asset_data (dict): Asset data from RT
            
        Returns:
            bool: Success status
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update the student's check-in status
            check_in_date = datetime.datetime.now().isoformat()
            cursor.execute(
                "UPDATE students SET device_checked_in = 1, check_in_date = ? WHERE id = ?",
                (check_in_date, student_id)
            )
            
            # Delete any existing device info
            cursor.execute("DELETE FROM device_info WHERE student_id = ?", (student_id,))
            
            # Add device info if provided
            if asset_data:
                device_type = ""
                serial_number = ""
                
                # Extract device type and serial from CustomFields
                if 'CustomFields' in asset_data:
                    for field in asset_data['CustomFields']:
                        if field.get('name') == 'Type' and field.get('values'):
                            device_type = field['values'][0]
                        elif field.get('name') == 'Serial Number' and field.get('values'):
                            serial_number = field['values'][0]
                
                # Insert device info
                cursor.execute(
                    """
                    INSERT INTO device_info (
                        student_id, asset_id, asset_tag, device_type,
                        serial_number, check_in_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student_id,
                        asset_data.get("id", ""),
                        asset_data.get("Name", ""),
                        device_type,
                        serial_number,
                        datetime.datetime.now().isoformat()
                    )
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error marking device checked in for student {student_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def mark_device_not_checked_in(self, student_id):
        """
        Mark a student's device as not checked in
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            bool: Success status
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update the student's check-in status
            cursor.execute(
                "UPDATE students SET device_checked_in = 0, check_in_date = NULL WHERE id = ?",
                (student_id,)
            )
            
            # Delete any device info
            cursor.execute("DELETE FROM device_info WHERE student_id = ?", (student_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error marking device not checked in for student {student_id}: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def import_students_from_csv(self, csv_file):
        """
        Import students from a CSV file
        
        Args:
            csv_file (str): Path to CSV file
            
        Returns:
            dict: Result with counts of added, updated, and failed
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            added = 0
            updated = 0
            failed = 0
            
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Get student ID from the row
                        student_id = row.get('id', '').strip()
                        
                        if not student_id:
                            logger.warning(f"Skipping row, no student ID found: {row}")
                            failed += 1
                            continue
                        
                        # Prepare student data
                        student_data = {}
                        for key, value in row.items():
                            if key != 'id' and value:  # Skip empty values
                                student_data[key] = value
                        
                        # Check if student exists
                        cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
                        exists = cursor.fetchone() is not None
                        
                        if exists:
                            # Update existing student
                            update_fields = []
                            params = []
                            
                            # Prepare update fields and params
                            for field in ['first_name', 'last_name', 'grade', 'rt_user_id']:
                                if field in student_data:
                                    update_fields.append(f"{field} = ?")
                                    params.append(student_data[field])
                            
                            if update_fields:
                                # Add the student_id as the last parameter
                                params.append(student_id)
                                
                                # Execute the update
                                cursor.execute(
                                    f"UPDATE students SET {', '.join(update_fields)} WHERE id = ?",
                                    params
                                )
                                updated += 1
                        else:
                            # Insert new student
                            cursor.execute(
                                """
                                INSERT INTO students (
                                    id, first_name, last_name, grade, rt_user_id, 
                                    device_checked_in, check_in_date
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    student_id,
                                    student_data.get("first_name"),
                                    student_data.get("last_name"),
                                    student_data.get("grade"),
                                    student_data.get("rt_user_id"),
                                    0,  # Default to device not checked in
                                    None  # Default to no check-in date
                                )
                            )
                            added += 1
                    
                    except Exception as row_error:
                        logger.error(f"Error processing student row: {row_error}")
                        failed += 1
            
            conn.commit()
            
            return {
                "success": True,
                "added": added,
                "updated": updated,
                "failed": failed
            }
                
        except Exception as e:
            logger.error(f"Error importing students from CSV: {e}")
            if 'conn' in locals():
                conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if 'conn' in locals():
                conn.close()
    
    def export_students_to_csv(self, include_device_info=True):
        """
        Export students to a CSV file
        
        Args:
            include_device_info (bool): Whether to include device info in the export
            
        Returns:
            str: CSV data
        """
        try:
            # Get all students
            students = self.get_all_students()
            
            if not students:
                return ""
            
            # Determine fields to include
            fieldnames = ["id", "first_name", "last_name", "grade", "rt_user_id"]
            
            if include_device_info:
                fieldnames.extend(["device_checked_in", "check_in_date"])
                
                # Check if any student has device info
                has_device_info = any("device_info" in student for student in students)
                
                if has_device_info:
                    fieldnames.extend(["asset_id", "asset_tag", "device_type", "serial_number"])
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write student data
            for student in students:
                row = {}
                # Include basic student fields
                for field in fieldnames:
                    if field in student:
                        row[field] = student[field]
                    elif include_device_info and "device_info" in student and field in student["device_info"]:
                        # Include device info fields
                        row[field] = student["device_info"][field]
                    else:
                        row[field] = ""
                writer.writerow(row)
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error exporting students to CSV: {e}")
            return ""
    
    def get_student_from_asset(self, asset_id):
        """
        Get a student by asset ID
        
        Args:
            asset_id (str): Asset ID from RT
            
        Returns:
            dict: Student data or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*
                FROM students s
                JOIN device_info d ON s.id = d.student_id
                WHERE d.asset_id = ?
            """, (asset_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            student = dict(row)
            student['device_checked_in'] = bool(student['device_checked_in'])
            
            # Get device info
            cursor.execute("""
                SELECT * FROM device_info 
                WHERE student_id = ?
            """, (student['id'],))
            
            device_row = cursor.fetchone()
            if device_row:
                device_info = dict(device_row)
                student['device_info'] = {
                    'asset_id': device_info['asset_id'],
                    'asset_tag': device_info['asset_tag'],
                    'device_type': device_info['device_type'],
                    'serial_number': device_info['serial_number'],
                    'check_in_timestamp': device_info['check_in_timestamp']
                }
            
            return student
            
        except Exception as e:
            logger.error(f"Error getting student from asset {asset_id}: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def clear_all_students(self):
        """
        Clear all students from the tracking system
        
        Returns:
            dict: Result with count of removed students
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get the current count of students
            cursor.execute("SELECT COUNT(*) FROM students")
            student_count = cursor.fetchone()[0]
            
            # Delete all device_info records
            cursor.execute("DELETE FROM device_info")
            
            # Delete all student records
            cursor.execute("DELETE FROM students")
            
            conn.commit()
            
            logger.info(f"Cleared {student_count} students from the tracker")
            return {
                "success": True,
                "count": student_count
            }
                
        except Exception as e:
            logger.error(f"Error clearing students: {e}")
            if 'conn' in locals():
                conn.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_statistics(self):
        """
        Get statistics on students and device check-ins
        
        Returns:
            dict: Statistics
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get total student count
            cursor.execute("SELECT COUNT(*) FROM students")
            total_students = cursor.fetchone()[0]
            
            # Get checked in count
            cursor.execute("SELECT COUNT(*) FROM students WHERE device_checked_in = 1")
            checked_in = cursor.fetchone()[0]
            
            # Calculate completion rate
            completion_rate = 0
            if total_students > 0:
                completion_rate = (checked_in / total_students) * 100
            
            return {
                "total_students": total_students,
                "checked_in": checked_in,
                "not_checked_in": total_students - checked_in,
                "completion_rate": completion_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_students": 0,
                "checked_in": 0,
                "not_checked_in": 0,
                "completion_rate": 0
            }
        finally:
            if 'conn' in locals():
                conn.close()