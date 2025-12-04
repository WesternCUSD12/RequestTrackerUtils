# Implementation Plan: Django Application Refactor

**Branch**: `005-django-refactor` | **Date**: 2025-12-01 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/005-django-refactor/spec.md`

## Summary

Refactor the Flask-based Request Tracker Utils application into a Django 4.2 LTS application while maintaining 100% feature parity. All existing routes, templates, and workflows (device check-in, student audits, label generation, RT API integration) must function identically. The migration uses Django apps to replace Flask blueprints (1:1 mapping), Django ORM for database operations, and Django's template engine for rendering. **Key constraint**: `/labels` routes remain public while all other routes require HTTP Basic Authentication. **Database approach**: New SQLite databases are created by Django; no data migration from Flask version required.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Django 4.2 LTS, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+, Pillow, WhiteNoise  
**Storage**: SQLite3 (new database at `{WORKING_DIR}/database.sqlite`), managed via Django ORM  
**Testing**: pytest (existing test suite), pytest-django for Django integration  
**Target Platform**: NixOS (production), macOS/Linux (development via devenv.nix)  
**Project Type**: Web application (Django monolith with 5 apps)  
**Performance Goals**: Startup under 5 seconds; stretch goals for response time/memory if issues arise  
**Constraints**: Feature parity with Flask version, no data migration required  
**Scale/Scope**: 5 Django apps, ~15 routes per app, 7 database models, ~20 templates

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### I. Documentation-First Development ✅

- **Status**: COMPLIANT
- Specification exists at `specs/005-django-refactor/spec.md` with user stories, acceptance criteria, success metrics
- Subsystem docs in `docs/architecture/` will be updated before code changes

### II. Modular Routing Architecture ✅

- **Status**: COMPLIANT (Django apps)
- 5 Django apps maintain separation of concerns: labels, devices, students, audit, assets
- URL prefixes preserved: `/labels/`, `/devices/`, `/students/`, `/assets/`
- One app per subsystem, thin views delegating to utilities

### III. Specification-Driven Testing ✅

- **Status**: COMPLIANT
- 3 independently testable user stories defined with explicit acceptance scenarios
- SC-001 requires all existing pytest tests pass without modification
- Tests organized under `tests/unit/` and `tests/integration/`

### IV. Request Tracker API Integration Standard ✅

- **Status**: COMPLIANT
- `common/rt_api.py` centralizes all RT API calls
- No direct RT API calls from views; all through centralized utility

### V. Configuration & Environment Management ✅

- **Status**: COMPLIANT
- Django settings.py uses environment variables (RT_TOKEN, AUTH_USERNAME, AUTH_PASSWORD, WORKING_DIR)
- Fail-fast validation for required config
- devenv.nix updated to include Django dependencies

**Constitution Gate**: ✅ PASSED - No violations requiring justification

## Project Structure

### Documentation (this feature)

```text
specs/005-django-refactor/
├── plan.md              # This file
├── research.md          # Phase 0 output ✅
├── data-model.md        # Phase 1 output ✅
├── quickstart.md        # Phase 1 output ✅
├── contracts/           # Phase 1 output ✅
│   ├── url_mappings.md
│   └── authentication.md
└── tasks.md             # Phase 2 output ✅
```

### Source Code (repository root)

**Current Flask Structure** (to be replaced):

```text
request_tracker_utils/
├── __init__.py          # Flask app factory
├── config.py            # Environment config
├── auth.py              # HTTP Basic Auth
├── routes/
│   ├── label_routes.py
│   ├── tag_routes.py
│   ├── device_routes.py
│   ├── student_routes.py
│   ├── asset_routes.py
│   └── audit_routes.py
├── templates/
├── static/
└── utils/
    ├── rt_api.py
    ├── db.py
    └── audit_tracker.py
