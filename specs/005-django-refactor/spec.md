# Feature Specification: Django Application Refactor

**Feature Branch**: `005-django-refactor`  
**Created**: 2025-12-01  
**Status**: Draft  
**Input**: User description: "Project refactored into django app"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Maintain Existing Functionality (Priority: P1)

All current features and workflows remain functional after the Django migration. Users can continue to perform device check-ins, manage student records, print labels, and conduct device audits without interruption.

**Why this priority**: Core business operations must continue uninterrupted. This ensures zero downtime and maintains user trust during the technical migration.

**Independent Test**: Can be fully tested by running the complete existing test suite against the Django implementation and verifying all features work identically to the Flask version.

**Acceptance Scenarios**:

1. **Given** the Django application is running, **When** a user accesses any existing route (e.g., `/devices/check-in`, `/students/student-devices`, `/devices/audit`), **Then** the page loads with the same functionality as the Flask version
2. **Given** the Django application is running, **When** a user performs device check-in, **Then** the device is checked in and logged to the database correctly
3. **Given** the Django application is running, **When** a user uploads a CSV for student audit, **Then** students are imported and the audit workflow functions identically
4. **Given** the Django application is running, **When** a user generates QR code labels, **Then** labels are generated with correct format and data

---

### User Story 2 - Simplified Development Workflow (Priority: P2)

Developers can leverage Django's built-in admin interface, ORM, and migrations system to manage data and schema changes more efficiently than the current Flask/SQLite implementation.

**Why this priority**: Developer productivity improvements reduce maintenance costs and enable faster feature development without affecting end users immediately.

**Independent Test**: Can be tested by accessing Django admin at `/admin`, performing CRUD operations on models, and running database migrations using Django's management commands.

**Acceptance Scenarios**:

1. **Given** a developer has admin credentials, **When** they access `/admin`, **Then** they can view and manage all database models (students, devices, audit sessions, etc.)
2. **Given** a database schema change is needed, **When** a developer creates a Django migration, **Then** the migration applies successfully and preserves existing data
3. **Given** a developer needs to query data, **When** they use Django ORM in views or management commands, **Then** queries execute correctly and return expected results

---

### User Story 3 - Enhanced Configuration Management (Priority: P3)

System configuration uses Django's settings framework with environment-specific overrides (development, production) and proper secret management instead of ad-hoc .env loading.

**Why this priority**: Better configuration management improves security and deployment flexibility but doesn't directly impact daily user operations.

**Independent Test**: Can be tested by running the application with different environment configurations (DEBUG=True vs False, different database backends) and verifying appropriate settings are applied.

**Acceptance Scenarios**:

1. **Given** the application is deployed to production, **When** environment variables are set for production, **Then** DEBUG is disabled, static files are served correctly, and production database is used
2. **Given** a developer runs locally, **When** they use development settings, **Then** DEBUG is enabled and local database is used
3. **Given** sensitive credentials are needed, **When** environment variables are configured, **Then** secrets are loaded securely without being committed to version control

---

### Edge Cases

- How does the system handle database connection failures with Django's connection pooling?

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST preserve all existing routes and URL patterns from the Flask application
- **FR-002**: System MUST create new SQLite database with Django ORM schema (no migration from Flask data required)
- **FR-003**: System MUST support the Request Tracker API integration without changes to the RT endpoints
- **FR-004**: System MUST preserve all existing templates and render them with Django's template engine
- **FR-005**: System MUST maintain the current student check-in workflow (CSV upload, device assignment, check-in logs)
- **FR-006**: System MUST maintain the audit workflow (CSV upload, session management, device verification)
- **FR-007**: System MUST maintain label generation functionality (QR codes, barcodes, PDF output)
- **FR-008**: System MUST support Google Admin SDK integration for Chromebook data sync
- **FR-009**: System MUST provide Django management commands for scheduled tasks (RT user sync, Chromebook sync)
- **FR-010**: System MUST authenticate to Request Tracker API via RT_TOKEN environment variable (separate from web route authentication)
- **FR-011**: System MUST support Django migrations for future schema changes
- **FR-012**: System MUST provide Django admin interface for all data models
- **FR-013**: System MUST maintain the devenv.nix development environment configuration
- **FR-014**: System MUST use Django ORM for all database operations instead of raw SQL
- **FR-015**: System MUST organize code into Django apps (students, devices, labels, audit)
- **FR-016**: System MUST implement HTTP Basic Authentication for all routes EXCEPT the `/labels` route and its sub-routes (which must remain public for external access)

