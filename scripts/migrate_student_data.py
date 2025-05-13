#!/usr/bin/env python3
"""
Migration script to import student data from JSON files into the SQLite database.
This script imports data from JSON files in both the standard and instance paths.
"""

import os
import sys
import json
import glob
import logging
from pathlib import Path

# Add parent directory to path so we can import request_tracker_utils modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from request_tracker_utils.utils.db import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_student_json_file(file_path):
    """Import a single JSON file into the database"""
    logger.info(f"Importing student data from {file_path}")
    
    try:
        # Load the JSON data
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'students' not in data:
            logger.warning(f"No students field found in {file_path}")
            return 0
            
        students = data['students']
        school_year = data.get('school_year', 'Unknown')
        logger.info(f"Found {len(students)} students for school year {school_year}")
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            added = 0
            updated = 0
            
            for student_id, student_data in students.items():
                # Check if student exists
                cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
                exists = cursor.fetchone() is not None
                
                # Prepare data for insertion/update
                device_checked_in = 1 if student_data.get('device_checked_in', False) else 0
                check_in_date = student_data.get('check_in_date')
                
                if exists:
                    # Update existing student
                    cursor.execute("""
                        UPDATE students SET
                            first_name = ?,
                            last_name = ?,
                            grade = ?,
                            rt_user_id = ?,
                            device_checked_in = ?,
                            check_in_date = ?
                        WHERE id = ?
                    """, (
                        student_data.get('first_name'),
                        student_data.get('last_name'),
                        student_data.get('grade'),
                        student_data.get('rt_user_id'),
                        device_checked_in,
                        check_in_date,
                        student_id
                    ))
                    updated += 1
                else:
                    # Insert new student
                    cursor.execute("""
                        INSERT INTO students (
                            id, first_name, last_name, grade, rt_user_id,
                            device_checked_in, check_in_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        student_id,
                        student_data.get('first_name'),
                        student_data.get('last_name'),
                        student_data.get('grade'),
                        student_data.get('rt_user_id'),
                        device_checked_in,
                        check_in_date
                    ))
                    added += 1
                    
                # Process device_info if present
                device_info = student_data.get('device_info')
                if device_info and device_checked_in:
                    # Delete any existing device info
                    cursor.execute("DELETE FROM device_info WHERE student_id = ?", (student_id,))
                    
                    # Insert device info
                    cursor.execute("""
                        INSERT INTO device_info (
                            student_id, asset_id, asset_tag, device_type,
                            serial_number, check_in_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        student_id,
                        device_info.get('asset_id', ''),
                        device_info.get('asset_tag', ''),
                        device_info.get('device_type', ''),
                        device_info.get('serial_number', ''),
                        device_info.get('check_in_timestamp', check_in_date)
                    ))
            
            conn.commit()
            logger.info(f"Successfully imported {added} new students and updated {updated} existing students from {file_path}")
            return added + updated
            
        except Exception as e:
            logger.error(f"Error importing student data: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Error opening or parsing JSON file {file_path}: {e}")
        return 0

def find_json_files(directories):
    """Find all student JSON files in the specified directories"""
    json_files = []
    
    for directory in directories:
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.warning(f"Directory does not exist: {directory_path}")
            continue
            
        # Look for student data files
        patterns = [
            str(directory_path / "*student*devices*.json"),
            str(directory_path / "student_data" / "*student*devices*.json")
        ]
        
        for pattern in patterns:
            found_files = glob.glob(pattern)
            if found_files:
                json_files.extend(found_files)
                logger.info(f"Found {len(found_files)} JSON files matching {pattern}")
    
    return json_files

def main():
    """Main function to find and import student JSON files"""
    # Set up search directories
    script_dir = Path(__file__).parent.parent
    instance_dir = script_dir / 'instance'
    home_dir = Path.home() / 'western_admin' / 'RT'
    
    # Define all places to look for student data JSON files
    search_dirs = [
        script_dir,
        instance_dir,
        instance_dir / 'student_data',
        '/var/lib/request-tracker-utils',
        '/var/lib/request-tracker-utils/student_data',
        home_dir,
        home_dir / 'student_data'
    ]
    
    # Find all JSON files
    json_files = find_json_files(search_dirs)
    
    if not json_files:
        logger.warning("No student data JSON files found in search directories.")
        return
        
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    # Import each file
    total_imported = 0
    for file_path in json_files:
        imported = import_student_json_file(file_path)
        total_imported += imported
        
    logger.info(f"Migration complete. Processed {total_imported} student records from {len(json_files)} files.")

if __name__ == "__main__":
    main()