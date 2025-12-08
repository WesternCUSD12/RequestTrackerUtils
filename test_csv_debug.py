#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtutils.settings')
django.setup()

from apps.students.models import Student
from apps.students.resources import StudentResource
from tablib import Dataset

print("=== Debug CSV Import Errors ===\n")

Student.objects.all().delete()

resource = StudentResource()

csv_content = """student_id,first_name,last_name,username,grade,advisor
S001,Alice,Johnson,ajohnson,9,Mr. Smith
S002,Bob,Williams,bwilliams,9,Mr. Smith
S003,Charlie,Brown,cbrown,10,Ms. Garcia"""

dataset = Dataset().load(csv_content.split('\n'), 'csv')

try:
    result = resource.import_data(dataset, dry_run=True, raise_errors=True)
    print(f"Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
