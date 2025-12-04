# Data Model: LDAP/Active Directory Authentication

**Feature**: 006-ldap-auth  
**Date**: 2025-12-03

## Entities

### User Session (Django Session + Custom Data)

Stored in Django's session framework (database backend).

| Field | Type | Description |
|-------|------|-------------|
| session_key | string | Django session identifier (auto-generated) |
| ldap_user | string | sAMAccountName from AD |
| display_name | string | displayName from AD |
| email | string | mail attribute from AD |
| user_role | string | Derived role: "technology_staff" or "teacher" |
| groups | list[string] | List of AD group CNs user belongs to |
| login_timestamp | datetime | When user authenticated |

**Notes**:
- Session data is stored in `django_session` table
- No custom User model needed - session-based authentication
- Role is derived at login time from group membership

### User Role (Derived from AD Groups)

| AD Group | Internal Role | Access Level |
|----------|---------------|--------------|
| tech-team | technology_staff | Full access to all routes |
| TEACHERS | teacher | Student audit only (`/audit/*`) |
| (neither) | (denied) | Cannot login |

**Role Resolution**:
- User in both groups → `technology_staff` (higher privilege wins)
- User in tech-team only → `technology_staff`
- User in TEACHERS only → `teacher`
- User in neither → Login denied with error message

### Authentication Event (Audit Log)

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When event occurred |
| username | string | sAMAccountName attempted |
| event_type | enum | "login_success", "login_failure", "logout", "access_denied" |
| ip_address | string | Client IP address |
| user_agent | string | Browser/client identification |
| failure_reason | string | Null on success; reason on failure |
| role_assigned | string | Role assigned on successful login; null otherwise |

**Storage**: Log file (`auth.log`) via Python logging framework (already configured in settings.py)

## State Transitions

```
┌─────────────┐
│ Unauthenticated │
└───────┬─────────┘
        │ POST /auth/login (valid creds + authorized group)
        ▼
┌─────────────┐
│ Authenticated  │ ───────────────────────────────────────┐
│ (session active)│                                        │
└───────┬─────────┘                                        │
        │                                                  │
        │ GET /auth/logout                                 │
        │ OR browser clears cookies                        │
        ▼                                                  │
┌─────────────┐                                           │
│ Unauthenticated │ ◄─────────────────────────────────────┘
└─────────────────┘   Login failure / Unauthorized group
```

## Access Control Matrix

| Route Pattern | technology_staff | teacher | Unauthenticated |
|---------------|------------------|---------|-----------------|
| `/labels/*` | ✅ | ✅ | ✅ (public) |
| `/static/*` | ✅ | ✅ | ✅ (public) |
| `/auth/login` | ✅ | ✅ | ✅ (public) |
| `/auth/logout` | ✅ | ✅ | ❌ (redirect to login) |
| `/audit/*` | ✅ | ✅ | ❌ (redirect to login) |
| `/devices/*` | ✅ | ❌ (403) | ❌ (redirect to login) |
| `/students/*` | ✅ | ❌ (403) | ❌ (redirect to login) |
| `/assets/*` | ✅ | ❌ (403) | ❌ (redirect to login) |
| `/admin/*` | ✅ | ❌ (403) | ❌ (redirect to login) |
| `/` (home) | ✅ | ❌ (403) | ❌ (redirect to login) |

## Configuration Schema

### Environment Variables

```python
# rtutils/settings.py additions

# LDAP Server Configuration
LDAP_SERVER = os.environ.get('LDAP_SERVER')  # Required: ldaps://dc.domain.com:636
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')  # Required: DC=domain,DC=com
LDAP_TECH_GROUP = os.environ.get('LDAP_TECH_GROUP', 'tech-team')
LDAP_TEACHER_GROUP = os.environ.get('LDAP_TEACHER_GROUP', 'TEACHERS')

# Optional LDAP Settings
LDAP_VERIFY_CERT = os.environ.get('LDAP_VERIFY_CERT', 'true').lower() == 'true'
LDAP_CA_CERT_FILE = os.environ.get('LDAP_CA_CERT_FILE')  # None = system default
LDAP_TIMEOUT = int(os.environ.get('LDAP_TIMEOUT', '10'))

# Fail-fast validation
if not LDAP_SERVER or not LDAP_BASE_DN:
    raise ValueError("LDAP_SERVER and LDAP_BASE_DN environment variables are required")
```

### Settings to Remove (OAuth2)

```python
# Remove these from settings.py
GOOGLE_OAUTH_CLIENT_ID  # DELETE
GOOGLE_OAUTH_CLIENT_SECRET  # DELETE
ALLOWED_OAUTH_DOMAINS  # DELETE
```

## Database Changes

**No schema migrations required.**

- Using Django's built-in session table (`django_session`)
- Authentication events logged to file, not database
- No custom User model - session stores all needed data
