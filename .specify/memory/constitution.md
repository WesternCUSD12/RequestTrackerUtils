<!--
  Sync Impact Report:
  - Version: 1.0.0 → 2.0.0 (MAJOR: Django migration - framework change)
  - Modified Principles: II. Modular Routing Architecture (Flask blueprints → Django apps)
  - Modified Sections: Technology Stack Standards (added Django 4.2 LTS)
  - Added: Authentication requirements (public /labels, protected others)
  - Templates Requiring Updates:
    ⚠ Pending: Update plan-template.md Constitution Check for Django apps
    ⚠ Pending: Update copilot-instructions.md with Django stack
  - Follow-up TODOs:
    - Remove Flask references after 005-django-refactor merges
    - Update deployment docs for Django WSGI
-->

# RequestTracker Utils Constitution

## Core Principles

### I. Documentation-First Development

Every feature begins with comprehensive documentation **before** implementation. Subsystem documentation lives in `docs/architecture/` and must be updated before code changes. Developers MUST:

- Create specification in `specs/[feature]/spec.md` with user stories, acceptance criteria, and success metrics
- Update or create subsystem documentation in `docs/architecture/` describing current state before refactoring
- Maintain evidence snapshots in `docs/architecture/_inputs/` with timestamps and provenance
- Link all changes back to specification requirements

**Rationale**: Documentation-first prevents scope creep, ensures shared understanding, and creates onboarding artifacts. The README's "Architecture" section explicitly mandates this workflow: "Start here when onboarding or researching changes."

### II. Modular Routing Architecture

All routes MUST be organized into Django apps with explicit, non-overlapping URL prefixes. Every app represents a cohesive functional domain. Developers MUST:

- Register apps in `INSTALLED_APPS` and include URLs with explicit `path()` prefixes (e.g., `/labels/`, `/devices/`, `/students/`, `/assets/`)
- Maintain separation of concerns: one app per subsystem
- Keep view handlers thin: delegate business logic to utility modules
- Follow naming convention: `apps/[subsystem]/urls.py` with `app_name = '[subsystem]'`
- Organize models, views, urls, and admin in each app directory

**Rationale**: Django app architecture prevents route collisions, enables modular testing, and maps directly to subsystem documentation structure. This pattern is consistently enforced across all 5 app modules in the codebase.

### III. Specification-Driven Testing

All features require independently testable user stories with explicit acceptance scenarios. Testing MUST cover:

- **Unit tests**: For utilities and business logic (e.g., RT API clients, database operations, CSV validators)
- **Integration tests**: For multi-component workflows (e.g., device check-in flow, asset creation + label printing)
- **Independent testability**: Each user story must be verifiable in isolation without implementing other stories

Test files MUST be organized under `tests/unit/` and `tests/integration/` mirroring the code structure. Use `pytest` as the standard test runner.

**Rationale**: Specification-driven testing ensures features deliver measurable user value and prevents regression. The spec template explicitly requires "INDEPENDENTLY TESTABLE" user stories, and implementation checklists mandate test creation for all utilities and workflows.

### IV. Request Tracker API Integration Standard

All interactions with the Request Tracker (RT) system MUST go through centralized API utilities. Developers MUST:

- Use `common/rt_api.py` for all RT API calls
- Handle RT API failures gracefully with user-friendly error messages
- Implement retry logic for transient failures (network timeouts, rate limits)
- Log all RT API interactions with structured logging (request details, response status, error context)

No direct RT API calls from view handlers. API utilities must be independently testable with mocked responses.

**Rationale**: Centralized RT integration isolates external dependencies, enables consistent error handling, and simplifies testing. This pattern is observed in Student-Device integration and asset management features.

### V. Configuration & Environment Management

Application configuration MUST be externalized and environment-specific. Developers MUST:

- Use environment variables for all deployment-specific values (RT URLs, API tokens, file paths, database locations)
- Implement **fail-fast validation**: Application MUST abort startup with clear error if required configuration is missing (e.g., `RT_TOKEN`)
- Provide sensible defaults for development environments in `rtutils/settings/development.py`
- Use Django's settings module pattern with base/development/production splits
- Document all configuration options in README with required/optional distinction
- Never commit secrets or environment-specific values to version control

Platform detection (macOS vs Linux) for default paths is acceptable but must be overridable via environment variables.

**Rationale**: Environment-based configuration enables safe multi-environment deployment (dev/staging/production) and prevents configuration-related incidents. Django's settings framework provides structured environment management.

