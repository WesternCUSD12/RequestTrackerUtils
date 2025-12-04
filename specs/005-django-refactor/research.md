# Research: Django Application Refactor

**Feature**: 005-django-refactor  
**Date**: 2025-12-01  
**Status**: Complete

---

## R1: SQLite Database with Django ORM

**Question**: How to handle database with Django?

**Decision**: Create new SQLite database with Django ORM; no migration from Flask data required

**Rationale**:

- Fresh database simplifies Django setup - no schema compatibility concerns
- Django manages schema through migrations from the start
- No risk of data corruption from migration process
- Flask data can be manually imported if needed later

**Alternatives Considered**:

- `inspectdb` + `--fake-initial`: Adds complexity for data we don't need to preserve
- Manual data migration scripts: Unnecessary overhead

**Implementation**:

```bash
# Step 1: Create models in app-specific models.py files per data-model.md

# Step 2: Create initial migrations
python manage.py makemigrations students
python manage.py makemigrations devices
python manage.py makemigrations audit

# Step 3: Apply migrations to create fresh database
python manage.py migrate
```

---

## R2: Jinja2 to Django Template Syntax

**Question**: What Jinja2 → Django template syntax changes are required?

**Decision**: Migrate to Django Template Language (DTL) with minimal syntax changes

**Rationale**:

- DTL is similar enough to Jinja2 that most templates work with minor changes
- No need for django-jinja package (adds complexity)
- Better integration with Django's built-in template tags

**Key Syntax Changes**:

| Jinja2                              | Django                             |
| ----------------------------------- | ---------------------------------- |
| `{{ url_for('route_name') }}`       | `{% url 'route_name' %}`           |
| `{{ url_for('route_name', id=x) }}` | `{% url 'route_name' x %}`         |
| `{% include "file.html" %}`         | `{% include "file.html" %}` (same) |
| `{% extends "base.html" %}`         | `{% extends "base.html" %}` (same) |
| `{{ variable\|filter }}`            | `{{ variable\|filter }}` (same)    |
| `{% for item in items %}`           | `{% for item in items %}` (same)   |
| `{% if condition %}`                | `{% if condition %}` (same)        |

**Templates Requiring Changes**:

- All templates using `url_for()` → replace with `{% url %}` tag
- Static file references: `{{ url_for('static', filename='x') }}` → `{% static 'x' %}`
- Form handling: Minor changes for Django forms

---

## R3: Selective HTTP Basic Authentication

**Question**: How to implement selective authentication (public `/labels`, protected others)?

**Decision**: Custom Django middleware checking `request.path`

**Rationale**:

- Middleware runs before view resolution, cleanest approach
- Single point of authentication logic
- Easy to configure public paths via settings

**Alternatives Considered**:

- Decorator on each view: Repetitive, easy to forget
- View mixins: Overkill for simple auth
- Django REST Framework auth: Not using DRF

**Implementation**:

```python
# common/middleware.py
import base64
from django.conf import settings
from django.http import HttpResponse

class SelectiveBasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = getattr(settings, 'PUBLIC_PATHS', ['/labels'])

    def __call__(self, request):
        # Check if path is public
        if any(request.path.startswith(p) for p in self.public_paths):
            return self.get_response(request)

        # Require authentication for all other paths
        if not self._check_auth(request):
            return self._unauthorized_response()

        return self.get_response(request)

    def _check_auth(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Basic '):
            return False
        try:
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)
            return (username == settings.AUTH_USERNAME and
                    password == settings.AUTH_PASSWORD)
        except Exception:
            return False

    def _unauthorized_response(self):
        response = HttpResponse('Authentication required', status=401)
        response['WWW-Authenticate'] = 'Basic realm="Login Required"'
        return response
```

**Settings Configuration**:

```python
# settings.py
PUBLIC_PATHS = ['/labels']
AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'admin')

MIDDLEWARE = [
    # ... other middleware
    'common.middleware.SelectiveBasicAuthMiddleware',
]
```

---

## R4: pytest-django Integration

**Question**: Can existing pytest suite run against Django without modification?

**Decision**: Use pytest-django plugin with minimal test changes

**Rationale**:

- pytest-django provides Django test database fixtures
- Existing pytest tests can run with `@pytest.mark.django_db` decorator
- No need to convert to Django TestCase

**Alternatives Considered**:

- Convert to Django TestCase: Breaks existing test patterns
- Dual test setup: Complex, hard to maintain
- No integration: Tests won't have database access

**Implementation**:

```bash
# Install pytest-django
pip install pytest-django

# Create pytest.ini or pyproject.toml section
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "rtutils.settings"
python_files = ["test_*.py", "*_test.py"]
```

**Test Changes Required**:

```python
# Add to tests that need database access
import pytest

@pytest.mark.django_db
def test_student_creation():
    # ... test code using Django ORM
```

---

## R5: devenv.nix Django Dependencies

**Question**: What packages need to be added to devenv.nix for Django?

**Decision**: Add Django 4.2 LTS and minimal supporting packages

**Rationale**:

- Django 4.2 is LTS (supported until April 2026)
- django-extensions provides useful dev tools
- pytest-django for testing integration

**Packages to Add**:

```nix
# devenv.nix additions
packages = [
  # ... existing packages
];

languages.python = {
  enable = true;
  package = pkgs.python311;
  venv.enable = true;
};

# pyproject.toml additions
[project.dependencies]
django = ">=4.2,<5.0"
django-extensions = ">=3.2"
pytest-django = ">=4.5"
```

---

## R6: Django Management Commands

**Question**: How to convert scheduled scripts to Django management commands?

**Decision**: Create management commands in appropriate app's `management/commands/` directory

**Rationale**:

- Django management commands have access to settings, ORM, and app context
- Can be run via `python manage.py <command>`
- Easy integration with cron/systemd

**Scripts to Convert**:
| Script | New Command | App |
|--------|-------------|-----|
| `scripts/scheduled_rt_user_sync.py` | `sync_rt_users` | students |
| `scripts/sync_chromebook_data.py` | `sync_chromebooks` | devices |

**Implementation**:

```python
# apps/students/management/commands/sync_rt_users.py
from django.core.management.base import BaseCommand
from common.rt_api import rt_api_request

class Command(BaseCommand):
    help = 'Sync users from Request Tracker'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        # ... sync logic using Django ORM
        self.stdout.write(self.style.SUCCESS('Sync complete'))
```

---

## Summary

All research questions resolved. Key decisions:

1. **Database**: New SQLite database created by Django; no Flask data migration required
2. **Templates**: DTL with `url_for` → `{% url %}` conversion
3. **Authentication**: Custom middleware for path-based auth
4. **Testing**: pytest-django with `@pytest.mark.django_db`
5. **Dependencies**: Django 4.2 LTS + django-extensions + pytest-django
6. **Commands**: Management commands in app-specific directories

**Ready for Phase 1: Design**
