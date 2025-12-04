# Feature Specification: LDAP/Active Directory Authentication

**Feature Branch**: `006-ldap-auth`  
**Created**: 2025-12-03  
**Status**: Draft  
**Input**: User description: "RTUtils should use ldap (active directory) for user authentication. The system should pull two groups, TEACHERS and tech-team. tech-team has access to all features. TEACHERS only has access to the student device audit feature"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tech Team Full Access Login (Priority: P1)

A technology staff member needs to sign into RTUtils using their Active Directory credentials to access all system features including device management, label printing, asset creation, and student device audits.

**Why this priority**: Technology staff are the primary users of all RTUtils features. Without their ability to log in and access full functionality, the system provides no value. This is the core authentication flow.

**Independent Test**: Attempt to sign in with valid tech-team AD credentials, verify successful login, verify access to all features (device management, labels, assets, student audit, Django admin). Verify that session persists across page navigation.

**Acceptance Scenarios**:

1. **Given** a user is a member of the "tech-team" AD group, **When** they enter valid AD credentials on the login page, **Then** they are authenticated and redirected to the home page with full feature access
2. **Given** a tech-team user is logged in, **When** they navigate to any feature (devices, labels, assets, student audit), **Then** they can access and use the feature without restriction
3. **Given** a tech-team user is logged in, **When** they close the browser and return later (within session timeout), **Then** their session remains valid and they don't need to re-authenticate

---

### User Story 2 - Teacher Limited Access Login (Priority: P2)

A teacher needs to sign into RTUtils using their Active Directory credentials to access the student device audit feature for verifying student device assignments in their classroom.

**Why this priority**: Teachers are a secondary user group with restricted access. Their use case is important but more limited in scope. This story depends on the core authentication infrastructure from US1.

**Independent Test**: Attempt to sign in with valid TEACHERS group AD credentials, verify successful login, verify access ONLY to student device audit feature, verify access denial to other features.

**Acceptance Scenarios**:

1. **Given** a user is a member of the "TEACHERS" AD group, **When** they enter valid AD credentials on the login page, **Then** they are authenticated and redirected to the student device audit page
2. **Given** a teacher user is logged in, **When** they attempt to access device management, labels, or asset features, **Then** they see an "Access Denied" message explaining their role has limited access
3. **Given** a teacher user is logged in, **When** they navigate to the student device audit feature, **Then** they can fully use the audit functionality

---

### User Story 3 - Unauthorized User Rejection (Priority: P3)

A user who has valid AD credentials but is not a member of either "tech-team" or "TEACHERS" groups should be denied access to the system with a clear error message.

**Why this priority**: Security boundary enforcement is essential but depends on the core authentication flow. This ensures only authorized personnel can access the system.

**Independent Test**: Attempt to sign in with valid AD credentials for a user not in either authorized group, verify access is denied with appropriate message.

**Acceptance Scenarios**:

1. **Given** a user has valid AD credentials but is NOT in "tech-team" or "TEACHERS" groups, **When** they attempt to log in, **Then** they see an error message stating they are not authorized to access this application
2. **Given** a user provides invalid AD credentials, **When** they attempt to log in, **Then** they see an error message about invalid credentials (distinct from authorization failure)

---

### Edge Cases

- What happens when the LDAP/AD server is unreachable? System displays "Authentication service unavailable" error and logs the connection failure
- What happens when a user is in BOTH tech-team and TEACHERS groups? User receives the higher privilege level (tech-team full access)
- What happens when a user's group membership changes after login? Access is re-evaluated on next login; current session maintains original permissions
- How does system handle AD accounts that are disabled or locked? Authentication fails with appropriate error message
- What happens when user explicitly logs out? Session is terminated and user must re-authenticate to access the system

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate users against Active Directory using LDAPS (LDAP over SSL/TLS, port 636) for encrypted credential transmission
- **FR-002**: System MUST query AD group membership for "tech-team" and "TEACHERS" groups during authentication
- **FR-003**: System MUST grant full feature access (including Django admin interface) to users who are members of the "tech-team" AD group
- **FR-004**: System MUST restrict users who are members of the "TEACHERS" AD group to only the student device audit feature
- **FR-005**: System MUST deny access to users who are not members of either authorized AD group
- **FR-006**: System MUST display appropriate error messages distinguishing between invalid credentials, unauthorized access, and service unavailability
- **FR-007**: System MUST maintain authenticated sessions to avoid repeated login prompts during normal usage
- **FR-008**: System MUST provide a logout function that terminates the user session
- **FR-009**: System MUST log all authentication attempts (success and failure) with timestamp and username
- **FR-010**: System MUST redirect unauthenticated users to the login page when accessing protected routes
- **FR-011**: System MUST display the current user's identity and role in the navigation interface
- **FR-012**: System MUST allow configuration of LDAP server connection details (server address, base DN, bind credentials) via environment variables
- **FR-013**: System MUST handle disabled or locked AD accounts with appropriate error message distinct from invalid credentials

### Assumptions

- Active Directory server is accessible from the RTUtils deployment environment
- AD groups "tech-team" and "TEACHERS" already exist and are properly maintained
- Users have unique usernames (sAMAccountName) in Active Directory
- Sessions are infinite (never expire); users remain logged in until explicit logout

### Key Entities

- **User Session**: Represents an authenticated user's session; includes username, display name, email, group membership (role), login timestamp
- **User Role**: Derived from AD group membership; either "technology_staff" (from tech-team) or "teacher" (from TEACHERS); determines feature access
- **Authentication Event**: Audit log entry; includes timestamp, username, event type (login/logout/failure), IP address, failure reason (if applicable)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the login process in under 5 seconds (from credential entry to home page display)
- **SC-002**: 100% of tech-team members can access all system features after authentication
- **SC-003**: 100% of TEACHERS members are correctly restricted to only the student device audit feature
- **SC-004**: 100% of unauthorized users (not in either group) are denied access with clear messaging
- **SC-005**: System correctly handles AD server unavailability without crashing or exposing sensitive information
- **SC-006**: All authentication events (success, failure, logout) are logged for audit purposes
- **SC-007**: Existing Basic Auth is fully replaced - no dual authentication systems remain

## Clarifications

### Session 2025-12-03

- Q: What should the session timeout duration be? → A: Infinite sessions (never expire, only explicit logout)
- Q: Should LDAP connections use encryption? → A: LDAPS required (port 636, encrypted)
