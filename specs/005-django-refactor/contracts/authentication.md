# Authentication Contract

**Feature**: 005-django-refactor  
**Date**: 2025-12-01

---

## Overview

HTTP Basic Authentication is implemented via Django middleware. The `/labels` route and all sub-routes are PUBLIC (no authentication required). All other routes require valid credentials.

---

## Configuration

### Environment Variables

| Variable        | Required | Default | Description              |
| --------------- | -------- | ------- | ------------------------ |
| `AUTH_USERNAME` | No       | `admin` | HTTP Basic Auth username |
| `AUTH_PASSWORD` | No       | `admin` | HTTP Basic Auth password |

### Settings

```python
# rtutils/settings.py

# Authentication configuration
AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'admin')

# Paths that do not require authentication
PUBLIC_PATHS = [
    '/labels',  # Label generation (external access)
]

# Middleware configuration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'common.middleware.SelectiveBasicAuthMiddleware',  # Custom auth
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

---

## Middleware Implementation

```python
# common/middleware.py

import base64
from django.conf import settings
from django.http import HttpResponse


class SelectiveBasicAuthMiddleware:
    """
    Middleware that requires HTTP Basic Authentication for all routes
    EXCEPT those matching PUBLIC_PATHS in settings.

    Usage:
        - Add to MIDDLEWARE in settings.py
        - Configure AUTH_USERNAME, AUTH_PASSWORD, and PUBLIC_PATHS
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = getattr(settings, 'PUBLIC_PATHS', [])
        self.username = getattr(settings, 'AUTH_USERNAME', 'admin')
        self.password = getattr(settings, 'AUTH_PASSWORD', 'admin')

    def __call__(self, request):
        # Check if path is public
        if self._is_public_path(request.path):
            return self.get_response(request)

        # Require authentication for all other paths
        if not self._check_auth(request):
            return self._unauthorized_response()

        return self.get_response(request)

    def _is_public_path(self, path):
        """Check if the request path matches any public path prefix."""
        return any(path.startswith(p) for p in self.public_paths)

    def _check_auth(self, request):
        """Validate HTTP Basic Authentication credentials."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Basic '):
            return False

        try:
            # Decode base64 credentials
            encoded_credentials = auth_header[6:]  # Remove 'Basic '
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)

            return username == self.username and password == self.password
        except (ValueError, UnicodeDecodeError):
            return False

    def _unauthorized_response(self):
        """Return 401 Unauthorized response with WWW-Authenticate header."""
        response = HttpResponse(
            'Authentication required. Please provide valid credentials.',
            status=401,
            content_type='text/plain'
        )
        response['WWW-Authenticate'] = 'Basic realm="Login Required"'
        return response
```

---

## Behavior Matrix

| Scenario                      | Request                                     | Response                   |
| ----------------------------- | ------------------------------------------- | -------------------------- |
| Public route                  | `GET /labels/print?assetId=123`             | 200 OK (no auth check)     |
| Protected route, no auth      | `GET /devices/check-in`                     | 401 Unauthorized           |
| Protected route, valid auth   | `GET /devices/check-in` (with Basic auth)   | 200 OK                     |
| Protected route, invalid auth | `GET /devices/check-in` (wrong credentials) | 401 Unauthorized           |
| Django admin, valid admin     | `GET /admin/` (Django admin login)          | 200 OK (Django admin auth) |

---

## Testing

### Test Cases

```python
# tests/unit/test_auth_middleware.py

import pytest
import base64
from django.test import RequestFactory
from common.middleware import SelectiveBasicAuthMiddleware


@pytest.fixture
def middleware():
    def get_response(request):
        from django.http import HttpResponse
        return HttpResponse('OK')
    return SelectiveBasicAuthMiddleware(get_response)


@pytest.fixture
def rf():
    return RequestFactory()


def test_public_path_no_auth_required(middleware, rf):
    """Public paths should not require authentication."""
    request = rf.get('/labels/print')
    response = middleware(request)
    assert response.status_code == 200


def test_protected_path_requires_auth(middleware, rf):
    """Protected paths should require authentication."""
    request = rf.get('/devices/check-in')
    response = middleware(request)
    assert response.status_code == 401
    assert 'WWW-Authenticate' in response


def test_protected_path_valid_auth(middleware, rf, settings):
    """Protected paths should allow valid credentials."""
    credentials = base64.b64encode(
        f"{settings.AUTH_USERNAME}:{settings.AUTH_PASSWORD}".encode()
    ).decode()
    request = rf.get('/devices/check-in')
    request.META['HTTP_AUTHORIZATION'] = f'Basic {credentials}'
    response = middleware(request)
    assert response.status_code == 200


def test_protected_path_invalid_auth(middleware, rf):
    """Protected paths should reject invalid credentials."""
    credentials = base64.b64encode(b'wrong:credentials').decode()
    request = rf.get('/devices/check-in')
    request.META['HTTP_AUTHORIZATION'] = f'Basic {credentials}'
    response = middleware(request)
    assert response.status_code == 401
```

---

## Client Usage

### Browser

When accessing protected routes in a browser, users will see the standard HTTP Basic Auth dialog prompting for username and password.

### curl

```bash
# Public route (no auth needed)
curl http://localhost:8000/labels/print?assetId=123

# Protected route (auth required)
curl -u admin:admin http://localhost:8000/devices/check-in
```

### Python requests

```python
import requests

# Public route
response = requests.get('http://localhost:8000/labels/print?assetId=123')

# Protected route
response = requests.get(
    'http://localhost:8000/devices/check-in',
    auth=('admin', 'admin')
)
```

---

## Security Considerations

1. **Change default credentials** in production via environment variables
2. **Use HTTPS** in production to encrypt credentials in transit
3. **Consider rate limiting** to prevent brute force attacks
4. **Log authentication failures** for security monitoring
5. **Never commit credentials** to version control
