# Research: LDAP/Active Directory Authentication

**Feature**: 006-ldap-auth  
**Date**: 2025-12-03  
**Purpose**: Resolve technical unknowns before implementation

## Research Questions

### RQ1: Python LDAP Library Selection

**Question**: Which Python library should be used for LDAPS connectivity with Active Directory?

**Research**:
- `python-ldap` - Most mature, C-based bindings to OpenLDAP. Requires system libldap.
- `ldap3` - Pure Python, no system dependencies, actively maintained, easier to install on NixOS.

**Decision**: Use `ldap3`

**Rationale**: 
- Pure Python implementation works seamlessly with NixOS without requiring system library compilation
- Excellent Active Directory support with built-in AD-specific features
- Supports LDAPS (SSL/TLS) natively
- Modern API with connection pooling support
- Actively maintained with good documentation

**Alternatives considered**:
- `python-ldap`: Rejected due to C extension compilation requirements on NixOS

### RQ2: LDAPS Connection Pattern

**Question**: How to establish secure LDAP connection with certificate validation?

**Research**:
```python
from ldap3 import Server, Connection, ALL, Tls
import ssl

# Option 1: Full certificate validation (production)
tls = Tls(validate=ssl.CERT_REQUIRED, ca_certs_file='/path/to/ca-bundle.crt')
server = Server('ldaps://dc.domain.com:636', use_ssl=True, tls=tls, get_info=ALL)

# Option 2: Skip validation (development/testing only)
tls = Tls(validate=ssl.CERT_NONE)
server = Server('ldaps://dc.domain.com:636', use_ssl=True, tls=tls, get_info=ALL)
```

**Decision**: Support both modes via environment variable `LDAP_VERIFY_CERT`

**Rationale**: 
- Production requires certificate validation for security
- Development environments may not have proper CA certificates
- Configuration-driven approach maintains security while allowing flexibility

### RQ3: AD Group Membership Query

**Question**: How to query Active Directory group membership for a user?

**Research**:
```python
# Method 1: Query user's memberOf attribute
search_filter = f'(sAMAccountName={username})'
attributes = ['memberOf', 'displayName', 'mail']
conn.search(base_dn, search_filter, attributes=attributes)
# memberOf returns list of group DNs

# Method 2: Query group's member attribute (reverse lookup)
group_dn = 'CN=tech-team,OU=Groups,DC=domain,DC=com'
search_filter = f'(&(objectClass=group)(cn=tech-team))'
attributes = ['member']
```

**Decision**: Use Method 1 (query user's memberOf attribute)

**Rationale**:
- Single query retrieves all groups user belongs to
- Can check both "tech-team" and "TEACHERS" in one call
- More efficient than querying each group separately
- Works with nested group membership via AD's tokenGroups attribute if needed

### RQ4: Django Session Backend for Infinite Sessions

**Question**: How to configure Django for sessions that never expire?

**Research**:
```python
# settings.py
SESSION_COOKIE_AGE = None  # Django doesn't support None directly
# Alternative: Set very large value
SESSION_COOKIE_AGE = 60 * 60 * 24 * 365 * 10  # 10 years in seconds

# Or use database sessions with no expiry
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

**Decision**: Use `SESSION_COOKIE_AGE = 31536000 * 10` (10 years) with database sessions

**Rationale**:
- Django's session framework doesn't support true "infinite" sessions
- 10-year expiration is effectively infinite for this use case
- Database sessions allow server-side session management (admin can invalidate)
- Browser close should NOT end session (per spec requirement)

### RQ5: Role-Based Access Middleware Pattern

**Question**: How to implement role-based access control with LDAP groups?

**Research**:
```python
class LDAPAuthenticationMiddleware:
    def __call__(self, request):
        # Skip public paths
        if self._is_public_path(request.path):
            return self.get_response(request)
        
        # Check session for authenticated user
        if not request.session.get('ldap_user'):
            return redirect('authentication:login')
        
        # Check role access
        user_role = request.session.get('user_role')
        if not self._has_access(request.path, user_role):
            return render(request, '403.html', status=403)
        
        return self.get_response(request)
```

**Decision**: Single middleware handling both authentication and authorization

**Rationale**:
- Simpler than separate auth/authz middleware
- Session already contains role information from login
- Path-based access rules match existing `ROLE_ACCESS_RULES` pattern in settings

### RQ6: AD Connection Bind Credentials

**Question**: How should the system bind to AD for authentication?

**Research**:
- **Anonymous bind**: Not supported by most AD configurations
- **User bind**: Authenticate as the user attempting login (simple bind)
- **Service account bind**: Use dedicated service account for searches

**Decision**: Two-phase authentication:
1. Bind as user with provided credentials (validates password)
2. Query user attributes and group membership while bound

**Rationale**:
- No service account required (simpler deployment)
- User's own credentials used for both auth and group query
- Standard pattern for AD authentication
- Service account can be added later if needed for advanced scenarios

### RQ7: NixOS python-ldap3 Packaging

**Question**: Is ldap3 available in nixpkgs?

**Research**:
```bash
nix search nixpkgs ldap3
# python311Packages.ldap3 - available in nixpkgs
```

**Decision**: Add `ldap3` to `pyproject.toml` dependencies

**Rationale**:
- Available in nixpkgs as `python311Packages.ldap3`
- Pure Python - no additional system dependencies
- Will be installed automatically via devenv.nix

## Summary of Decisions

| Question | Decision | Key Reason |
|----------|----------|------------|
| LDAP library | `ldap3` | Pure Python, NixOS compatible |
| Connection security | LDAPS with configurable cert validation | Security + flexibility |
| Group query | User's memberOf attribute | Single efficient query |
| Session duration | 10-year cookie + database backend | Effectively infinite |
| Middleware pattern | Single combined auth/authz | Simpler, session-based |
| AD binding | User bind (no service account) | Simpler deployment |
| NixOS packaging | `ldap3` in pyproject.toml | Available in nixpkgs |

## Environment Variables Required

```bash
# Required
LDAP_SERVER=ldaps://dc.westerncusd12.org:636
LDAP_BASE_DN=DC=westerncusd12,DC=org
LDAP_TECH_GROUP=tech-team
LDAP_TEACHER_GROUP=TEACHERS

# Optional
LDAP_VERIFY_CERT=true  # Default: true
LDAP_CA_CERT_FILE=/etc/ssl/certs/ca-certificates.crt  # Default: system CA bundle
LDAP_TIMEOUT=10  # Default: 10 seconds
```
