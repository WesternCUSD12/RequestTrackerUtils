import sqlite3
import os
import logging
from flask import current_app
from pathlib import Path

logger = logging.getLogger(__name__)

def get_db_path():
    """Get the path to the SQLite database file"""
    try:
        # Try to get path from Flask app config
        db_path = Path(current_app.instance_path) / 'database.sqlite'
        db_dir = db_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_path)
    except Exception as e:
        # Fallback if not in Flask context
        logger.warning(f"Cannot get database path from Flask app: {e}")
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        db_path = os.path.join(base_dir, 'instance', 'database.sqlite')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return db_path

def get_db_connection():
    """Get a database connection with row factory"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database schema"""
    conn = get_db_connection()
    try:
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
            check_in_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create device_info table for student devices
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            asset_id TEXT,
            asset_tag TEXT,
            device_type TEXT,
            serial_number TEXT,
            check_in_timestamp TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
        )
        ''')
        
        # Create device_logs table for check-in activities
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            date TEXT,
            time TEXT,
            asset_id TEXT,
            asset_tag TEXT,
            device_type TEXT,
            serial_number TEXT,
            previous_owner TEXT,
            ticket_id TEXT,
            has_ticket INTEGER,
            ticket_description TEXT,
            broken_screen INTEGER,
            checked_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create a trigger to update the updated_at field when a student record is updated
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_student_timestamp
        AFTER UPDATE ON students
        FOR EACH ROW
        BEGIN
            UPDATE students SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
        ''')
        
        conn.commit()
        logger.info("Database schema initialized")
    except Exception as e:
        logger.error(f"Error initializing database schema: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# Initialize the database when this module is imported
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")