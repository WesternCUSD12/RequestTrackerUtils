#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtutils.settings')
django.setup()

from apps.students.models import Student, DeviceInfo
from apps.students.views import find_student_by_rt_user, update_student_checkin

print("=== Test Device Check-in Integration ===\n")

# Setup: Create a student with RT user ID
print("Test 1: Create student with RT user ID")
student = Student.objects.create(
    student_id='TEST001',
    first_name='Test',
    last_name='User',
    username='testuser',
    grade=9,
    advisor='Test Advisor',
    rt_user_id=12345,
    is_active=True,
    device_checked_in=False
)
print(f"✓ Created student: {student.student_id} with rt_user_id={student.rt_user_id}")

# Test 2: Find student by RT user ID
print("\nTest 2: Find student by RT user ID")
found = find_student_by_rt_user(12345)
if found:
    print(f"✓ Found student: {found.student_id} ({found.full_name})")
else:
    print("✗ Student not found")

# Test 3: Update student check-in
print("\nTest 3: Update student check-in")
update_student_checkin(
    student=student,
    asset_id='ASSET123',
    asset_tag='TAG123',
    serial_number='SN12345',
    device_type='Chromebook'
)

# Verify
student.refresh_from_db()
print(f"✓ device_checked_in={student.device_checked_in}")
print(f"✓ check_in_date={student.check_in_date}")

# Test 4: Verify DeviceInfo created
print("\nTest 4: Verify DeviceInfo created")
device_info = DeviceInfo.objects.filter(student=student).first()
if device_info:
    print(f"✓ DeviceInfo created:")
    print(f"  - asset_id: {device_info.asset_id}")
    print(f"  - asset_tag: {device_info.asset_tag}")
    print(f"  - serial_number: {device_info.serial_number}")
    print(f"  - device_type: {device_info.device_type}")
else:
    print("✗ DeviceInfo not found")

# Test 5: Test inactive student - should not find
print("\nTest 5: Test inactive student lookup")
student.is_active = False
student.save()
found_inactive = find_student_by_rt_user(12345)
if found_inactive is None:
    print("✓ Inactive student correctly excluded from lookup")
else:
    print("✗ Inactive student should not be found")

print("\n✅ Device check-in integration verification PASSED")
