#!/usr/bin/env python3
"""Test script to verify authentication is working correctly."""

import requests
import sys

BASE_URL = "http://localhost:8000"

def test_public_route():
    """Test that /labels routes are accessible without auth."""
    print("Testing public route: /labels/")
    response = requests.get(f"{BASE_URL}/labels/")
    
    if response.status_code == 200:
        print("✓ /labels/ is public (no auth required)")
        return True
    else:
        print(f"✗ /labels/ returned {response.status_code} (expected 200)")
        return False

def test_protected_route_without_auth():
    """Test that protected routes require authentication."""
    print("\nTesting protected route without auth: /")
    response = requests.get(f"{BASE_URL}/")
    
    if response.status_code == 401:
        print("✓ / requires authentication (returned 401)")
        return True
    else:
        print(f"✗ / returned {response.status_code} (expected 401)")
        return False

def test_protected_route_with_auth():
    """Test that protected routes work with valid credentials."""
    print("\nTesting protected route with auth: /")
    response = requests.get(
        f"{BASE_URL}/",
        auth=('admin', 'admin')
    )
    
    if response.status_code == 200:
        print("✓ / accessible with valid credentials")
        return True
    else:
        print(f"✗ / returned {response.status_code} with auth (expected 200)")
        return False

def test_protected_route_with_bad_auth():
    """Test that protected routes reject invalid credentials."""
    print("\nTesting protected route with bad auth: /")
    response = requests.get(
        f"{BASE_URL}/",
        auth=('wrong', 'credentials')
    )
    
    if response.status_code == 401:
        print("✓ / rejects invalid credentials (returned 401)")
        return True
    else:
        print(f"✗ / returned {response.status_code} with bad auth (expected 401)")
        return False

def main():
    """Run all authentication tests."""
    print("=== Authentication Tests ===\n")
    print(f"Testing against: {BASE_URL}\n")
    
    results = [
        test_public_route(),
        test_protected_route_without_auth(),
        test_protected_route_with_auth(),
        test_protected_route_with_bad_auth()
    ]
    
    print("\n=== Results ===")
    passed = sum(results)
    total = len(results)
    print(f"{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All authentication tests passed!")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}")
        print("Make sure the Flask server is running on port 8000")
        sys.exit(1)
