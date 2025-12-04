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
        
        # Create audit_sessions table (Feature 004-student-device-audit)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_sessions (
            session_id TEXT PRIMARY KEY,
            creator_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed')),
            student_count INTEGER DEFAULT 0
        )
        ''')
        
        # Create audit_students table (Feature 004-student-device-audit)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            name TEXT NOT NULL,
            grade TEXT NOT NULL,
            advisor TEXT NOT NULL,
            username TEXT,
            audited INTEGER DEFAULT 0,
            audit_timestamp TIMESTAMP,
            auditor_name TEXT,
            FOREIGN KEY (session_id) REFERENCES audit_sessions(session_id) ON DELETE CASCADE
        )
        ''')
        
        # Add username column if it doesn't exist (migration)
        try:
            cursor.execute("SELECT username FROM audit_students LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE audit_students ADD COLUMN username TEXT")
        
        # Create audit_device_records table (Feature 004-student-device-audit)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_device_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_student_id INTEGER NOT NULL,
            asset_id TEXT NOT NULL,
            asset_tag TEXT,
            serial_number TEXT,
            device_type TEXT,
            verified INTEGER DEFAULT 0,
            FOREIGN KEY (audit_student_id) REFERENCES audit_students(id) ON DELETE CASCADE
        )
        ''')
        
        # Create audit_notes table (Feature 004-student-device-audit)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_student_id INTEGER NOT NULL,
            note_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (audit_student_id) REFERENCES audit_students(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for audit tables (Feature 004-student-device-audit)
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_students_session 
        ON audit_students(session_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_students_audited 
        ON audit_students(audited)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_device_records_student 
        ON audit_device_records(audit_student_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_audit_notes_student 
        ON audit_notes(audit_student_id)
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