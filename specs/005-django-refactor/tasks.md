# Tasks: Django Application Refactor

**Input**: Design documents from `/specs/005-django-refactor/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Not explicitly requested in spec. Tests are included only for critical path verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Django project initialization and basic structure

- [x] T001 Update pyproject.toml with Django 4.2 LTS dependencies
- [x] T002 Update devenv.nix to include Django packages
- [x] T003 Create Django project structure with `django-admin startproject rtutils .`
- [x] T004 [P] Create apps directory structure at `apps/`
- [x] T005 [P] Create Django app: `apps/labels/` (startapp labels apps/labels)
- [x] T006 [P] Create Django app: `apps/devices/` (startapp devices apps/devices)
- [x] T007 [P] Create Django app: `apps/students/` (startapp students apps/students)
- [x] T008 [P] Create Django app: `apps/audit/` (startapp audit apps/audit)
- [x] T009 [P] Create Django app: `apps/assets/` (startapp assets apps/assets)
- [x] T010 [P] Create common utilities package at `common/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration & Settings

- [x] T011 Configure Django settings.py with environment variables (RT_TOKEN, AUTH_USERNAME, AUTH_PASSWORD, WORKING_DIR, DEBUG)
- [x] T012 [P] Add INSTALLED_APPS configuration for all apps in rtutils/settings.py
- [x] T013 [P] Configure DATABASES to create new SQLite at `{WORKING_DIR}/database.sqlite`
- [x] T014 [P] Configure TEMPLATES with Django template backend and templates directory
- [x] T015 [P] Configure STATIC_URL and STATICFILES_DIRS in settings.py

### Authentication Middleware

- [x] T016 Implement SelectiveBasicAuthMiddleware in common/middleware.py (public /labels, protected others)
- [x] T017 [P] Add PUBLIC_PATHS, AUTH_USERNAME, AUTH_PASSWORD settings
- [x] T018 Add middleware to MIDDLEWARE list in settings.py

### Shared Utilities

- [x] T019 Migrate rt_api.py from request_tracker_utils/utils/ to common/rt_api.py
- [x] T020 [P] Migrate label_config.py to common/label_config.py
- [x] T021 [P] Migrate text_utils.py to common/text_utils.py

### Database Models

- [x] T022 Create Student model in apps/students/models.py per data-model.md
- [x] T023 [P] Create DeviceInfo model in apps/devices/models.py per data-model.md
- [x] T024 [P] Create DeviceLog model in apps/devices/models.py per data-model.md
- [x] T025 Create AuditSession model in apps/audit/models.py per data-model.md
- [x] T026 [P] Create AuditStudent model in apps/audit/models.py per data-model.md
- [x] T027 [P] Create AuditDeviceRecord model in apps/audit/models.py per data-model.md
- [x] T028 [P] Create AuditNote model in apps/audit/models.py per data-model.md
- [x] T029 Run `python manage.py makemigrations` for all apps
- [x] T030 Run `python manage.py migrate` to create fresh database schema

### Root URLconf

- [x] T031 Create root URLconf in rtutils/urls.py with all app includes per contracts/url_mappings.md
- [x] T032 [P] Create homepage view in rtutils/views.py

**Checkpoint**: Foundation ready - Django server should start and show homepage

---

## Phase 3: User Story 1 - Maintain Existing Functionality (Priority: P1) 🎯 MVP

**Goal**: All current features and workflows remain functional after Django migration

**Independent Test**: Run existing test suite + manually verify all routes work identically to Flask

### Labels App (PUBLIC - No Auth)

- [x] T033 Create apps/labels/urls.py with all label routes per contracts/url_mappings.md
- [x] T034 [P] [US1] Migrate label_home view to apps/labels/views.py
- [x] T035 [P] [US1] Migrate print_label view to apps/labels/views.py
- [x] T036 [P] [US1] Migrate batch_labels view to apps/labels/views.py
- [x] T037 [P] [US1] Migrate search_assets_json view to apps/labels/views.py
- [x] T038 [P] [US1] Migrate remaining label utility views (search, lookup, debug) to apps/labels/views.py
- [x] T039 [US1] Migrate QR code and barcode generation to apps/labels/utils.py
- [x] T040 [US1] Migrate label templates from request_tracker_utils/templates/ to templates/labels/

### Devices App (PROTECTED)

- [x] T041 Create apps/devices/urls.py with device routes per contracts/url_mappings.md
- [x] T042 [P] [US1] Migrate check_in_home view to apps/devices/views.py
- [x] T043 [P] [US1] Migrate check_in_asset view to apps/devices/views.py
- [x] T044 [P] [US1] Migrate process_check_in view to apps/devices/views.py
- [x] T045 [P] [US1] Migrate check_out_home view to apps/devices/views.py
- [x] T046 [P] [US1] Migrate check_in_logs view to apps/devices/views.py
- [x] T047 [US1] Migrate device templates to templates/devices/

### Audit App (PROTECTED)

