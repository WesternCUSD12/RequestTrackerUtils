# Implementation Plan: LDAP/Active Directory Authentication

**Branch**: `006-ldap-auth` | **Date**: 2025-12-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-ldap-auth/spec.md`

## Summary

Replace HTTP Basic Auth with LDAP/Active Directory authentication for RTUtils. The system will authenticate users via LDAPS (port 636) against the domain controller, query group membership for "tech-team" (full access) and "TEACHERS" (student audit only), and maintain infinite sessions with role-based access control.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Django 4.2 LTS, ldap3 (pure Python LDAPS connectivity)  
**Storage**: SQLite3 (existing), Django session backend  
**Testing**: pytest with pytest-django  
**Target Platform**: NixOS (Linux server)  
**Project Type**: Web application (Django)  
**Performance Goals**: Login in under 5 seconds (spec SC-001)  
**Constraints**: LDAPS required (port 636), infinite sessions  
**Scale/Scope**: Internal tool, ~20 users (tech staff + teachers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Documentation-First | ✅ PASS | spec.md created with user stories, acceptance criteria, success metrics |
| II. Modular Routing Architecture | ✅ PASS | Will modify existing `apps/authentication` app (already registered) |
| III. Specification-Driven Testing | ✅ PASS | Three independently testable user stories (P1: tech-team, P2: teacher, P3: unauthorized) |
| IV. Request Tracker API Integration | N/A | No RT API changes required |
| V. Configuration & Environment Management | ✅ PASS | LDAP settings via environment variables (FR-012) |
| Authentication Requirements | ✅ PASS | `/labels/*` remains public, other routes protected per constitution |

**Pre-Design Gate**: ✅ PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/006-ldap-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts needed)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
apps/
├── authentication/          # MODIFY - Replace OAuth2 with LDAP
│   ├── __init__.py
│   ├── admin.py            # MODIFY - User admin with role display
│   ├── apps.py
│   ├── ldap_client.py      # NEW - LDAPS connection and group query
│   ├── middleware.py       # MODIFY - Replace OAuth2 middleware with LDAP session check
│   ├── models.py           # MODIFY - User role management
│   ├── urls.py             # MODIFY - Login/logout routes
│   ├── views.py            # MODIFY - LDAP login form handling
│   └── templates/
│       └── auth/
│           ├── login.html  # MODIFY - Username/password form
│           └── error.html  # KEEP - Error display
│
├── audit/                   # NO CHANGE - Teacher access target
│
common/
├── middleware.py            # MODIFY - Remove BasicAuth, integrate with LDAP auth

rtutils/
├── settings.py              # MODIFY - LDAP config, remove OAuth2 config

tests/
├── unit/
│   └── test_ldap_client.py  # NEW - LDAP client unit tests
└── integration/
    └── test_ldap_auth.py    # NEW - Authentication flow integration tests
```

**Structure Decision**: Modify existing `apps/authentication` app to replace OAuth2 with LDAP. No new apps needed - authentication is already a registered Django app with the appropriate structure.

## Complexity Tracking

> No constitution violations - using existing app structure
