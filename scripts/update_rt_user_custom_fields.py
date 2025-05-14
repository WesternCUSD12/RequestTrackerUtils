#!/usr/bin/env python3
"""
Script to sync student data into RT user custom fields.
Updates 'grade' and 'student id' fields for RT users based on the student database.
"""
import sys
import logging
import argparse
import os
import sqlite3
from pathlib import Path
import traceback
from dotenv import load_dotenv

# Add parent directory to Python path to import request_tracker_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
load_dotenv()

# Import RT API utilities
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import rt_api_request, fetch_user_data, update_user_custom_field

# Create a Flask app context for testing
from flask import Flask
app = Flask(__name__)
app.config.update({
    'RT_URL': RT_URL,
    'API_ENDPOINT': API_ENDPOINT,
    'RT_TOKEN': RT_TOKEN,
    'INSTANCE_PATH': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance')
})

# Set up the app context
ctx = app.app_context()
ctx.push()

# Now import components that need Flask context
from request_tracker_utils.utils.student_check_tracker import StudentDeviceTracker
from request_tracker_utils.utils.db import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_rt_user_custom_field(user_id, field_name, field_value, config=None):
    """
    Update a custom field value for a user in RT.
    
    This is a wrapper around the update_user_custom_field function with additional logging.
    
    Args:
        user_id (str): The numeric ID or username of the user to update
        field_name (str): The name of the custom field to update
        field_value (str): The new value for the custom field
        config (dict, optional): Configuration dictionary
        
    Returns:
        dict: The response from the API
        
    Raises:
        Exception: If there's an error updating the user custom field
    """
    try:
        return update_user_custom_field(user_id, field_name, field_value, config)
    except Exception as e:
        logger.error(f"Error updating user {user_id} custom field '{field_name}': {e}")
        raise Exception(f"Failed to update user custom field in RT: {e}")

def validate_user_custom_fields(rt_user_id, config=None):
    """
    Check if the required custom fields exist for RT users.
    
    Args:
        rt_user_id (str): A sample RT user ID to check
        config (dict, optional): Configuration dictionary
        
    Returns:
        bool: True if both "grade" and "student id" custom fields exist
    """
    try:
        # Fetch user data to check custom fields
        user_data = fetch_user_data(rt_user_id, config)
        
        # Check if CustomFields exists in the response
        if 'CustomFields' not in user_data:
            logger.warning(f"No CustomFields found in user data for {rt_user_id}")
            return False
            
        # Get the custom field names
        cf_names = []
        for cf in user_data.get('CustomFields', []):
            if isinstance(cf, dict) and 'name' in cf:
                cf_names.append(cf['name'].lower())
        
        # Check for required fields
        has_grade = any('grade' in name.lower() for name in cf_names)
        has_student_id = any('student' in name.lower() and 'id' in name.lower() for name in cf_names)
        
        if not has_grade:
            logger.warning("Grade custom field not found for users")
        if not has_student_id:
            logger.warning("Student ID custom field not found for users")
            
        return has_grade and has_student_id
        
    except Exception as e:
        logger.error(f"Error checking user custom fields: {e}")
        return False

def get_exact_field_names(rt_user_id, config=None):
    """
    Get the exact names of the grade and student id custom fields.
    
    Args:
        rt_user_id (str): A sample RT user ID to check
        config (dict, optional): Configuration dictionary
        
    Returns:
        tuple: (grade_field_name, student_id_field_name)
    """
    try:
        # Fetch user data to check custom fields
        user_data = fetch_user_data(rt_user_id, config)
        
        grade_field = None
        student_id_field = None
        
        # Check custom fields
        for cf in user_data.get('CustomFields', []):
            if isinstance(cf, dict) and 'name' in cf:
                name = cf['name'].lower()
                if 'grade' in name:
                    grade_field = cf['name']
                elif 'student' in name and 'id' in name:
                    student_id_field = cf['name']
        
        return (grade_field, student_id_field)
        
    except Exception as e:
        logger.error(f"Error getting exact field names: {e}")
        return (None, None)

