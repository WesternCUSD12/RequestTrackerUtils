"""
Tests for Phase 5: Teacher Device Audit Sessions

Covers business logic and model operations.
"""
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.utils import timezone
from apps.audit.models import AuditSession, AuditStudent
from apps.students.models import Student


class AuditSessionBusinessLogicTests(TestCase):
    """Test core audit session functionality"""

    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            password='pass123',
            first_name='John',
            last_name='Doe'
        )
        teacher_group, _ = Group.objects.get_or_create(name='TEACHERS')
        self.teacher_user.groups.add(teacher_group)
        
        self.admin_user = User.objects.create_superuser(
            username='admin1',
            email='admin@test.com',
            password='pass123'
        )
        
        self.student = Student.objects.create(
            student_id='S001',
            first_name='Alice',
            last_name='Smith',
            username='asmith',
            grade=10,
            advisor='Smith'
        )
        
        self.session = AuditSession.objects.create(
            created_by=self.teacher_user,
            creator_name='John Doe',
            status='active'
        )

    def test_active_sessions_queryable(self):
        """Active sessions are queryable from database"""
        active = AuditSession.objects.filter(status='active')
        self.assertEqual(active.count(), 1)
        self.assertEqual(active[0].session_id, self.session.session_id)

    def test_closed_sessions_separate_from_active(self):
        """Closed sessions are separate from active"""
        closed = AuditSession.objects.create(
            created_by=self.teacher_user,
            creator_name='John Doe',
            status='closed',
            closed_at=timezone.now()
        )
        
        active = AuditSession.objects.filter(status='active')
        closed_set = AuditSession.objects.filter(status='closed')
        
        self.assertEqual(active.count(), 1)
        self.assertEqual(closed_set.count(), 1)

    def test_session_closure_updates_status(self):
        """Closing session updates status and timestamp"""
        self.assertEqual(self.session.status, 'active')
        self.assertIsNone(self.session.closed_at)
        self.assertFalse(self.session.is_closed)
        
        # Close the session
        self.session.status = 'closed'
        self.session.closed_at = timezone.now()
        self.session.save()
        
        # Verify
        refreshed = AuditSession.objects.get(session_id=self.session.session_id)
        self.assertEqual(refreshed.status, 'closed')
        self.assertIsNotNone(refreshed.closed_at)
        self.assertTrue(refreshed.is_closed)


class AuditStudentBusinessLogicTests(TestCase):
    """Test audit student functionality"""

    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username='teacher1',
            password='pass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.student = Student.objects.create(
            student_id='S001',
            first_name='Alice',
            last_name='Smith',
            username='asmith',
            grade=10,
            advisor='Smith'
        )
        
        self.session = AuditSession.objects.create(
            created_by=self.teacher_user,
            creator_name='John Doe',
            status='active'
        )
        
        self.audit_student = AuditStudent.objects.create(
            session=self.session,
            student=self.student,
            name='Alice Smith',
            grade='10',
            advisor='Smith',
            audited=False
        )

    def test_mark_audited_updates_database(self):
        """Marking student as audited updates database"""
        # Verify initial state
        self.assertFalse(self.audit_student.audited)
        self.assertIsNone(self.audit_student.audit_timestamp)
        
        # Mark as audited
        self.audit_student.audited = True
        self.audit_student.audit_timestamp = timezone.now()
        self.audit_student.auditor_name = 'John Doe'
        self.audit_student.save()
        
        # Verify update
        refreshed = AuditStudent.objects.get(pk=self.audit_student.pk)
        self.assertTrue(refreshed.audited)
        self.assertIsNotNone(refreshed.audit_timestamp)
        self.assertEqual(refreshed.auditor_name, 'John Doe')

    def test_students_filterable_by_grade(self):
        """Students can be filtered by grade"""
        # Create additional students
        for grade in ['11', '12']:
            AuditStudent.objects.create(
                session=self.session,
                student=None,
                name=f'Student Grade {grade}',
                grade=grade,
                advisor='Smith'
            )
        
        grade_10 = self.session.students.filter(grade='10')
        grade_11 = self.session.students.filter(grade='11')
        
        self.assertEqual(grade_10.count(), 1)
        self.assertEqual(grade_11.count(), 1)

    def test_students_filterable_by_advisor(self):
        """Students can be filtered by advisor"""
        # Create student with different advisor
        AuditStudent.objects.create(
            session=self.session,
            student=None,
            name='Student Other Advisor',
            grade='10',
            advisor='Johnson'
        )
        
        smith_students = self.session.students.filter(advisor='Smith')
        johnson_students = self.session.students.filter(advisor='Johnson')
        
        self.assertEqual(smith_students.count(), 1)
        self.assertEqual(johnson_students.count(), 1)

    def test_audit_history_preserved_after_closure(self):
        """Audit history preserved when session is closed"""
        # Mark as audited
        self.audit_student.audited = True
        self.audit_student.auditor_name = 'John Doe'
        self.audit_student.audit_timestamp = timezone.now()
        self.audit_student.save()
        
        # Close session
        self.session.status = 'closed'
        self.session.closed_at = timezone.now()
        self.session.save()
        
        # Verify history still accessible
        refreshed = AuditStudent.objects.get(pk=self.audit_student.pk)
        self.assertTrue(refreshed.audited)
        self.assertIsNotNone(refreshed.audit_timestamp)