## Technology Stack Standards

### Language & Framework

- **Python**: 3.11+ (minimum version)
- **Web Framework**: Django 4.2 LTS
- **Database**: SQLite3 (stored in `{WORKING_DIR}/database.sqlite`), managed via Django ORM
- **Template Engine**: Django Template Language (DTL)
- **Testing**: pytest with pytest-django for database and RT API mocking
- **Admin Interface**: Django Admin for model management

### Required Libraries

- `requests` 2.28+ (RT API client)
- `reportlab` 3.6+ (PDF label generation)
- `qrcode` 7.3+ (QR code generation)
- `python-barcode` 0.13+ (barcode generation)
- `Pillow` (image manipulation for labels)
- `whitenoise` (static file serving in production)

### Authentication Requirements

- **Public Routes**: `/labels/*` routes MUST remain public (no authentication) for external system access (RT webhooks, label printers)
- **Protected Routes**: All other routes (`/devices/*`, `/students/*`, `/audit/*`, `/assets/*`, `/admin/*`) require HTTP Basic Authentication
- **Implementation**: Use Django middleware (`common/middleware.py`) with `PUBLIC_PATHS` configuration
- **Credentials**: `AUTH_USERNAME` and `AUTH_PASSWORD` environment variables

### Code Quality Tools

- **Linting**: `ruff check .` (enforced in CI/CD)
- **Formatting**: Follow PEP 8 with ruff defaults
- **Docstrings**: Google-style docstrings for all public functions (Args/Returns/Raises)

### Deployment

- **NixOS**: Primary deployment target using `flake.nix` and `devenv.nix`
- **Deployment Command**: `sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils`
- **Service Management**: systemd service module with configurable host/port/secrets
- **WSGI Server**: Django's built-in runserver for development; Gunicorn/uWSGI for production
- **Static Files**: `python manage.py collectstatic` with WhiteNoise middleware

## Documentation-First Workflow

### Subsystem Documentation Requirements

1. **Before Code Changes**: Update or create subsystem documentation in `docs/architecture/[subsystem].md`
2. **Evidence Capture**: Embed snapshots (tree outputs, command results, diagrams) in `docs/architecture/_inputs/` with timestamps
3. **Cross-Reference**: Link changes in `specs/[feature]/quickstart.md` and README after subsystem docs are updated
4. **Review Gate**: All merge requests touching `request_tracker_utils/` MUST cite the affected subsystem doc

### Specification Structure

Every feature must have a directory under `specs/[NNN-feature-name]/` containing:

- `spec.md`: User stories with priorities (P1/P2/P3), acceptance scenarios, success criteria
- `plan.md`: Technical implementation plan, database schema, API contracts, risk register
- `tasks.md`: Granular task breakdown with dependencies and parallelization markers
- `checklists/implementation.md`: Progress tracking checklist with 100+ verification items
- `research.md`: Answers to pre-implementation research questions

### Documentation Update Sequence

1. Create/update specification → 2. Update subsystem architecture docs → 3. Implement code → 4. Update README/quickstart guides

## Governance

### Amendment Process

1. Propose amendment with rationale and affected principles
2. Document impact on existing features and templates
3. Increment version according to semantic versioning:
   - **MAJOR**: Backward-incompatible governance changes or principle removals
   - **MINOR**: New principles added or material expansions
   - **PATCH**: Clarifications, wording improvements, non-semantic refinements
4. Update `LAST_AMENDED_DATE` to current date (ISO 8601 format: YYYY-MM-DD)
5. Propagate changes to all affected templates and command prompts

### Compliance Verification

- All pull requests MUST verify compliance with core principles
- Code review checklist must include constitution compliance check
- Deviations require explicit justification and documentation in spec's risk register
- Complexity additions must be justified with measurable benefits
- All merge requests touching `apps/` or `common/` MUST cite the affected subsystem doc

### Template Synchronization

When constitution changes, verify and update:

- `.specify/templates/plan-template.md` (Constitution Check section alignment)
- `.specify/templates/spec-template.md` (User story and acceptance criteria requirements)
- `.specify/templates/tasks-template.md` (Task categorization and testing requirements)
- `.specify/templates/commands/*.md` (Agent-specific guidance alignment)

**Version**: 2.0.0 | **Ratified**: 2025-01-08 | **Last Amended**: 2025-12-01
