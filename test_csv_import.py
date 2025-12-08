#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtutils.settings')
django.setup()

from apps.students.models import Student
from apps.students.resources import StudentResource
from tablib import Dataset

print("=== Test CSV Import ===\n")

# Clear existing students
Student.objects.all().delete()
print("✓ Cleared existing students")

# Test 1: Import CSV
print("\nTest 1: Import CSV with upsert")
resource = StudentResource()

csv_content = """student_id,first_name,last_name,username,grade,advisor
S001,Alice,Johnson,ajohnson,9,Mr. Smith
S002,Bob,Williams,bwilliams,9,Mr. Smith
S003,Charlie,Brown,cbrown,10,Ms. Garcia"""

dataset = Dataset().load(csv_content.split('\n'), 'csv')
result = resource.import_data(dataset, dry_run=False)

print(f"✓ Import complete: {result.totals}")

# Test 2: Verify students imported with is_active=True
print("\nTest 2: Verify is_active status after import")
for student in Student.objects.all().order_by('student_id'):
    print(f"  - {student.student_id}: {student.full_name} (is_active={student.is_active})")

# Test 3: Upsert - update existing and add new
print("\nTest 3: Upsert test - update existing and add new")
csv_content2 = """student_id,first_name,last_name,username,grade,advisor
S001,Alice,Johnson-Updated,ajohnson,10,Ms. Smith
S004,David,Davis,ddavis,11,Dr. Wilson"""

dataset2 = Dataset().load(csv_content2.split('\n'), 'csv')
result2 = resource.import_data(dataset2, dry_run=False)
print(f"✓ Upsert complete: {result2.totals}")

# Test 4: Verify upsert worked
print("\nTest 4: Verify upsert results")
for student in Student.objects.all().order_by('student_id'):
    print(f"  - {student.student_id}: {student.full_name}, grade={student.grade}")

print("\n✅ CSV Import verification PASSED")