- [x] T048 Create apps/audit/urls.py with audit routes per contracts/url_mappings.md
- [x] T049 [P] [US1] Migrate audit_home view to apps/audit/views.py
- [x] T050 [P] [US1] Migrate upload_csv view to apps/audit/views.py
- [x] T051 [P] [US1] Migrate view_session view to apps/audit/views.py
- [x] T052 [P] [US1] Migrate session_students view to apps/audit/views.py
- [x] T053 [P] [US1] Migrate student_detail view to apps/audit/views.py
- [x] T054 [P] [US1] Migrate student_devices view to apps/audit/views.py
- [x] T055 [P] [US1] Migrate verify_student view to apps/audit/views.py
- [x] T056 [P] [US1] Migrate re_audit_student view to apps/audit/views.py
- [x] T057 [P] [US1] Migrate completed_students view to apps/audit/views.py
- [x] T058 [P] [US1] Migrate audit_notes view to apps/audit/views.py
- [x] T059 [P] [US1] Migrate export_notes view to apps/audit/views.py
- [x] T060 [P] [US1] Migrate clear_audit view to apps/audit/views.py
- [x] T061 [US1] Migrate audit_tracker.py to apps/audit/tracker.py
- [x] T062 [US1] Migrate csv_validator.py to apps/audit/validators.py
- [x] T063 [US1] Migrate audit templates to templates/audit/

### Students App (PROTECTED)

- [x] T064 Create apps/students/urls.py with student routes per contracts/url_mappings.md
- [x] T065 [P] [US1] Migrate student_devices view to apps/students/views.py
- [x] T066 [P] [US1] Migrate import_students view to apps/students/views.py
- [x] T067 [US1] Migrate student templates to templates/students/

### Assets App (PROTECTED)

- [x] T068 Create apps/assets/urls.py with asset routes per contracts/url_mappings.md
- [x] T069 [P] [US1] Migrate create_asset view to apps/assets/views.py
- [x] T070 [P] [US1] Migrate next_tag view to apps/assets/views.py
- [x] T071 [P] [US1] Migrate confirm_tag view to apps/assets/views.py
- [x] T072 [P] [US1] Migrate reset_tag view to apps/assets/views.py
- [x] T073 [P] [US1] Migrate update_name view to apps/assets/views.py
- [x] T074 [P] [US1] Migrate webhook_created view to apps/assets/views.py
- [x] T075 [P] [US1] Migrate tag_admin view to apps/assets/views.py
- [x] T076 [US1] Migrate asset templates to templates/assets/

### Template Migration (Jinja2 → Django)

- [x] T077 [US1] Migrate base.html template with url_for → {% url %} conversion
- [x] T078 [P] [US1] Update all templates: {{ url_for('x') }} → {% url 'x' %}
- [x] T079 [P] [US1] Update all templates: {{ url_for('static', filename='x') }} → {% static 'x' %}
- [x] T080 [US1] Copy static files to static/ directory

### Homepage & Root Views

- [x] T081 [US1] Migrate homepage view with route documentation to rtutils/views.py
- [x] T082 [US1] Add root-level asset tag routes to rtutils/urls.py

**Checkpoint**: User Story 1 complete - All Flask routes should work identically in Django

---

## Phase 4: User Story 2 - Simplified Development Workflow (Priority: P2)

**Goal**: Django admin interface and ORM for database management

**Independent Test**: Access `/admin`, perform CRUD operations, run migrations

### Django Admin Configuration

- [x] T083 [US2] Create superuser with `python manage.py createsuperuser`
- [x] T084 [P] [US2] Register Student model in apps/students/admin.py per data-model.md
- [x] T085 [P] [US2] Register DeviceInfo model in apps/devices/admin.py per data-model.md
- [x] T086 [P] [US2] Register DeviceLog model in apps/devices/admin.py per data-model.md
- [x] T087 [P] [US2] Register AuditSession model in apps/audit/admin.py per data-model.md
- [x] T088 [P] [US2] Register AuditStudent model in apps/audit/admin.py per data-model.md
- [x] T089 [P] [US2] Register AuditDeviceRecord model in apps/audit/admin.py per data-model.md
- [x] T090 [P] [US2] Register AuditNote model in apps/audit/admin.py per data-model.md

### ORM Refactoring

- [x] T091 [US2] Refactor apps/students/views.py to use Django ORM instead of raw SQL
- [x] T092 [P] [US2] Refactor apps/devices/views.py to use Django ORM
- [x] T093 [P] [US2] Refactor apps/audit/views.py to use Django ORM
- [x] T094 [P] [US2] Refactor apps/audit/tracker.py to use Django ORM
- [x] T095 [US2] Remove db.py raw SQL utilities (replaced by ORM)

### Management Commands

- [x] T096 [P] [US2] Create sync_rt_users management command in apps/students/management/commands/
- [x] T097 [P] [US2] Create sync_chromebooks management command in apps/devices/management/commands/

**Checkpoint**: User Story 2 complete - Django admin works, ORM queries functional

