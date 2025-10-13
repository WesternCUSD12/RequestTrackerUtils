#!/usr/bin/env python3
"""
Script to sync student data into RT user custom fields.
Updates 'grade' and 'student id' fields for RT users based on the student database.
"""
import sys
import logging
import argparse
import os
import time
from pathlib import Path
import traceback
from dotenv import load_dotenv
import requests

# Add parent directory to Python path to import request_tracker_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
load_dotenv()

# Import RT API utilities (after sys.path changes)
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN  # noqa: E402
from request_tracker_utils.utils.rt_api import fetch_user_data, update_user_custom_field  # noqa: E402

# Create a Flask app context for testing
from flask import Flask  # noqa: E402
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
from request_tracker_utils.utils.student_check_tracker import StudentDeviceTracker  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_rt_user_custom_field(user_id, field_name, field_value, config=None, max_retries=3, retry_delay=2):
    """
    Update a custom field value for a user in RT.
    
    This is a wrapper around the update_user_custom_field function with additional logging.
    
    Args:
        user_id (str): The numeric ID or username of the user to update
        field_name (str): The name of the custom field to update
        field_value (str): The new value for the custom field
        config (dict, optional): Configuration dictionary
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        dict: The response from the API
        
    Raises:
        Exception: If there's an error updating the user custom field after all retries
    """
    for attempt in range(max_retries):
        try:
            # Add a small delay to prevent overwhelming the server
            if attempt > 0:
                logger.info(f"Retry attempt {attempt+1} for updating {user_id} field '{field_name}'")
                time.sleep(retry_delay * attempt)  # Exponential backoff
            
            return update_user_custom_field(user_id, field_name, field_value, config)
        except requests.exceptions.HTTPError as e:
            # Handle 404 errors - user doesn't exist
            if e.response is not None and e.response.status_code == 404:
                logger.warning(f"User {user_id} not found in RT (404 error)")
                raise Exception(f"User {user_id} not found in RT")
            
            # For 500 errors, retry if attempts remain
            if e.response is not None and e.response.status_code >= 500 and attempt < max_retries - 1:
                logger.warning(f"Server error (500) when updating {user_id}, will retry...")
                continue
            logger.error(f"Error updating user {user_id} custom field '{field_name}': {e}")
            raise
        except Exception as e:
            # For general connection errors, retry if attempts remain
            if attempt < max_retries - 1:
                logger.warning(f"Connection error when updating {user_id}, will retry...")
                continue
            logger.error(f"Error updating user {user_id} custom field '{field_name}': {e}")
            raise Exception(f"Failed to update user custom field in RT: {e}")
    
    # If all retries failed
    raise Exception(f"Failed to update user custom field in RT after {max_retries} attempts")

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
        try:
            user_data = fetch_user_data(rt_user_id, config)
        except requests.exceptions.HTTPError as e:
            # Handle 404 errors - user doesn't exist
            if e.response is not None and e.response.status_code == 404:
                logger.warning(f"Sample user {rt_user_id} not found in RT (404 error)")
                # Try a different approach - just assume custom fields need to be created
                return False
            # Re-raise other errors
            raise
            
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
        has_grad_year = any('graduation' in name.lower() or 'grad' in name.lower() or 'year' in name.lower() 
                          for name in cf_names)
        has_student_id = any('student' in name.lower() and 'id' in name.lower() for name in cf_names)
        
        if not has_grad_year:
            logger.warning("Graduation Year custom field not found for users")
        if not has_student_id:
            logger.warning("Student ID custom field not found for users")
            
        return has_grad_year and has_student_id
        
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
                if 'graduation' in name or 'grad' in name or ('year' in name and 'id' not in name):
                    grade_field = cf['name']
                elif 'student' in name and 'id' in name:
                    student_id_field = cf['name']
        
        return (grade_field, student_id_field)
        
    except Exception as e:
        logger.error(f"Error getting exact field names: {e}")
        return (None, None)