### Key Entities _(include if feature involves data)_

All entities remain the same as the existing Flask application, but will be defined as Django models:

- **Student**: Represents a student with ID, name, grade, RT user ID, device check-in status, check-in date
- **DeviceInfo**: Represents devices assigned to students with asset ID, tag, type, serial number, check-in timestamp
- **DeviceLog**: Represents device check-in activity logs with timestamp, asset details, previous owner, ticket information, condition flags
- **AuditSession**: Represents an audit session with creator name, created timestamp, status, student count
- **AuditStudent**: Represents a student in an audit session with name, grade, advisor, username, audit status, timestamp, auditor name
- **AuditDeviceRecord**: Represents device records found during audit with asset details and verification status
- **AuditNote**: Represents notes captured during audit with note text, created timestamp, creator name

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: All existing automated tests pass against the Django implementation without modification
- **SC-002**: Application startup time remains under 5 seconds in development mode
- **SC-003**: Django database initialization creates correct schema for all models
- **SC-004**: All existing API endpoints respond with identical output to Flask version (measured via integration tests)
- **SC-005**: Django admin interface provides full CRUD operations for all models with zero configuration beyond model definitions
- **SC-006**: Development environment setup (via devenv.nix) completes in under 2 minutes
- **SC-007**: All existing templates render correctly with Django template engine without syntax errors
- **SC-008**: _(Stretch goal)_ Memory usage remains comparable to Flask version; validated only if performance issues reported
- **SC-009**: _(Stretch goal)_ Response times remain comparable to Flask version; validated only if performance issues reported

## Clarifications

### Session 2025-12-01

- Q: Should the `/labels` route be public while all other routes require authentication? → A: Yes, `/labels` and all sub-routes must be public (no authentication) to allow external systems (RT webhooks, label printers) to access label generation. All other routes require HTTP Basic Authentication.
- Q: SC-008/SC-009 require measuring performance "within 10% of Flask version" but no baseline exists. How to handle? → A: Remove as formal success criteria; treat as stretch goals validated only if performance issues arise post-migration.
- Q: What happens when existing SQLite database schema doesn't match initial Django migrations? → A: New databases are created; no migration from existing Flask data. Django starts with fresh schema.
- Q: What happens if Django static file serving fails in production? → A: Use WhiteNoise middleware; Django serves static files directly without external server.
- Q: FR-010 says "RT token-based" auth, FR-016 says "HTTP Basic Auth" - are these the same? → A: No. FR-010 is RT API authentication (RT_TOKEN env var for server-to-RT calls). FR-016 is web route authentication (HTTP Basic Auth for browser access).
- Q: SC-010 "file count reduction" - what counts? → A: Remove SC-010; Django app structure is inherently organized; file count is not a meaningful metric.

## Assumptions

- Django 4.2 LTS will be used for long-term support and stability
- New SQLite database will be created by Django; no data migration from Flask version required
- Flask blueprints will map one-to-one with Django apps (students app, devices app, audit app, labels app)
- Django's built-in template engine will be used instead of Jinja2
- Django's development server will be used locally; production deployment strategy is out of scope
- Existing devenv.nix environment will be updated to include Django and related dependencies
- URL routing will use Django's URLconf instead of Flask's blueprint registration
- Forms will use Django forms framework instead of WTForms
- Static file handling will use Django's static files app (`django.contrib.staticfiles`)
- Existing JavaScript and CSS files will be moved to Django's static file structure without modification

## Out of Scope

- Migrating from SQLite to PostgreSQL (can be done later)
- Adding user authentication beyond RT token (can be done later with Django's auth framework)
- Implementing Django REST Framework for API endpoints
- Adding Django Channels for WebSocket support
- Implementing Django's caching framework
- Adding Django's testing framework (will use existing test suite initially)
- Deploying with Django-specific WSGI servers (Gunicorn, uWSGI)
- Implementing Django's i18n/l10n for internationalization
