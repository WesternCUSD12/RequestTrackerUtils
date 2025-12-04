# Quickstart: Django Application Refactor

**Feature**: 005-django-refactor  
**Date**: 2025-12-01

---

## Prerequisites

- Python 3.11+
- Existing Flask application data (SQLite database)
- devenv.nix environment

---

## Development Setup

### 1. Update devenv.nix

Add Django dependencies to `devenv.nix`:

```nix
# devenv.nix
{ pkgs, ... }:

{
  languages.python = {
    enable = true;
    package = pkgs.python311;
    venv.enable = true;
  };

  packages = with pkgs; [
    # ... existing packages
  ];
}
```

Update `pyproject.toml`:

```toml
[project]
dependencies = [
    # Existing dependencies
    "requests>=2.28",
    "reportlab>=3.6",
    "qrcode>=7.3",
    "python-barcode>=0.13",
    "Pillow",

    # Django dependencies (new)
    "django>=4.2,<5.0",
    "django-extensions>=3.2",
    "pytest-django>=4.5",
]
```

### 2. Reload Environment

```bash
direnv allow
```

### 3. Initialize Django Project

```bash
# Create Django project structure
django-admin startproject rtutils .

# Create apps directory
mkdir -p apps

# Create Django apps
python manage.py startapp labels apps/labels
python manage.py startapp devices apps/devices
python manage.py startapp students apps/students
python manage.py startapp audit apps/audit
python manage.py startapp assets apps/assets
```

### 4. Configure Settings

Edit `rtutils/settings.py`:

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Environment-based configuration
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
WORKING_DIR = os.environ.get('WORKING_DIR', str(Path.home() / '.rtutils'))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(WORKING_DIR, 'database.sqlite'),
    }
}

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Project apps
    'apps.labels',
    'apps.devices',
    'apps.students',
    'apps.audit',
    'apps.assets',
    # Dev tools
    'django_extensions',
]

# Authentication
AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.environ.get('AUTH_PASSWORD', 'admin')
PUBLIC_PATHS = ['/labels']

# RT API configuration
RT_URL = os.environ.get('RT_URL', 'https://tickets.wc-12.com')
RT_TOKEN = os.environ.get('RT_TOKEN', '')
API_ENDPOINT = '/REST/2.0'

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```

### 5. Migrate Existing Database

```bash
# Generate models from existing database
python manage.py inspectdb > models_snapshot.py

# Review and refactor into app-specific models.py files
# (See data-model.md for model definitions)

# Create initial migrations
python manage.py makemigrations

# Apply with --fake-initial (tables already exist)
python manage.py migrate --fake-initial
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

---

## Verification Checklist

### Routes

- [ ] `/labels/` - Label form loads (no auth)
- [ ] `/labels/print?assetId=X` - Label renders (no auth)
- [ ] `/devices/check-in` - Prompts for auth, then loads
- [ ] `/devices/audit` - Prompts for auth, then loads
- [ ] `/students/student-devices` - Prompts for auth, then loads
- [ ] `/admin/` - Django admin loads

### Authentication

- [ ] `/labels/*` routes work without credentials
- [ ] Other routes return 401 without credentials
- [ ] Other routes work with valid credentials
- [ ] Invalid credentials return 401

### Database

- [ ] Django admin shows all models
- [ ] Existing data visible in admin
- [ ] CRUD operations work in admin

### Templates

- [ ] All pages render without errors
- [ ] Static files (CSS/JS) load correctly
- [ ] Forms submit correctly

### RT API

- [ ] Label generation fetches asset data from RT
- [ ] Device check-in creates RT tickets
- [ ] Audit workflow fetches RT devices

---

## Common Issues

### Template Syntax Errors

If templates fail to render, check for Jinja2 syntax:

| Jinja2                                  | Django Fix              |
| --------------------------------------- | ----------------------- |
| `{{ url_for('route') }}`                | `{% url 'app:route' %}` |
| `{{ url_for('static', filename='x') }}` | `{% static 'x' %}`      |

### Database Migration Errors

If migrations fail:

```bash
# Reset migrations (CAREFUL - only in development)
python manage.py migrate --fake app_name zero
python manage.py migrate app_name --fake-initial
```

### Missing RT_TOKEN

Ensure environment variable is set:

```bash
export RT_TOKEN="your-token-here"
```

---

## Testing

### Run Existing Tests

```bash
# With pytest-django
pytest tests/

# Specific test file
pytest tests/unit/test_rt_api.py
```

### Run Django Tests

```bash
python manage.py test
```

### Test Authentication

```bash
# Test public route
curl http://localhost:8000/labels/

# Test protected route (should fail)
curl http://localhost:8000/devices/check-in

# Test with auth
curl -u admin:admin http://localhost:8000/devices/check-in
```

---

## Production Deployment

### Environment Variables

Set in production:

```bash
DEBUG=False
SECRET_KEY=<secure-random-key>
ALLOWED_HOSTS=your-domain.com
AUTH_USERNAME=<secure-username>
AUTH_PASSWORD=<secure-password>
RT_TOKEN=<rt-api-token>
```

### Collect Static Files

```bash
python manage.py collectstatic
```

### WSGI Server

Use Gunicorn or uWSGI instead of Django's development server:

```bash
gunicorn rtutils.wsgi:application --bind 0.0.0.0:8000
```

---

## Next Steps

1. Complete template migration (Jinja2 → Django)
2. Migrate views from Flask blueprints to Django views
3. Update URL routing to use Django URLconf
4. Run full test suite
5. Deploy to staging for testing