def calculate_graduation_year(grade, current_year=None):
    """
    Calculate graduation year based on grade level.
    
    Args:
        grade (str or int): The grade level (K-12)
        current_year (int, optional): Current year to base calculation on. Defaults to current year.
        
    Returns:
        str: The graduation year, or original grade if conversion failed
    """
    # Default to current year if not specified
    if current_year is None:
        from datetime import datetime
        now = datetime.now()
        # If it's after June, consider it the next academic year
        if now.month >= 6:
            current_year = now.year + 1
        else:
            current_year = now.year
    
    try:
        # Handle various grade formats
        if grade in ('K', 'k', 'K-1', 'k-1', 'kinder', 'kindergarten'):
            grade_num = 0
        else:
            grade_num = int(str(grade).strip())
        
        # Calculate graduation year: 12th grade graduates this year, 11th next year, etc.
        years_to_graduation = 12 - grade_num
        graduation_year = current_year + years_to_graduation
        
        logger.debug(f"Converted grade {grade} to graduation year {graduation_year}")
        return str(graduation_year)
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not convert grade '{grade}' to graduation year: {e}")
        # Return the original grade if conversion fails
        return str(grade)

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
            logger.warning("Required custom fields not found in RT. Using default field names: 'Graduation Year' and 'Student ID'")
            # Use default field names - changed Grade to Graduation Year
            grade_field, student_id_field = "Graduation Year", "Student ID"
        else:
            # Get exact field names (case-sensitive)
            grade_field, student_id_field = get_exact_field_names(sample_student['rt_user_id'], config)
            if not grade_field or not student_id_field:
                logger.warning("Could not determine exact field names. Using defaults: Graduation Year='Graduation Year', Student ID='Student ID'")
                grade_field = grade_field or "Graduation Year"
                student_id_field = student_id_field or "Student ID"
            
        logger.info(f"Using custom field names: Graduation Year='{grade_field}', Student ID='{student_id_field}'")
        
        # Rate limiting parameters
        rate_limit_delay = 0.5  # seconds between API calls
        consecutive_errors = 0
        error_backoff_factor = 2  # Multiply delay by this factor after consecutive errors
        
        # Process each student
        for student in students:
            try:
                rt_user_id = student.get('rt_user_id')
                if not rt_user_id:
                    results['skipped_no_rt'] += 1
                    continue
                    
                student_id = student.get('id')
                grade = student.get('grade')
                
                # Convert grade to graduation year using current year from config if specified
                current_year = config.get('CURRENT_YEAR')  # May be None, that's okay
                graduation_year = calculate_graduation_year(grade, current_year) if grade else None
                
                logger.info(f"Processing student: {student.get('first_name')} {student.get('last_name')} (RT: {rt_user_id})")
                logger.info(f"  Grade: {grade} → Graduation Year: {graduation_year}")
                
                # Skip update if dry run
                if dry_run:
                    logger.info(f"DRY RUN - Would update RT user {rt_user_id}: {grade_field}='{graduation_year}', {student_id_field}='{student_id}'")
                    results['updated_users'] += 1
                    continue
                
                # Apply basic rate limiting
                time.sleep(rate_limit_delay * (consecutive_errors + 1))
                    
                # Update graduation year (previously grade)
                updated = False
                if graduation_year:
                    try:
                        update_rt_user_custom_field(rt_user_id, grade_field, graduation_year, config)
                        logger.info(f"Updated {grade_field} to '{graduation_year}' for user {rt_user_id}")
                        updated = True
                    except Exception as grade_err:
                        if "not found" in str(grade_err).lower():
                            logger.warning(f"User {rt_user_id} not found in RT - skipping")
                            consecutive_errors += 1
                            raise
                        else:
                            logger.error(f"Error updating {grade_field} for user {rt_user_id}: {grade_err}")
                            consecutive_errors += 1
                            raise
                
                # Apply rate limiting between operations
                if updated:
                    time.sleep(rate_limit_delay)
                
                # Update student ID
                if student_id:
                    try:
                        update_rt_user_custom_field(rt_user_id, student_id_field, student_id, config)
                        logger.info(f"Updated {student_id_field} to '{student_id}' for user {rt_user_id}")
                        updated = True
                    except Exception as id_err:
                        if "not found" in str(id_err).lower():
                            # Already logged by the previous error
                            raise
                        else:
                            logger.error(f"Error updating {student_id_field} for user {rt_user_id}: {id_err}")
                            consecutive_errors += 1
                            raise
                
                # Reset consecutive errors counter after successful update
                if updated:
                    consecutive_errors = 0
                    results['updated_users'] += 1
                    
            except Exception as e:
                logger.error(f"Error updating RT user {student.get('rt_user_id')}: {e}")
                results['errors'] += 1
                
                # Increase delay after consecutive errors to give server a break
                if consecutive_errors > 3:
                    backoff_delay = rate_limit_delay * error_backoff_factor * consecutive_errors
                    logger.warning(f"Multiple consecutive errors, backing off for {backoff_delay:.1f} seconds")
                    time.sleep(backoff_delay)
        
        return results
        
    except Exception as e:
        logger.error(f"Error syncing student data to RT: {e}")
        logger.error(traceback.format_exc())
        results['errors'] += 1
        return results

