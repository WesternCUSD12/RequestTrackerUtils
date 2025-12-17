"""
Tests for the manual prefetch live-fallback behavior.

Ensures that when the bulk cached assets do not contain a student's devices,
we call `get_assets_by_owner`, merge returned assets into `asset_cache`, and
create `AuditDeviceRecord` entries.
"""

from unittest.mock import patch
from django.test import TestCase
from apps.students.models import Student
from apps.audit.models import AuditSession, AuditStudent, AuditDeviceRecord


class PrefetchFallbackTests(TestCase):
    def setUp(self):
        # Create a simple session and student with username
        self.session = AuditSession.objects.create(name="Prefetch Test Session")
        self.student = Student.objects.create(
            student_id="S100",
            first_name="Alice",
            last_name="Example",
            username="alice123",
            grade=10,
        )
        self.audit_student = AuditStudent.objects.create(
            session=self.session,
            student=self.student,
            name=self.student.full_name,
            username=self.student.username,
        )

    @patch("common.rt_api.fetch_all_assets_cached")
    @patch("common.rt_api.get_assets_by_owner")
    @patch("common.rt_api.fetch_user_data")
    def test_fallback_merges_and_creates_records(
        self, mock_fetch_user, mock_get_assets, mock_fetch_all
    ):
        """When the bulk cache misses, get_assets_by_owner should be called and
        its results merged into asset_cache, and AuditDeviceRecord entries created."""
        # Simulate empty bulk cache
        mock_fetch_all.return_value = []

        # Simulate user data with numeric RT id
        mock_fetch_user.return_value = {
            "_hyperlinks": [{"ref": "self", "type": "user", "id": 777}]
        }

        # Simulate live assets returned for owner 777
        live_asset = {
            "id": "ASSET-777",
            "Name": "Test Device",
            "CustomFields": [{"name": "Device Type", "value": "Chromebook"}],
            "Owner": {"id": 777},
        }
        mock_get_assets.return_value = [live_asset]

        # Import and run the prefetch helper
        from apps.audit.views import _run_manual_prefetch

        result = _run_manual_prefetch(str(self.session.session_id), job=None)

        # Verify that get_assets_by_owner was called once with numeric id '777'
        mock_get_assets.assert_called_once_with("777")

        # Verify that a device record was created for the audit_student
        records = AuditDeviceRecord.objects.filter(audit_student=self.audit_student)
        self.assertEqual(records.count(), 1)
        rec = records.first()
        self.assertEqual(rec.asset_id, "ASSET-777")
        self.assertEqual(rec.device_type, "Chromebook")

        # Check result indicates processed student and total_devices
        self.assertEqual(result["processed_students"], 1)
        self.assertEqual(result["total_devices"], 1)
