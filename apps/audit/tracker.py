"""Audit session management utilities.

This module provides the AuditSession class for managing student device audit
sessions, including session creation, student tracking, and audit completion.
"""

import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from request_tracker_utils.utils.db import get_db_connection

logger = logging.getLogger(__name__)


class AuditTracker:
    """Manages audit sessions and student device verification tracking."""
    
    @staticmethod
    def get_or_create_active_session(creator_name: str = 'System') -> str:
        """Get the active session or create one if none exists.
        
        Only one session is active at a time. Multiple users can audit simultaneously.
        
        Args:
            creator_name: Name of the person creating/accessing the session
            
        Returns:
            session_id: UUID of the active session
            
        Raises:
            sqlite3.Error: If database operation fails
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check for existing active session
            cursor.execute("""
                SELECT session_id FROM audit_sessions
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                session_id = row['session_id']
                logger.debug(f"Using existing active session {session_id}")
                return session_id
            
            # Create new session if none exists
            session_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO audit_sessions (session_id, creator_name, status, student_count)
                VALUES (?, ?, 'active', 0)
            """, (session_id, creator_name))
            
            conn.commit()
            logger.info(f"Created new audit session {session_id} by {creator_name}")
            return session_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get/create audit session: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def replace_students(session_id: str, students: List[Dict[str, str]], creator_name: str) -> int:
        """Replace all students in the active session with a new list.
        
        This clears existing students and adds new ones.
        
        Args:
            session_id: UUID of the audit session
            students: List of student dicts with name, grade, advisor
            creator_name: Name of person uploading the list
            
        Returns:
            Number of students added
            
        Raises:
            sqlite3.Error: If database operation fails
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Delete existing students for this session
            # (CASCADE will automatically delete related notes and device records)
            cursor.execute("""
                DELETE FROM audit_students WHERE session_id = ?
            """, (session_id,))
            
            # Insert new students
            for student in students:
                username = student.get('username', '')
                logger.debug(f"Inserting student: name={student['name']}, username='{username}'")
                cursor.execute("""
                    INSERT INTO audit_students (session_id, name, grade, advisor, username, audited)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (session_id, student['name'], student['grade'], student['advisor'], username))
            
            # Update session metadata
            cursor.execute("""
                UPDATE audit_sessions
                SET student_count = ?, creator_name = ?, created_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (len(students), creator_name, session_id))
            
            conn.commit()
            logger.info(f"Replaced students in session {session_id} with {len(students)} new students by {creator_name}")
            return len(students)
            
        except sqlite3.Error as e:
            logger.error(f"Failed to replace students in session: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def create_session(creator_name: str) -> str:
        """Create a new audit session.
        
        Args:
            creator_name: Name of the person creating the audit session
            
        Returns:
            session_id: UUID of the created session
            
        Raises:
            sqlite3.Error: If database operation fails
        """
        session_id = str(uuid.uuid4())
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO audit_sessions (session_id, creator_name, status, student_count)
                VALUES (?, ?, 'active', 0)
            """, (session_id, creator_name))
            
            conn.commit()
            logger.info(f"Created audit session {session_id} by {creator_name}")
            return session_id
            
        except sqlite3.Error as e:
            logger.error(f"Failed to create audit session: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def add_students(session_id: str, students: List[Dict[str, str]]) -> int:
        """Add students to an audit session.
        
        Args:
            session_id: UUID of the audit session
            students: List of student dicts with name, grade, advisor
            
        Returns:
            Number of students added
            
        Raises:
            sqlite3.Error: If database operation fails
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert students
            for student in students:
                cursor.execute("""
                    INSERT INTO audit_students (session_id, name, grade, advisor, audited)
                    VALUES (?, ?, ?, ?, 0)
                """, (session_id, student['name'], student['grade'], student['advisor']))
            
            # Update student count
            cursor.execute("""
                UPDATE audit_sessions
                SET student_count = ?
                WHERE session_id = ?
            """, (len(students), session_id))
            
            conn.commit()
            logger.info(f"Added {len(students)} students to session {session_id}")
            return len(students)
            
        except sqlite3.Error as e:
            logger.error(f"Failed to add students to session: {e}")
            raise
        finally:
            conn.close()
    
    @staticmethod
    def get_session(session_id: str) -> Optional[Dict]:
        """Get audit session details.
        
        Args:
            session_id: UUID of the audit session
            
        Returns:
            Session dict or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT session_id, creator_name, created_at, status, student_count
                FROM audit_sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get session: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_statistics() -> Dict[str, int]:
        """Get audit statistics for the active session.
        
        Returns:
            Dictionary with statistics:
            - total_students: Total students in active session
            - audited: Number of audited students
            - pending: Number of students not yet audited
            - completion_rate: Percentage of students audited
            - session_id: Active session ID (or None)
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get active session
            cursor.execute("""
                SELECT session_id FROM audit_sessions
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            session_row = cursor.fetchone()
            session_id = session_row['session_id'] if session_row else None
            
            # Get total students and audited count from active session
            if session_id:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_students,
                        SUM(CASE WHEN audited = 1 THEN 1 ELSE 0 END) as audited
                    FROM audit_students
                    WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()
                total_students = row['total_students'] or 0
                audited = row['audited'] or 0
            else:
                total_students = 0
                audited = 0
            
            pending = total_students - audited
            completion_rate = (audited / total_students * 100) if total_students > 0 else 0.0
            
            return {
                'session_id': session_id,
                'total_students': total_students,
                'audited': audited,
                'pending': pending,
                'completion_rate': completion_rate
            }
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {
                'session_id': None,
                'total_students': 0,
                'audited': 0,
                'pending': 0,
                'completion_rate': 0.0
            }
        finally:
            conn.close()
    
    @staticmethod
    def get_students_by_session(session_id: str) -> List[Dict]:
        """Get all students for a specific audit session.
        
        Args:
            session_id: UUID of the audit session
            
        Returns:
            List of student dictionaries
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, name, grade, advisor, username, audited, audit_timestamp, auditor_name
                FROM audit_students
                WHERE session_id = ?
                ORDER BY name, grade
            """, (session_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get students for session {session_id}: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    def get_student(student_id: int) -> Optional[Dict]:
        """Get student details from audit_students table.
        
        Args:
            student_id: Student record ID
            
        Returns:
            Student dict or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, session_id, name, grade, advisor, username, audited, audit_timestamp, auditor_name
                FROM audit_students
                WHERE id = ?
            """, (student_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return dict(row)
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get student: {e}")
            return None
        finally:
            conn.close()
    
    @staticmethod
    def mark_student_audited(student_id: int, auditor_name: str, 
                            device_records: List[Dict], notes: str = "") -> bool:
        """Mark a student as audited with device verification records.
        
        Args:
            student_id: Student record ID
            auditor_name: Name of person conducting audit
            device_records: List of dicts with asset_id, asset_tag, serial_number, device_type, verified
            notes: Optional notes for IT staff
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update student audit status
            cursor.execute("""
                UPDATE audit_students
                SET audited = 1,
                    audit_timestamp = CURRENT_TIMESTAMP,
                    auditor_name = ?
                WHERE id = ?
            """, (auditor_name, student_id))
            
            # Insert device records
            for device in device_records:
                cursor.execute("""
                    INSERT INTO audit_device_records 
                    (audit_student_id, asset_id, asset_tag, serial_number, device_type, verified)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    student_id,
                    device.get('asset_id', ''),
                    device.get('asset_tag', ''),
                    device.get('serial_number', ''),
                    device.get('device_type', ''),
                    device.get('verified', 0)
                ))
            
            # Insert notes if provided
            if notes:
                cursor.execute("""
                    INSERT INTO audit_notes (audit_student_id, note_text, created_by)
                    VALUES (?, ?, ?)
                """, (student_id, notes, auditor_name))
            
            conn.commit()
            logger.info(f"Marked student {student_id} as audited by {auditor_name}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to mark student audited: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_completed_audits(session_id: str) -> List[Dict]:
        """Get all completed audits for a session.
        
        Args:
            session_id: UUID of the audit session
            
        Returns:
            List of completed student audit records
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, grade, advisor, audit_timestamp, auditor_name
                FROM audit_students
                WHERE session_id = ? AND audited = 1
                ORDER BY audit_timestamp DESC
            """, (session_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get completed audits: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    def restore_student_for_reaudit(student_id: int) -> bool:
        """Restore student to active audit list for re-audit.
        
        Args:
            student_id: Student record ID
            
        Returns:
            True if successful, False otherwise
            
        Note:
            Preserves existing audit_device_records as historical data.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE audit_students
                SET audited = 0,
                    audit_timestamp = NULL,
                    auditor_name = NULL
                WHERE id = ?
            """, (student_id,))
            
            conn.commit()
            logger.info(f"Restored student {student_id} for re-audit")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Failed to restore student for re-audit: {e}")
            return False
        finally:
            conn.close()
    
    @staticmethod
    def get_all_notes(session_id: Optional[str] = None, 
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None) -> List[Dict]:
        """Get audit notes with optional filtering.
        
        Args:
            session_id: Optional session UUID to filter by
            date_from: Optional start date (ISO format)
            date_to: Optional end date (ISO format)
            
        Returns:
            List of notes with student and device information
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    n.id,
                    n.note_text,
                    n.created_at,
                    n.created_by,
                    s.name as student_name,
                    s.grade,
                    s.advisor,
                    s.session_id
                FROM audit_notes n
                JOIN audit_students s ON n.audit_student_id = s.id
                WHERE 1=1
            """
            params = []
            
            if session_id:
                query += " AND s.session_id = ?"
                params.append(session_id)
            
            if date_from:
                query += " AND n.created_at >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND n.created_at <= ?"
                params.append(date_to)
            
            query += " ORDER BY n.created_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get audit notes: {e}")
            return []
        finally:
            conn.close()
    
    @staticmethod
    def clear_all_audit_data() -> Dict[str, any]:
        """Clear all audit-related data from the database.
        
        Deletes all records from audit tables:
        - audit_notes
        - audit_device_records  
        - audit_students
        - audit_sessions
        
        Returns:
            Dictionary with success status and counts of deleted records
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get counts before deletion
            cursor.execute("SELECT COUNT(*) as count FROM audit_sessions")
            sessions_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM audit_students")
            students_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM audit_device_records")
            devices_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM audit_notes")
            notes_count = cursor.fetchone()['count']
            
            # Delete in reverse foreign key order
            cursor.execute("DELETE FROM audit_notes")
            cursor.execute("DELETE FROM audit_device_records")
            cursor.execute("DELETE FROM audit_students")
            cursor.execute("DELETE FROM audit_sessions")
            
            conn.commit()
            
            logger.info(f"Cleared all audit data: {sessions_count} sessions, {students_count} students, {devices_count} devices, {notes_count} notes")
            
            return {
                'success': True,
                'sessions_deleted': sessions_count,
                'students_deleted': students_count,
                'devices_deleted': devices_count,
                'notes_deleted': notes_count
            }
            
        except sqlite3.Error as e:
            logger.error(f"Failed to clear audit data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            conn.close()
