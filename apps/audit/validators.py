"""CSV validation utilities for audit session uploads.

This module provides functions to parse, validate, and process CSV files
containing student audit data (name, grade, advisor).
"""

import csv
import io
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


def detect_encoding(file_bytes: bytes) -> str:
    """Detect CSV file encoding.
    
    Args:
        file_bytes: Raw bytes from uploaded CSV file
        
    Returns:
        Detected encoding name (utf-8, utf-16, or latin-1)
        
    Note:
        Tries common encodings in order: UTF-8, UTF-16, Latin-1.
        Falls back to UTF-8 if all fail.
    """
    encodings = ['utf-8', 'utf-16', 'latin-1']
    
    for encoding in encodings:
        try:
            file_bytes.decode(encoding)
            logger.debug(f"Detected encoding: {encoding}")
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    logger.warning("Could not detect encoding, defaulting to utf-8")
    return 'utf-8'


def validate_required_columns(headers: List[str]) -> Tuple[bool, Optional[str]]:
    """Validate that CSV has required columns.
    
    Args:
        headers: List of column names from CSV header row
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Required columns: name, grade, advisor (case-insensitive)
    """
    required = {'name', 'grade', 'advisor'}
    # Normalize headers: strip whitespace and convert to lowercase
    headers_lower = {h.strip().lower() for h in headers if h}
    
    missing = required - headers_lower
    
    if missing:
        error_msg = f"Missing required columns: {', '.join(sorted(missing))}. Found columns: {', '.join(sorted(headers_lower))}"
        logger.error(f"CSV validation failed: {error_msg}")
        return False, error_msg
    
    return True, None


def detect_duplicates(students: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Detect duplicate student entries using composite key.
    
    Args:
        students: List of student dicts with name, grade, advisor
        
    Returns:
        List of duplicate student records (empty if no duplicates)
        
    Students are considered duplicates if they have identical
    (name + grade + advisor) composite keys.
    """
    seen = set()
    duplicates = []
    
    for student in students:
        # Create composite key (case-insensitive, stripped)
        key = (
            student.get('name', '').strip().lower(),
            student.get('grade', '').strip().lower(),
            student.get('advisor', '').strip().lower()
        )
        
        if key in seen:
            duplicates.append(student)
            logger.warning(f"Duplicate student detected: {student}")
        else:
            seen.add(key)
    
    return duplicates


def parse_audit_csv(file_path: str, max_rows: int = 1000) -> Tuple[List[Dict[str, str]], List[str]]:
    """Parse CSV file and return student list or validation errors.
    
    Args:
        file_path: Path to uploaded CSV file
        max_rows: Maximum number of student rows allowed (default 1000)
        
    Returns:
        Tuple of (students_list, errors_list)
        If errors exist, students_list will be empty.
        
    Raises:
        IOError: If file cannot be read
    """
    errors = []
    students = []
    
    try:
        # Read file and detect encoding
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        encoding = detect_encoding(file_bytes)
        
        # Parse CSV
        text_content = file_bytes.decode(encoding, errors='replace')
        csv_reader = csv.DictReader(io.StringIO(text_content))
        
        # Validate headers
        if not csv_reader.fieldnames:
            errors.append("CSV file is empty or has no header row")
            return students, errors
        
        is_valid, error_msg = validate_required_columns(csv_reader.fieldnames)
        if not is_valid:
            errors.append(error_msg)
            return students, errors
        
        # Read student rows
        for idx, row in enumerate(csv_reader, start=2):  # Start at 2 (after header)
            if idx > max_rows + 1:  # +1 for header row
                errors.append(f"CSV exceeds maximum of {max_rows} students")
                return [], errors
            
            # Normalize column names (case-insensitive)
            student = {
                'name': row.get('name') or row.get('Name') or row.get('NAME') or '',
                'grade': row.get('grade') or row.get('Grade') or row.get('GRADE') or '',
                'advisor': row.get('advisor') or row.get('Advisor') or row.get('ADVISOR') or '',
                'username': row.get('username') or row.get('Username') or row.get('USERNAME') or ''
            }
            
            # Strip whitespace
            student = {k: v.strip() if v else '' for k, v in student.items()}
            
            # Replace missing advisor with "Missing"
            if not student['advisor']:
                student['advisor'] = 'Missing'
            
            # username is optional - empty string is OK
            
            # Validate required fields (name and grade must be present)
            if not student['name']:
                errors.append(f"Row {idx}: Missing value for name")
                continue
            if not student['grade']:
                errors.append(f"Row {idx}: Missing value for grade")
                continue
            
            students.append(student)
        
        if not students and not errors:
            errors.append("CSV contains no valid student records")
        
        logger.info(f"Parsed {len(students)} students from CSV")
        return students, errors
        
    except Exception as e:
        logger.exception(f"Error parsing CSV file: {e}")
        errors.append(f"Failed to parse CSV: {str(e)}")
        return [], errors