---

## Phase 5: User Story 3 - Enhanced Configuration Management (Priority: P3)

**Goal**: Django settings framework with environment-specific overrides

**Independent Test**: Run with DEBUG=True and DEBUG=False, verify appropriate behavior

### Settings Refactoring

- [x] T098 [US3] Create rtutils/settings/base.py with common settings
- [x] T099 [P] [US3] Create rtutils/settings/development.py with DEBUG=True settings
- [x] T100 [P] [US3] Create rtutils/settings/production.py with DEBUG=False, security settings
- [x] T101 [US3] Update rtutils/settings/**init**.py to select settings based on DJANGO_SETTINGS_MODULE
- [x] T102 [US3] Add fail-fast validation for required environment variables (RT_TOKEN)

### WSGI Configuration

- [x] T103 [P] [US3] Update rtutils/wsgi.py to use correct settings module
- [x] T104 [P] [US3] Create rtutils/asgi.py for future async support

### Static Files (Production)

- [x] T105 [US3] Add STATIC_ROOT setting for collectstatic
- [x] T106 [US3] Configure WhiteNoise or similar for production static serving

**Checkpoint**: User Story 3 complete - Environment-specific configuration works

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

### Testing Integration

- [x] T107 [P] Configure pytest.ini with DJANGO_SETTINGS_MODULE
- [x] T108 [P] Install pytest-django and update requirements
- [x] T109 Run existing test suite: `pytest tests/`

### Documentation

- [x] T110 [P] Update README.md with Django setup instructions
- [x] T111 [P] Update docs/architecture/ subsystem docs for Django structure
- [x] T112 Run quickstart.md validation checklist

### Cleanup

- [x] T113 [P] Remove old Flask app code from request_tracker_utils/ (after verification)
- [x] T114 [P] Update run.py to use Django development server
- [x] T115 Update NixOS deployment configuration for Django

### Verification

- [x] T116 Verify all routes respond identically to Flask version
- [x] T117 Verify /labels routes work without authentication
- [x] T118 Verify all other routes require HTTP Basic Auth
- [x] T119 Verify Django admin CRUD operations work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion - BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion (can run parallel to US1)
- **Phase 5 (US3)**: Depends on Phase 2 completion (can run parallel to US1/US2)
- **Phase 6 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational phase - Core migration
- **User Story 2 (P2)**: Can start after Foundational phase - Admin interface (independent)
- **User Story 3 (P3)**: Can start after Foundational phase - Config management (independent)

### Within User Story 1

1. URLconf creation (T033, T041, T048, T064, T068) must complete first
2. View migrations can run in parallel within each app
3. Template migration (T077-T080) should be done after views are migrated
4. Final homepage integration (T081-T082) after all apps are complete

---

## Parallel Opportunities

### Phase 1 (Setup)

```
T004, T005, T006, T007, T008, T009, T010 - All app creation in parallel
```

### Phase 2 (Foundational)

```
T012, T013, T014, T015 - Settings configuration in parallel
T019, T020, T021 - Utility migration in parallel
T024, T025 - Device models in parallel
T027, T028, T029 - Audit models in parallel
```

### Phase 3 (User Story 1)

```
Labels app views: T034, T035, T036, T037, T038 - All in parallel
Devices app views: T042, T043, T044, T045, T046 - All in parallel
Audit app views: T049-T060 - All in parallel
Students app views: T065, T066 - In parallel
Assets app views: T069-T075 - All in parallel
```

### Phase 4 (User Story 2)

```
T084-T090 - All admin registrations in parallel
T091-T094 - ORM refactoring per app in parallel
T096, T097 - Management commands in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T032)
3. Complete Phase 3: User Story 1 (T033-T082)
4. **STOP and VALIDATE**: Test all routes work identically to Flask
5. Deploy/demo if ready - Django is now functional

### Incremental Delivery

1. Setup + Foundational → Django server starts
2. User Story 1 → All Flask functionality migrated → **MVP Complete**
3. User Story 2 → Django admin + ORM → Enhanced developer experience
4. User Story 3 → Environment config → Production-ready settings
5. Polish → Documentation, cleanup → Migration complete

---

## Notes

- All [P] tasks can run in parallel with other [P] tasks in the same phase
- View migrations are independent per file
- Template migration should happen after corresponding views
- Keep Flask code until Django version is fully verified
- Run `python manage.py runserver 0.0.0.0:8000` to test after each checkpoint
- **Database**: New databases created by Django; no Flask data migration
- Total tasks: 119 (T001-T119)
- Phase 1 (Setup): 10 tasks (T001-T010)
- Phase 2 (Foundational): 22 tasks (T011-T032)
- Phase 3 (User Story 1): 50 tasks (T033-T082)
- Phase 4 (User Story 2): 15 tasks (T083-T097)
- Phase 5 (User Story 3): 9 tasks (T098-T106)
- Phase 6 (Polish): 13 tasks (T107-T119)
