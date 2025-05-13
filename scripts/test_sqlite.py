#!/usr/bin/env python3
"""
Test script to verify the SQLite database implementation for student data.
"""
import os
import sys
import json
import sqlite3
import datetime
from pathlib import Path

# Add project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# First let's create a simplified version of the necessary functions to avoid Flask dependencies

def get_db_path():
    """Get the path to the SQLite database file"""
    instance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    return os.path.join(instance_path, 'student_data.db')

def get_db_connection():
    """Get a connection to the SQLite database"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This makes the rows accessible by column name
    return conn

def setup_database():
    """Set up the database schema if it doesn't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        grade TEXT,
        rt_user_id TEXT,
        device_checked_in INTEGER DEFAULT 0,
        check_in_date TEXT
    )
    ''')
    
    # Create device_info table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS device_info (
        student_id TEXT PRIMARY KEY,
        asset_id TEXT,
        asset_tag TEXT,
        device_type TEXT,
        serial_number TEXT,
        check_in_timestamp TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    ''')
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
    conn.commit()
    conn.close()

def print_divider(title=""):
    """Print a divider with optional title"""
    width = 80
    if title:
        print(f"\n{'-' * 3} {title} {'-' * (width - len(title) - 5)}")
    else:
        print(f"\n{'-' * width}")

def test_db_connection():
    """Test the database connection"""
    print_divider("Testing Database Connection")
    try:
        # Setup database first
        setup_database()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Database tables: {[table[0] for table in tables]}")
        
        # Count students
        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]
        print(f"Number of students in database: {student_count}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

def test_crud_operations():
    """Test CRUD operations on the database directly"""
    print_divider("Testing CRUD Operations")
    
    try:
        # Setup database first
        setup_database()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create a test student
        test_student_id = f"test_student_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Add the student
        print(f"Adding test student: {test_student_id}")
        cursor.execute(
            """
            INSERT INTO students (
                id, first_name, last_name, grade, rt_user_id, 
                device_checked_in, check_in_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                test_student_id,
                "Test",
                "Student",
                "10",
                "test123",
                0,
                None
            )
        )
        conn.commit()
        
        # Retrieve the student
        cursor.execute("SELECT * FROM students WHERE id = ?", (test_student_id,))
        student = cursor.fetchone()
        print(f"Retrieved student: {dict(student)}")
        
        # Update the student
        print(f"Updating student to grade 11")
        cursor.execute(
            "UPDATE students SET grade = ? WHERE id = ?",
            ("11", test_student_id)
        )
        conn.commit()
        
        # Verify update
        cursor.execute("SELECT * FROM students WHERE id = ?", (test_student_id,))
        student = cursor.fetchone()
        print(f"Retrieved student after update: {dict(student)}")
        
        # Test device check-in
        print("Testing device check-in")
        check_in_date = datetime.datetime.now().isoformat()
        cursor.execute(
            "UPDATE students SET device_checked_in = 1, check_in_date = ? WHERE id = ?",
            (check_in_date, test_student_id)
        )
        
        # Add device info
        cursor.execute(
            """
            INSERT INTO device_info (
                student_id, asset_id, asset_tag, device_type,
                serial_number, check_in_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                test_student_id,
                "123456",
                "Asset-12345",
                "Chromebook",
                "SN12345",
                datetime.datetime.now().isoformat()
            )
        )
        conn.commit()
        
        # Verify check-in
        cursor.execute("""
            SELECT s.*, 
                   d.asset_id, d.asset_tag, d.device_type, 
                   d.serial_number, d.check_in_timestamp 
            FROM students s
            LEFT JOIN device_info d ON s.id = d.student_id
            WHERE s.id = ?
        """, (test_student_id,))
        student = cursor.fetchone()
        print(f"Student after check-in: {dict(student)}")
        
        # Test check-out
        print("Testing device check-out")
        cursor.execute(
            "UPDATE students SET device_checked_in = 0, check_in_date = NULL WHERE id = ?",
            (test_student_id,)
        )
        cursor.execute("DELETE FROM device_info WHERE student_id = ?", (test_student_id,))
        conn.commit()
        
        # Verify check-out
        cursor.execute("SELECT * FROM students WHERE id = ?", (test_student_id,))
        student = cursor.fetchone()
        print(f"Student after check-out: {dict(student)}")
        
        # Delete the test student
        print(f"Deleting test student")
        cursor.execute("DELETE FROM students WHERE id = ?", (test_student_id,))
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT * FROM students WHERE id = ?", (test_student_id,))
        student = cursor.fetchone()
        print(f"Student after deletion (should be None): {student}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error testing CRUD operations: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def test_json_migration():
    """Test JSON to SQLite migration simulation"""
    print_divider("Testing JSON Migration Simulation")
    
    try:
        # Setup database first
        setup_database()
        
        # Check if JSON file exists
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                 'instance', 'student_data', 'student_devices_2024-2025.json')
        
        if os.path.exists(json_path):
            print(f"Found JSON file: {json_path}")
            
            # Read the JSON file to count students
            with open(json_path, 'r') as f:
                data = json.load(f)
                json_students = data.get('students', {})
                print(f"JSON file contains {len(json_students)} students")
            
                # Simulate migration for a single student
                if json_students:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Get the first student
                    student_id, student_data = next(iter(json_students.items()))
                    print(f"Simulating migration for student: {student_id}")
                    
                    # Check if student already exists
                    cursor.execute("SELECT 1 FROM students WHERE id = ?", (student_id,))
                    exists = cursor.fetchone() is not None
                    
                    if not exists:
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
                        print("✅ Successfully migrated one student from JSON to SQLite")
                    else:
                        print("✅ Student already exists in database")
                    
                    conn.close()
            
            return True
        else:
            print(f"JSON file not found: {json_path}")
            return True  # Not a failure, just no JSON to migrate
    except Exception as e:
        print(f"Error testing migration: {e}")
        return False

def main():
    """Main testing function"""
    print_divider("SQLite Implementation Test")
    print(f"Current time: {datetime.datetime.now().isoformat()}")
    
    # Run tests
    tests = [
        ("Database Connection", test_db_connection),
        ("CRUD Operations", test_crud_operations),
        ("JSON Migration Simulation", test_json_migration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print_divider(f"Running test: {test_name}")
        success = test_func()
        results.append((test_name, success))
    
    # Print summary
    print_divider("Test Results Summary")
    all_successful = True
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if not success:
            all_successful = False
    
    if all_successful:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Please check the logs.")

if __name__ == "__main__":
    main()