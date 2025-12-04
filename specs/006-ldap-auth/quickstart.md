# Quickstart: LDAP/Active Directory Authentication

**Feature**: 006-ldap-auth  
**Date**: 2025-12-03

## Prerequisites

1. **Active Directory Environment**
   - AD server accessible via LDAPS (port 636)
   - Two AD groups configured: `tech-team` and `TEACHERS`
   - Users assigned to appropriate groups

2. **Development Environment**
   - Python 3.11+
   - Django 4.2 LTS
   - `ldap3` library installed

## Environment Setup

### Required Environment Variables

```bash
# .env file
LDAP_SERVER=ldaps://dc.westerncusd12.org:636
LDAP_BASE_DN=DC=westerncusd12,DC=org
LDAP_TECH_GROUP=tech-team
LDAP_TEACHER_GROUP=TEACHERS
```

### Optional Environment Variables

```bash
# Certificate validation (default: true)
LDAP_VERIFY_CERT=true

# Custom CA certificate file (default: system CA bundle)
LDAP_CA_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Connection timeout in seconds (default: 10)
LDAP_TIMEOUT=10
```

## Installation

1. **Add dependency to pyproject.toml**:
   ```toml
   dependencies = [
       # ... existing dependencies ...
       "ldap3>=2.9.0",
   ]
   ```

2. **Update devenv.nix** (if using NixOS):
   ```nix
   packages = with pkgs; [
     # ldap3 is pure Python, no extra packages needed
   ];
   ```

3. **Install dependencies**:
   ```bash
   uv sync  # or pip install -e .
   ```

## Usage

### Login Flow

1. Navigate to any protected route (e.g., `/devices/`)
2. Redirected to `/auth/login`
3. Enter AD username and password
4. On success:
   - tech-team users → redirected to home page
   - TEACHERS users → redirected to `/audit/`
5. Session persists until explicit logout

### Logout

1. Click "Sign Out" in navigation bar
2. Or navigate to `/auth/logout`
3. Session terminated, redirected to login page

### Access Control

| Role | Accessible Routes |
|------|-------------------|
| technology_staff | All routes |
| teacher | `/audit/*` only |

## Testing

### Manual Testing

1. **Tech Team Login**:
   ```bash
   # Login with tech-team member credentials
   # Verify access to all routes
   ```

2. **Teacher Login**:
   ```bash
   # Login with TEACHERS member credentials
   # Verify access to /audit/
   # Verify 403 on /devices/, /students/, /assets/
   ```

3. **Unauthorized User**:
   ```bash
   # Login with valid AD credentials (not in either group)
   # Verify "not authorized" error message
   ```

### Automated Testing

```bash
# Run LDAP authentication tests
pytest tests/unit/test_ldap_client.py -v
pytest tests/integration/test_ldap_auth.py -v
```

## Troubleshooting

### "Authentication service unavailable"

- Check LDAP_SERVER is correct and reachable
- Verify port 636 is not blocked by firewall
- Check `auth.log` for detailed error

### "Invalid credentials"

- Verify username is sAMAccountName (not email or UPN)
- Check AD account is not locked/disabled

### "Not authorized to access this application"

- Verify user is member of `tech-team` or `TEACHERS` group
- Check group names match LDAP_TECH_GROUP and LDAP_TEACHER_GROUP

### SSL Certificate Errors

- Set `LDAP_VERIFY_CERT=false` for testing (not recommended for production)
- Or provide correct CA certificate via `LDAP_CA_CERT_FILE`

## Migration from Basic Auth

1. Deploy with LDAP configuration
2. Remove `AUTH_USERNAME` and `AUTH_PASSWORD` from environment
3. Update any external integrations (note: `/labels/*` remains public)
