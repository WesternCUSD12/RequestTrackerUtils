# Tasks: LDAP/Active Directory Authentication

**Input**: Design documents from `/specs/006-ldap-auth/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: Not explicitly requested in specification - test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- `apps/authentication/` - LDAP authentication module
- `rtutils/settings.py` - Django settings
- `common/middleware.py` - Shared middleware
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests

---

## Phase 1: Setup

**Purpose**: Project dependencies and configuration scaffolding

- [X] T001 Add `ldap3>=2.9.0` dependency to pyproject.toml
- [X] T002 [P] Add LDAP environment variables to rtutils/settings.py (LDAP_SERVER, LDAP_BASE_DN, LDAP_TECH_GROUP, LDAP_TEACHER_GROUP, LDAP_VERIFY_CERT, LDAP_CA_CERT_FILE, LDAP_TIMEOUT)
- [X] T003 [P] Remove OAuth2 configuration from rtutils/settings.py (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, ALLOWED_OAUTH_DOMAINS)
- [X] T004 Configure Django session backend for infinite sessions in rtutils/settings.py (SESSION_COOKIE_AGE=31536000*10, SESSION_ENGINE='django.contrib.sessions.backends.db')

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core LDAP infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create LDAP client module at apps/authentication/ldap_client.py with LDAPClient class
- [X] T006 Implement LDAPS connection method in apps/authentication/ldap_client.py (connect with TLS, configurable cert validation)
- [X] T007 Implement user authentication method in apps/authentication/ldap_client.py (bind as user, validate credentials)
- [X] T008 Implement group membership query in apps/authentication/ldap_client.py (query memberOf attribute, return list of groups)
- [X] T009 Implement role resolution logic in apps/authentication/ldap_client.py (tech-team → technology_staff, TEACHERS → teacher, both → technology_staff)
- [X] T010 Create login template at apps/authentication/templates/auth/login.html (username/password form, CSRF, error display, next parameter)
- [X] T011 [P] Create 403 forbidden template at apps/authentication/templates/auth/403.html (access denied message with role explanation)
- [X] T012 Remove OAuth2 middleware from apps/authentication/middleware.py (delete OAuth2AuthenticationMiddleware class)
- [X] T013 Remove OAuth2 routes from apps/authentication/urls.py (delete callback and oauth-related URL patterns)
- [X] T014 Delete OAuth2 module at apps/authentication/oauth2.py

**Checkpoint**: LDAP client ready, templates ready, OAuth2 removed - user story implementation can now begin

---

## Phase 3: User Story 1 - Tech Team Full Access Login (Priority: P1) 🎯 MVP

**Goal**: Technology staff can authenticate with AD credentials and access all system features

**Independent Test**: Login with tech-team member credentials, verify access to all routes (/, /devices/, /assets/, /students/, /audit/)

### Implementation for User Story 1

- [X] T015 [US1] Implement login view GET handler in apps/authentication/views.py (render login form, redirect if already authenticated)
- [X] T016 [US1] Implement login view POST handler in apps/authentication/views.py (validate credentials via LDAPClient, create session on success)
- [X] T017 [US1] Store session data on successful login in apps/authentication/views.py (ldap_user, display_name, email, user_role, groups, login_timestamp)
- [X] T018 [US1] Implement logout view in apps/authentication/views.py (clear session, redirect to login)
- [X] T019 [US1] Update URL patterns in apps/authentication/urls.py (add /auth/login and /auth/logout routes)
- [X] T020 [US1] Create LDAPAuthenticationMiddleware in apps/authentication/middleware.py (check session for ldap_user, redirect unauthenticated to login)
- [X] T021 [US1] Configure public paths in middleware (allow /auth/*, /labels/*, /static/* without authentication)
- [X] T022 [US1] Update MIDDLEWARE in rtutils/settings.py (replace OAuth2AuthenticationMiddleware with LDAPAuthenticationMiddleware)
- [X] T023 [US1] Remove SelectiveBasicAuthMiddleware from common/middleware.py
- [X] T024 [US1] Add authentication logging in apps/authentication/views.py (log login_success, login_failure, logout events with timestamp, username, IP)
- [X] T025 [US1] Display current user and role in navigation - update templates/base.html (show username, role, logout link)

**Checkpoint**: Tech team members can login with AD credentials, access all features, and logout. Session persists across browser sessions.

---

## Phase 4: User Story 2 - Teacher Limited Access Login (Priority: P2)

**Goal**: Teachers can authenticate with AD credentials and access only the student device audit feature

**Independent Test**: Login with TEACHERS group member credentials, verify access to /audit/*, verify 403 on /devices/, /students/, /assets/

### Implementation for User Story 2

- [X] T026 [US2] Add role-based access check in LDAPAuthenticationMiddleware in apps/authentication/middleware.py (check user_role against route)
- [X] T027 [US2] Define ROLE_ACCESS_RULES in rtutils/settings.py (technology_staff: all routes, teacher: /audit/* only)
- [X] T028 [US2] Implement role redirect on login in apps/authentication/views.py (teacher → /audit/, technology_staff → /)
- [X] T029 [US2] Return 403 response with template for unauthorized route access in apps/authentication/middleware.py

**Checkpoint**: Teachers can login, access audit feature only, and see 403 on restricted routes. Tech team access unchanged.

---

## Phase 5: User Story 3 - Unauthorized User Rejection (Priority: P3)

**Goal**: Users not in authorized AD groups are denied access with clear messaging

**Independent Test**: Login with valid AD credentials for user NOT in tech-team or TEACHERS, verify error message displayed

### Implementation for User Story 3

- [X] T030 [US3] Add group validation in login POST handler in apps/authentication/views.py (check user is in tech-team OR TEACHERS)
- [X] T031 [US3] Display "Not authorized to access this application" error on login page for unauthorized users in apps/authentication/views.py
- [X] T032 [US3] Distinguish error messages in login template (invalid credentials vs unauthorized vs service unavailable) in apps/authentication/templates/auth/login.html
- [X] T033 [US3] Log access_denied events for unauthorized users in apps/authentication/views.py

**Checkpoint**: Unauthorized users see clear error message, cannot access system. Error messages are distinct and helpful.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, cleanup, and documentation

- [X] T034 [P] Handle LDAP connection failures gracefully in apps/authentication/ldap_client.py (catch exceptions, return service unavailable)
- [X] T035 [P] Handle AD account disabled/locked in apps/authentication/ldap_client.py (parse error response, return appropriate message per FR-013)
- [X] T036 Add connection timeout handling in apps/authentication/ldap_client.py (use LDAP_TIMEOUT setting)
- [X] T037 [P] Remove AUTH_USERNAME and AUTH_PASSWORD environment variable references from rtutils/settings.py
- [X] T038 [P] Update README.md with LDAP configuration instructions
- [ ] T039 Run quickstart.md validation (manual test all login scenarios)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories should proceed sequentially: US1 → US2 → US3
  - US2 and US3 build on US1's authentication flow
- **Polish (Phase 6)**: Can start after US1 complete, finish after all stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core authentication flow
- **User Story 2 (P2)**: Depends on US1 completion - Adds role-based access control to existing flow
- **User Story 3 (P3)**: Depends on US1 completion - Adds group validation to existing flow

### Within Each Phase

- T001-T004 (Setup): T001 first, then T002-T004 in parallel
- T005-T014 (Foundational): T005-T009 sequential (LDAP client), T010-T011 parallel (templates), T012-T014 parallel (OAuth2 removal)
- T015-T025 (US1): Sequential flow building authentication
- T026-T029 (US2): Sequential flow adding role checks
- T030-T033 (US3): Sequential flow adding group validation
- T034-T039 (Polish): T034-T035 parallel, T037-T38 parallel

### Parallel Opportunities

Within Foundational phase:
- T010 and T011 (templates) can run in parallel
- T012, T013, T014 (OAuth2 removal) can run in parallel

Within Polish phase:
- T034 and T035 (error handling) can run in parallel
- T037 and T038 (cleanup and docs) can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# After T005-T009 (LDAP client) complete:

# Launch template creation in parallel:
Task T010: "Create login template at apps/authentication/templates/auth/login.html"
Task T011: "Create 403 forbidden template at apps/authentication/templates/auth/403.html"

# Launch OAuth2 removal in parallel:
Task T012: "Remove OAuth2 middleware from apps/authentication/middleware.py"
Task T013: "Remove OAuth2 routes from apps/authentication/urls.py"
Task T014: "Delete OAuth2 module at apps/authentication/oauth2.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T014)
3. Complete Phase 3: User Story 1 (T015-T025)
4. **STOP and VALIDATE**: Test tech-team login, full access, logout
5. Deploy/demo if ready - basic LDAP auth working!

### Incremental Delivery

1. Setup + Foundational → LDAP infrastructure ready
2. Add User Story 1 → **MVP: Tech team can authenticate**
3. Add User Story 2 → Teachers get restricted access
4. Add User Story 3 → Unauthorized users rejected with clear messages
5. Polish → Error handling, cleanup, documentation

### File Change Summary

| File | Action | Phase |
|------|--------|-------|
| pyproject.toml | ADD ldap3 dependency | Setup |
| rtutils/settings.py | MODIFY (LDAP config, remove OAuth2, session config) | Setup, US1 |
| apps/authentication/ldap_client.py | NEW | Foundational |
| apps/authentication/middleware.py | MODIFY (replace OAuth2 with LDAP) | Foundational, US1, US2 |
| apps/authentication/views.py | MODIFY (login/logout views) | US1, US2, US3 |
| apps/authentication/urls.py | MODIFY (login/logout routes) | Foundational, US1 |
| apps/authentication/oauth2.py | DELETE | Foundational |
| apps/authentication/templates/auth/login.html | NEW | Foundational, US3 |
| apps/authentication/templates/auth/403.html | NEW | Foundational |
| common/middleware.py | MODIFY (remove BasicAuth) | US1 |
| templates/base.html | MODIFY (user display) | US1 |
| README.md | MODIFY (LDAP docs) | Polish |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story checkpoint validates independently testable functionality
- Commit after each task or logical group
- LDAP_VERIFY_CERT=false for development, true for production
- Test with actual AD credentials before considering story complete