def main():
    parser = argparse.ArgumentParser(description="Sync student data to RT user custom fields")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually update RT, just show what would be done")
    parser.add_argument('--batch-size', type=int, default=0, help="Process students in batches with specified size (0 for all at once)")
    parser.add_argument('--batch-delay', type=float, default=5.0, help="Delay in seconds between batches")
    parser.add_argument('--rate-limit', type=float, default=0.5, help="Delay in seconds between API calls")
    parser.add_argument('--current-year', type=int, help="Specify the current year for graduation calculation (default: auto-detect)")
    args = parser.parse_args()
    
    logger.info("Starting RT user custom fields sync")
    
    config = {
        'RT_URL': RT_URL,
        'API_ENDPOINT': API_ENDPOINT,
        'RT_TOKEN': RT_TOKEN,
        'RATE_LIMIT_DELAY': args.rate_limit,
        'CURRENT_YEAR': args.current_year
    }
    
    if args.dry_run:
        logger.info("Running in DRY RUN mode - no changes will be made")
        
    # Log current year being used for graduation calculation
    from datetime import datetime
    current_year = args.current_year
    if current_year:
        logger.info(f"Using specified year {current_year} for graduation calculation")
    else:
        now = datetime.now()
        if now.month >= 6:
            current_year = now.year + 1
        else:
            current_year = now.year
        logger.info(f"Auto-detected current year {current_year} for graduation calculation")
    
    # If using batch processing
    if args.batch_size > 0:
        logger.info(f"Processing in batches of {args.batch_size} students with {args.batch_delay} seconds delay between batches")
        
        # Get all students first
        try:
            instance_path = app.config.get('INSTANCE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance'))
            data_dir = os.path.join(instance_path, 'student_data')
            tracker = StudentDeviceTracker(data_dir=data_dir)
            all_students = tracker.get_all_students()
            
            # Process in batches
            total_students = len(all_students)
            _total_updated = 0
            _total_skipped = 0
            _total_errors = 0
            
            for i in range(0, total_students, args.batch_size):
                _batch = all_students[i:i+args.batch_size]
                logger.info(f"Processing batch {i//args.batch_size + 1} of {(total_students + args.batch_size - 1)//args.batch_size}: students {i+1}-{min(i+args.batch_size, total_students)}")
                
                # TODO: Implement batch processing logic
                # For now, continue with normal processing
                
                if i + args.batch_size < total_students and not args.dry_run:
                    logger.info(f"Batch complete, pausing for {args.batch_delay} seconds before next batch")
                    time.sleep(args.batch_delay)
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            logger.error(traceback.format_exc())
            
    # Standard processing (no batching or batching not yet implemented)
    results = sync_student_data_to_rt(config, args.dry_run)
    
    logger.info("RT user custom fields sync complete")
    logger.info(f"Total students: {results['total_students']}")
    logger.info(f"RT users updated: {results['updated_users']}")
    logger.info(f"Skipped (no RT user ID): {results['skipped_no_rt']}")
    logger.info(f"Errors: {results['errors']}")
    
if __name__ == "__main__":
    main()
