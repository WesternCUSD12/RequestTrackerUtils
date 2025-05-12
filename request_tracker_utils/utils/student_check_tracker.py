import csv
import os
import time
import fcntl
import datetime
import logging
from pathlib import Path
from flask import current_app
import json

logger = logging.getLogger(__name__)

class StudentDeviceTracker:
    """Utility for tracking student device check-ins across the school year"""
    
    def __init__(self, data_dir=None):
        """
        Initialize the student device tracker
        
        Args:
            data_dir (str, optional): Directory to store tracker data files. If None, uses WORKING_DIR from config.
        """
        if data_dir is None:
            self.data_dir = Path(current_app.config.get('WORKING_DIR', '/var/lib/request-tracker-utils'))
        else:
            self.data_dir = Path(data_dir)
            
        # Ensure the student_data directory exists
        self.student_data_path = self.data_dir / 'student_data'
        
        # Try to create the directory
        try:
            self.student_data_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using student data directory at: {self.student_data_path}")
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Failed to create student data directory at {self.student_data_path}: {e}")
            
            # Fall back to using the instance folder as in the device_routes.py implementation
            try:
                # Import is already at the top level, no need to import here again
                instance_data_dir = Path(current_app.instance_path) / 'student_data'
                instance_data_dir.mkdir(parents=True, exist_ok=True)
                self.student_data_path = instance_data_dir
                logger.info(f"Using alternative student data directory: {self.student_data_path}")
            except Exception as nested_e:
                logger.error(f"Failed to create student data directory: {nested_e}")
                raise
        
        # Define the path for the current school year's tracking file
        self._set_current_year_file()
    
    def _set_current_year_file(self):
        """Set the current school year's tracking file"""
        today = datetime.datetime.now()
        
        # Calculate academic year (if before July, it's previous year-current year; if July or after, it's current year-next year)
        if today.month < 7:
            # Spring semester - academic year started last year
            start_year = today.year - 1
            end_year = today.year
        else:
            # Fall semester - academic year starts this year
            start_year = today.year
            end_year = today.year + 1
        
        self.current_school_year = f"{start_year}-{end_year}"
        self.current_tracker_file = self.student_data_path / f"student_devices_{self.current_school_year}.json"
        
        # Check if we need to create a new file
        if not self.current_tracker_file.exists():
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
        """Load the current tracker data from file"""
        try:
            with open(self.current_tracker_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tracker data: {e}")
            return None
    
    def _save_tracker_data(self, data):
        """Save tracker data to file with locking for concurrency"""
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
    
    def get_all_students(self):
        """
        Get all students in the tracking system
        
        Returns:
            list: List of student data dictionaries
        """
        data = self._load_tracker_data()
        if not data:
            return []
        
        # Convert dictionary to list of student objects with their IDs included
        students = []
        for student_id, student_data in data["students"].items():
            student_info = student_data.copy()
            student_info["id"] = student_id
            students.append(student_info)
        
        # Sort by last name, then first name
        return sorted(students, key=lambda s: (s.get("last_name", ""), s.get("first_name", "")))
    
    def get_student(self, student_id):
        """
        Get a specific student's data
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            dict: Student data or None if not found
        """
        data = self._load_tracker_data()
        if not data or student_id not in data["students"]:
            return None
        
        student_data = data["students"][student_id].copy()
        student_data["id"] = student_id
        return student_data
    
    def add_update_student(self, student_id, student_data):
        """
        Add or update a student in the tracking system
        
        Args:
            student_id (str): Student ID or username
            student_data (dict): Student data including first_name, last_name, etc.
            
        Returns:
            bool: Success status
        """
        data = self._load_tracker_data()
        if not data:
            return False
        
        # Create or update student
        if student_id not in data["students"]:
            data["students"][student_id] = {}
        
        # Update student data
        for key, value in student_data.items():
            if key != "id":  # Skip the ID field as we're using it as the key
                data["students"][student_id][key] = value
        
        # Add tracking data if not present
        if "device_checked_in" not in data["students"][student_id]:
            data["students"][student_id]["device_checked_in"] = False
        
        if "check_in_date" not in data["students"][student_id]:
            data["students"][student_id]["check_in_date"] = None
        
        # Save the updated data
        return self._save_tracker_data(data)
    
    def remove_student(self, student_id):
        """
        Remove a student from the tracking system
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            bool: Success status
        """
        data = self._load_tracker_data()
        if not data or student_id not in data["students"]:
            return False
        
        # Remove student
        del data["students"][student_id]
        
        # Save the updated data
        return self._save_tracker_data(data)
    
    def mark_device_checked_in(self, student_id, asset_data=None):
        """
        Mark a student's device as checked in
        
        Args:
            student_id (str): Student ID or username
            asset_data (dict, optional): Asset data from the check-in
            
        Returns:
            bool: Success status
        """
        data = self._load_tracker_data()
        if not data:
            return False
        
        # Create student if they don't exist
        if student_id not in data["students"]:
            data["students"][student_id] = {
                "device_checked_in": False,
                "check_in_date": None,
            }
        
        # Mark device as checked in
        data["students"][student_id]["device_checked_in"] = True
        data["students"][student_id]["check_in_date"] = datetime.datetime.now().isoformat()
        
        # Store asset data if provided
        if asset_data:
            # Extract basic asset details
            device_info = {
                "asset_id": asset_data.get("id", ""),
                "asset_tag": asset_data.get("Name", ""),
                "check_in_timestamp": datetime.datetime.now().isoformat()
            }
            
            # Extract device type and serial from CustomFields
            if 'CustomFields' in asset_data:
                for field in asset_data['CustomFields']:
                    if field.get('name') == 'Type' and field.get('values'):
                        device_info["device_type"] = field['values'][0]
                    elif field.get('name') == 'Serial Number' and field.get('values'):
                        device_info["serial_number"] = field['values'][0]
            
            data["students"][student_id]["device_info"] = device_info
        
        # Save the updated data
        return self._save_tracker_data(data)
    
    def mark_device_not_checked_in(self, student_id):
        """
        Mark a student's device as not checked in
        
        Args:
            student_id (str): Student ID or username
            
        Returns:
            bool: Success status
        """
        data = self._load_tracker_data()
        if not data or student_id not in data["students"]:
            return False
        
        # Mark device as not checked in
        data["students"][student_id]["device_checked_in"] = False
        data["students"][student_id]["check_in_date"] = None
        
        # Remove device info if present
        if "device_info" in data["students"][student_id]:
            del data["students"][student_id]["device_info"]
        
        # Save the updated data
        return self._save_tracker_data(data)
    
    def import_students_from_csv(self, csv_file):
        """
        Import students from a CSV file
        
        Args:
            csv_file (str): Path to CSV file
            
        Returns:
            dict: Import summary with counts
        """
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                
                # Track counts
                added = 0
                updated = 0
                failed = 0
                
                # Load current data
                data = self._load_tracker_data()
                if not data:
                    return {"error": "Could not load tracker data"}
                
                # Process each row
                for row in reader:
                    try:
                        # Determine student ID (try common fields)
                        student_id = None
                        for id_field in ['id', 'student_id', 'username']:
                            if id_field in row and row[id_field]:
                                student_id = row[id_field]
                                break
                        
                        # Skip if no ID found
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
                        if student_id in data["students"]:
                            # Update existing student
                            for key, value in student_data.items():
                                data["students"][student_id][key] = value
                            updated += 1
                        else:
                            # Add new student
                            data["students"][student_id] = student_data
                            # Initialize tracking fields
                            data["students"][student_id]["device_checked_in"] = False
                            data["students"][student_id]["check_in_date"] = None
                            added += 1
                            
                    except Exception as row_error:
                        logger.error(f"Error processing student row: {row_error}")
                        failed += 1
                
                # Save the updated data
                if self._save_tracker_data(data):
                    return {
                        "success": True,
                        "added": added,
                        "updated": updated,
                        "failed": failed
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to save data"
                    }
                    
        except Exception as e:
            logger.error(f"Error importing students from CSV: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def export_students_to_csv(self, include_device_info=True):
        """
        Export students to a CSV string
        
        Args:
            include_device_info (bool): Whether to include device information
            
        Returns:
            str: CSV content
        """
        try:
            students = self.get_all_students()
            if not students:
                return ""
            
            import io
            output = io.StringIO()
            
            # Determine fields to include
            if include_device_info:
                fieldnames = ["id", "first_name", "last_name", "grade", "device_checked_in", "check_in_date"]
                # Add device_info fields if any student has them
                for student in students:
                    if "device_info" in student:
                        for key in student["device_info"].keys():
                            if key not in fieldnames:
                                fieldnames.append(key)
            else:
                fieldnames = ["id", "first_name", "last_name", "grade", "device_checked_in", "check_in_date"]
            
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
        Find a student based on an asset ID
        
        Args:
            asset_id (str): Asset ID from RT
            
        Returns:
            dict: Student data or None if not found
        """
        data = self._load_tracker_data()
        if not data:
            return None
        
        # Search each student for the asset
        for student_id, student_data in data["students"].items():
            if "device_info" in student_data and student_data["device_info"].get("asset_id") == asset_id:
                result = student_data.copy()
                result["id"] = student_id
                return result
        
        return None
    
    def clear_all_students(self):
        """
        Clear all students from the tracking system
        
        Returns:
            dict: Result with count of removed students
        """
        try:
            data = self._load_tracker_data()
            if not data:
                return {
                    "success": False,
                    "error": "Could not load tracker data"
                }
            
            # Count students before clearing
            student_count = len(data["students"])
            
            # Clear students but keep other metadata
            data["students"] = {}
            data["last_updated"] = datetime.datetime.now().isoformat()
            
            # Save the updated data
            if self._save_tracker_data(data):
                logger.info(f"Cleared {student_count} students from the tracker")
                return {
                    "success": True,
                    "count": student_count
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to save cleared data"
                }
                
        except Exception as e:
            logger.error(f"Error clearing students: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_statistics(self):
        """
        Get statistics about the student device check-in status
        
        Returns:
            dict: Statistics
        """
        data = self._load_tracker_data()
        if not data:
            return {
                "total_students": 0,
                "checked_in": 0,
                "not_checked_in": 0,
                "completion_rate": 0
            }
        
        total_students = len(data["students"])
        checked_in = sum(1 for s in data["students"].values() if s.get("device_checked_in"))
        not_checked_in = total_students - checked_in
        
        completion_rate = 0
        if total_students > 0:
            completion_rate = (checked_in / total_students) * 100
        
        return {
            "school_year": self.current_school_year,
            "total_students": total_students,
            "checked_in": checked_in,
            "not_checked_in": not_checked_in,
            "completion_rate": completion_rate
        }