```

**Target Django Structure**:

```text
rtutils/                     # Django project root
├── manage.py
├── rtutils/                 # Project settings package
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py          # Common settings
│   │   ├── development.py   # DEBUG=True
│   │   └── production.py    # DEBUG=False, security
│   ├── urls.py              # Root URLconf
│   ├── views.py             # Homepage view
│   └── wsgi.py
├── apps/
│   ├── labels/              # Label generation (PUBLIC routes)
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── utils.py         # QR/barcode generation
│   ├── devices/             # Device check-in/out (PROTECTED)
│   │   ├── models.py        # DeviceInfo, DeviceLog
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── management/
│   │       └── commands/
│   │           └── sync_chromebooks.py
│   ├── students/            # Student management (PROTECTED)
│   │   ├── models.py        # Student
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── management/
│   │       └── commands/
│   │           └── sync_rt_users.py
│   ├── audit/               # Device audit workflow (PROTECTED)
│   │   ├── models.py        # AuditSession, AuditStudent, etc.
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── tracker.py
│   └── assets/              # Asset tag management (PROTECTED)
│       ├── views.py
│       ├── urls.py
│       └── admin.py
├── common/                  # Shared utilities
│   ├── __init__.py
│   ├── rt_api.py            # RT API client (migrated)
│   ├── middleware.py        # SelectiveBasicAuthMiddleware
│   ├── label_config.py      # Label configuration
│   └── text_utils.py        # Text utilities
├── templates/               # Django templates (migrated)
│   ├── base.html
│   ├── labels/
│   ├── devices/
│   ├── students/
│   ├── audit/
│   └── assets/
├── static/                  # Static files (unchanged)
│   ├── css/
│   └── js/
└── tests/
    ├── unit/
    └── integration/
```

**Structure Decision**: Django project with 5 apps matching Flask blueprints. The `common/` package replaces `utils/` for shared code. Middleware handles selective authentication (public `/labels`, protected all others). WhiteNoise serves static files in production.

## Complexity Tracking

No constitution violations requiring justification. The migration from Flask to Django maintains all constitutional principles through equivalent Django patterns (apps = blueprints, middleware = before_request, settings.py = config.py).

---

## Phase 0: Research

### Research Questions

| ID  | Question                                                                         | Status                                                |
| --- | -------------------------------------------------------------------------------- | ----------------------------------------------------- |
| R1  | How to handle database with Django?                                              | ✅ New database created; no migration needed          |
| R2  | What Jinja2 → Django template syntax changes are required?                       | ✅ `url_for` → `{% url %}`, `static` → `{% static %}` |
| R3  | How to implement selective HTTP Basic Auth (public `/labels`, protected others)? | ✅ Custom middleware with PUBLIC_PATHS                |
| R4  | Can existing pytest suite run against Django without modification?               | ✅ pytest-django with `@pytest.mark.django_db`        |
| R5  | What packages need to be added to devenv.nix for Django?                         | ✅ Django 4.2 LTS + django-extensions + pytest-django |
| R6  | How to convert scheduled scripts to Django management commands?                  | ✅ `apps/{app}/management/commands/`                  |

_Output: [research.md](./research.md) ✅ Complete_

---

## Phase 1: Design

### Data Model

Django models for all 7 entities: [data-model.md](./data-model.md) ✅ Complete

- `students.models.Student`
- `devices.models.DeviceInfo`
- `devices.models.DeviceLog`
- `audit.models.AuditSession`
- `audit.models.AuditStudent`
- `audit.models.AuditDeviceRecord`
- `audit.models.AuditNote`

**Note**: New databases are created by Django; no data migration from Flask required.

### API Contracts

URL routing contracts: [contracts/](./contracts/) ✅ Complete

- [url_mappings.md](./contracts/url_mappings.md) - All route definitions
- [authentication.md](./contracts/authentication.md) - Auth middleware spec
- `/labels/*` - **PUBLIC** (no authentication)
- All other routes - Protected (HTTP Basic Auth)

### Quickstart Guide

Developer setup guide: [quickstart.md](./quickstart.md) ✅ Complete

---

## Key Clarifications Applied

| Issue                                | Resolution                                                            |
| ------------------------------------ | --------------------------------------------------------------------- |
| SC-008/SC-009 (performance baseline) | Marked as stretch goals; validated only if issues arise               |
| Database migration                   | New databases created; no Flask data migration                        |
| Static file serving                  | WhiteNoise middleware; no external server needed                      |
| FR-010 vs FR-016 (auth confusion)    | FR-010 = RT API auth (RT_TOKEN); FR-016 = web route auth (HTTP Basic) |
| SC-010 (file count metric)           | Removed; Django structure is inherently organized                     |

---

## Next Steps

1. ✅ Generate `research.md` - Phase 0 research output
2. ✅ Generate `data-model.md` - Phase 1 data model
3. ✅ Generate `contracts/` - Phase 1 URL routing contracts
4. ✅ Generate `quickstart.md` - Phase 1 developer guide
5. ✅ Generate `tasks.md` - Phase 2 task breakdown
6. ⏳ Update agent context: `.specify/scripts/bash/update-agent-context.sh copilot`
7. ⏳ Proceed to implementation
