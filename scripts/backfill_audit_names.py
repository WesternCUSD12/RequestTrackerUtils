#!/usr/bin/env python3
import os
import sys
import pathlib
import django

# Ensure project root is on sys.path so 'rtutils' package can be imported
project_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtutils.settings')
django.setup()

from apps.audit.models import AuditSession

count = 0
for s in AuditSession.objects.filter(name=''):
    created = getattr(s, 'created_at', None)
    if created:
        try:
            created_str = created.strftime("%Y-%m-%d %H:%M")
        except Exception:
            created_str = str(created)
    else:
        created_str = 'unknown'
    creator = getattr(s, 'creator_name', None) or getattr(s, 'creator_username', None) or 'unknown'
    s.name = f"Audit {created_str} - {creator}"
    s.save()
    count += 1

print('updated', count)
