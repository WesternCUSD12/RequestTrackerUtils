# Authentication API Contract

**Feature**: 006-ldap-auth  
**Version**: 1.0.0  
**Date**: 2025-12-03

## Overview

This document defines the HTTP API contract for LDAP/Active Directory authentication endpoints.

## Endpoints

### POST /auth/login

Authenticate user against Active Directory via LDAPS.

#### Request

**Content-Type**: `application/x-www-form-urlencoded`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | AD sAMAccountName |
| password | string | Yes | AD password |
| next | string | No | URL to redirect after login |

#### Response

**Success (302 Found)**
- Redirects to `next` parameter or role-appropriate default:
  - `technology_staff` → `/` (home)
  - `teacher` → `/audit/`
- Sets session cookie

**Failure (200 OK)**
- Re-renders login form with error message
- Error messages:
  - "Invalid credentials" - wrong username/password
  - "Not authorized to access this application" - valid user, wrong groups
  - "Authentication service unavailable" - LDAP connection failed

---

### GET /auth/login

Display login form.

#### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| next | string | No | URL to redirect after login |

#### Response

**Success (200 OK)**
- HTML login form
- Includes CSRF token
- Preserves `next` parameter in hidden field

**Already Authenticated (302 Found)**
- Redirects to home page (authenticated users)

---

### POST /auth/logout

Terminate user session.

#### Request

No body required. CSRF token in cookie.

#### Response

**Success (302 Found)**
- Clears session cookie
- Redirects to `/auth/login`

---

### GET /auth/logout

Alternative logout endpoint (convenience).

#### Response

**Success (302 Found)**
- Clears session cookie
- Redirects to `/auth/login`

---

## Session Cookie

| Attribute | Value |
|-----------|-------|
| Name | `sessionid` |
| HttpOnly | Yes |
| Secure | Yes (production) |
| SameSite | Lax |
| Max-Age | None (session cookie) |

## Session Data

Stored server-side in Django session:

```python
{
    "user_dn": "CN=John Doe,OU=Users,DC=westerncusd12,DC=org",
    "username": "jdoe",
    "display_name": "John Doe",
    "role": "technology_staff" | "teacher",
    "groups": ["tech-team"] | ["TEACHERS"],
    "authenticated_at": "2025-12-03T10:30:00Z"
}
```

## Access Control Matrix

| Route Pattern | technology_staff | teacher | Unauthenticated |
|---------------|------------------|---------|-----------------|
| `/auth/*` | ✓ | ✓ | ✓ |
| `/labels/*` | ✓ | ✓ | ✓ (public) |
| `/audit/*` | ✓ | ✓ | → login |
| `/devices/*` | ✓ | 403 | → login |
| `/students/*` | ✓ | 403 | → login |
| `/assets/*` | ✓ | 403 | → login |
| `/*` (other) | ✓ | 403 | → login |

## Error Codes

| HTTP Status | Meaning |
|-------------|---------|
| 200 | Success (or form re-render with error) |
| 302 | Redirect (success or already authenticated) |
| 403 | Forbidden (authenticated but lacks permission) |
| 500 | Server error (LDAP connection failure logged) |
