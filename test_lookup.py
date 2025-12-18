#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rtutils.settings")
sys.path.insert(0, "/Users/jmartin/rtutils")
django.setup()

from apps.audit.views import lookup_device_owner
from django.http import HttpRequest
from django.contrib.sessions.backends.db import SessionStore

# Create a mock request
request = HttpRequest()
request.method = "GET"
request.session = SessionStore()
request.session["user_role"] = "teacher"
request.session["username"] = "teacher"

# Test the function
try:
    response = lookup_device_owner(request, "WHS-C158")
    print("Response status:", response.status_code)
    print("Response content:", response.content.decode())
except Exception as e:
    print("Error:", e)
    import traceback

    traceback.print_exc()
