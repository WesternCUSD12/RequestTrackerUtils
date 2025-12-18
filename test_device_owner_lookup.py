#!/usr/bin/env python
"""
Test script for device owner lookup functionality
"""

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


def test_lookup_device_owner():
    """Test the device owner lookup API endpoint"""
    print("Testing device owner lookup functionality...")

    # Create a mock request
    request = HttpRequest()
    request.method = "GET"
    request.session = SessionStore()
    request.session["user_role"] = "teacher"
    request.session["username"] = "testteacher"

    # Test with a sample asset ID
    test_asset_ids = ["WHS-C158", "W12-001", "INVALID-ASSET"]

    for asset_id in test_asset_ids:
        print(f"\n--- Testing asset_id: {asset_id} ---")
        try:
            response = lookup_device_owner(request, asset_id)
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.content.decode()}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_lookup_device_owner()