def sync_student_data_to_rt(config=None, dry_run=False):
    """
    Sync student data from the database to RT user custom fields.
    
    Args:
        config (dict, optional): Configuration dictionary
        dry_run (bool): If True, don't actually update RT
        
    Returns:
        dict: Summary of update results
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
    
    # Initialize results
    results = {
        'total_students': 0,
        'updated_users': 0,
        'skipped_no_rt': 0,
        'errors': 0
    }
    
    try:
        # Get instance path for database location
        instance_path = app.config.get('INSTANCE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance'))
        data_dir = os.path.join(instance_path, 'student_data')
        
        # Get students from the database
        tracker = StudentDeviceTracker(data_dir=data_dir)
        students = tracker.get_all_students()
        results['total_students'] = len(students)
        
        logger.info(f"Found {len(students)} students in the database")
        
        # Sample the first student with RT user ID to validate and get field names
        sample_student = None
        for student in students:
            if student.get('rt_user_id'):
                sample_student = student
                break
                
        if not sample_student:
            logger.error("No student with RT user ID found for validation")
            return results
            
        # Validate custom fields
        fields_exist = validate_user_custom_fields(sample_student['rt_user_id'], config)
        if not fields_exist:
            logger.warning("Required custom fields not found in RT. Using default field names: 'Grade' and 'Student ID'")
            # Use default field names
            grade_field, student_id_field = "Grade", "Student ID"
        else:
            # Get exact field names (case-sensitive)
            grade_field, student_id_field = get_exact_field_names(sample_student['rt_user_id'], config)
            if not grade_field or not student_id_field:
                logger.warning(f"Could not determine exact field names. Using defaults: Grade='Grade', Student ID='Student ID'")
                grade_field = grade_field or "Grade"
                student_id_field = student_id_field or "Student ID"
            
        logger.info(f"Using custom field names: Grade='{grade_field}', Student ID='{student_id_field}'")
        
        # Process each student
        for student in students:
            try:
                rt_user_id = student.get('rt_user_id')
                if not rt_user_id:
                    results['skipped_no_rt'] += 1
                    continue
                    
                student_id = student.get('id')
                grade = student.get('grade')
                
                logger.info(f"Processing student: {student.get('first_name')} {student.get('last_name')} (RT: {rt_user_id})")
                
                # Skip update if dry run
                if dry_run:
                    logger.info(f"DRY RUN - Would update RT user {rt_user_id}: {grade_field}='{grade}', {student_id_field}='{student_id}'")
                    results['updated_users'] += 1
                    continue
                    
                # Update grade
                if grade:
                    update_rt_user_custom_field(rt_user_id, grade_field, grade, config)
                    logger.info(f"Updated {grade_field} to '{grade}' for user {rt_user_id}")
                
                # Update student ID
                if student_id:
                    update_rt_user_custom_field(rt_user_id, student_id_field, student_id, config)
                    logger.info(f"Updated {student_id_field} to '{student_id}' for user {rt_user_id}")
                
                results['updated_users'] += 1
                    
            except Exception as e:
                logger.error(f"Error updating RT user {student.get('rt_user_id')}: {e}")
                results['errors'] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Error syncing student data to RT: {e}")
        logger.error(traceback.format_exc())
        results['errors'] += 1
        return results

def main():
    parser = argparse.ArgumentParser(description="Sync student data to RT user custom fields")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually update RT, just show what would be done")
    args = parser.parse_args()
    
    logger.info("Starting RT user custom fields sync")
    
    config = {
        'RT_URL': RT_URL,
        'API_ENDPOINT': API_ENDPOINT,
        'RT_TOKEN': RT_TOKEN
    }
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
        
    results = sync_student_data_to_rt(config, args.dry_run)
    
    logger.info("RT user custom fields sync complete")
    logger.info(f"Total students: {results['total_students']}")
    logger.info(f"RT users updated: {results['updated_users']}")
    logger.info(f"Skipped (no RT user ID): {results['skipped_no_rt']}")
    logger.info(f"Errors: {results['errors']}")
    
if __name__ == "__main__":
    main()
