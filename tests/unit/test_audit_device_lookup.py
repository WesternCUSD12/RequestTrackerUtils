"""
Tests for audit device lookup using student username.
Verifies that devices are correctly fetched from Request Tracker using only the username field.
"""

import json
from unittest.mock import patch
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from apps.students.models import Student
from apps.audit.models import AuditSession, AuditStudent


class AuditDeviceLookupLogicTests(TestCase):
    """Test the device lookup logic - verify student username is used for RT queries"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testteacher',
            password='testpass123'
        )
        
        self.student = Student.objects.create(
            student_id='S001',
            first_name='John',
            last_name='Doe',
            username='jdoe',  # **THIS IS THE USERNAME THAT MUST BE USED FOR RT LOOKUP**
            grade=9
        )
        
        self.session = AuditSession.objects.create(
            name='Test Audit Session',
            created_by=self.user,
            creator_name='Test Teacher'
        )
        
        self.audit_student = AuditStudent.objects.create(
            session=self.session,
            student=self.student,
            name=self.student.full_name,
            username=self.student.username
        )
        
        self.factory = RequestFactory()

    def _add_session_to_request(self, request):
        """Helper to add session middleware to request"""
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()
        request.session['user_role'] = 'teacher'
        request.session['username'] = 'testteacher'
        return request

    @patch('common.rt_api.get_assets_by_owner')
    @patch('common.rt_api.fetch_user_data')
    def test_username_used_for_rt_lookup(self, mock_fetch_user, mock_get_assets):
        """
        **CRITICAL TEST**
        Verify that student.username is used (and ONLY the username) to query Request Tracker.
        The endpoint must call fetch_user_data(username), not fetch_user_data(id).
        """
        from apps.audit.views import get_audit_student_devices
        
        # Setup mocks
        mock_fetch_user.return_value = {
            '_hyperlinks': [{'ref': 'self', 'type': 'user', 'id': 42}]
        }
        mock_get_assets.return_value = [
            {'id': 'W12-001', 'name': 'MacBook Pro', 'model': 'A1398'},
            {'id': 'W12-002', 'name': 'iPad Air', 'model': 'A1474'}
        ]
        
        # Create a real request object with session
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        # Call the view function directly
        response = get_audit_student_devices(
            request, 
            str(self.session.session_id), 
            self.audit_student.id
        )
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # **PRIMARY ASSERTION: Verify username was used for RT lookup**
        mock_fetch_user.assert_called_once_with('jdoe')  # Username!
        
        # Verify numeric ID was extracted and used for asset query
        mock_get_assets.assert_called_once_with('42')
        
        # Verify devices returned
        self.assertEqual(len(data['devices']), 2)
        self.assertEqual(data['devices'][0]['id'], 'W12-001')

    @patch('common.rt_api.fetch_user_data')
    @patch('common.rt_api.get_assets_by_owner')
    def test_empty_devices_when_no_username(self, mock_get_assets, mock_fetch_user):
        """Verify empty devices returned when student has no username"""
        from apps.audit.views import get_audit_student_devices
        
        # Create student without username
        student_no_username = Student.objects.create(
            student_id='S002',
            first_name='Jane',
            last_name='NoUsername',
            username='',  # NO USERNAME
            grade=10
        )
        
        audit_student_no_username = AuditStudent.objects.create(
            session=self.session,
            student=student_no_username,
            name=student_no_username.full_name,
            username=''
        )
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        response = get_audit_student_devices(
            request,
            str(self.session.session_id),
            audit_student_no_username.id
        )
        
        # Verify success
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # RT API should NOT be called if no username
        mock_fetch_user.assert_not_called()
        mock_get_assets.assert_not_called()
        
        # Empty devices returned
        self.assertEqual(data['devices'], [])

    @patch('common.rt_api.fetch_user_data')
    def test_rt_api_failure_returns_empty_gracefully(self, mock_fetch_user):
        """Verify graceful handling when RT API fails"""
        from apps.audit.views import get_audit_student_devices
        
        # Simulate RT API error
        mock_fetch_user.side_effect = Exception('RT API connection failed')
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        response = get_audit_student_devices(
            request,
            str(self.session.session_id),
            self.audit_student.id
        )
        
        # Should return 200 with empty devices, not 500 error
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['devices'], [])

    @patch('common.rt_api.get_assets_by_owner')
    @patch('common.rt_api.fetch_user_data')
    def test_numeric_id_extraction_from_hyperlinks(self, mock_fetch_user, mock_get_assets):
        """
        Verify correct numeric ID is extracted from RT hyperlinks.
        RT returns multiple hyperlinks; ensure we extract the one with ref='self' and type='user'.
        """
        from apps.audit.views import get_audit_student_devices
        
        # Mock RT response with multiple hyperlinks - must extract correct one
        mock_fetch_user.return_value = {
            'name': 'jdoe',
            '_hyperlinks': [
                {'ref': 'other', 'type': 'something', 'id': 99},   # Wrong
                {'ref': 'self', 'type': 'user', 'id': 42},         # Correct
                {'ref': 'other', 'type': 'user', 'id': 123}        # Wrong
            ]
        }
        
        mock_get_assets.return_value = [{'id': 'W12-001', 'name': 'Device 1', 'model': 'A'}]
        
        request = self.factory.get('/')
        request = self._add_session_to_request(request)
        
        response = get_audit_student_devices(
            request,
            str(self.session.session_id),
            self.audit_student.id
        )
        
        # Verify the CORRECT numeric ID (42) was used, not 99 or 123
        mock_get_assets.assert_called_once_with('42')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['devices']), 1)
