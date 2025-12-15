"""
LDAP/Active Directory authentication client.

Feature: 006-ldap-auth
Provides LDAPS connectivity, user authentication, and group membership queries.
"""

import logging
import ssl
from typing import Optional, List, Tuple

from ldap3 import Server, Connection, Tls, ALL, SIMPLE
from ldap3.core.exceptions import (
    LDAPException,
    LDAPBindError,
    LDAPInvalidCredentialsResult,
)
from django.conf import settings


logger = logging.getLogger("auth")


class LDAPAuthenticationError(Exception):
    """Base exception for LDAP authentication errors."""

    pass


class LDAPServiceUnavailableError(LDAPAuthenticationError):
    """Raised when LDAP server is unreachable."""

    pass


class LDAPInvalidCredentialsError(LDAPAuthenticationError):
    """Raised when user credentials are invalid."""

    pass


class LDAPAccountDisabledError(LDAPAuthenticationError):
    """Raised when user account is disabled or locked."""

    pass


class LDAPClient:
    """
    LDAP/Active Directory client for authentication and group queries.

    Uses LDAPS (LDAP over SSL/TLS) on port 636 for encrypted communication.
    Supports configurable certificate validation and connection timeouts.
    """

    def __init__(self):
        """Initialize LDAP client with settings from Django configuration."""
        self.server_uri = settings.LDAP_SERVER
        self.base_dn = settings.LDAP_BASE_DN
        self.upn_suffix = settings.LDAP_UPN_SUFFIX
        self.tech_group = settings.LDAP_TECH_GROUP
        self.teacher_groups = getattr(settings, "LDAP_TEACHER_GROUPS", ["TEACHERS"])
        self.verify_cert = settings.LDAP_VERIFY_CERT
        self.ca_cert_file = settings.LDAP_CA_CERT_FILE
        self.timeout = settings.LDAP_TIMEOUT

    def _create_tls_config(self) -> Tls:
        """
        Create TLS configuration for LDAPS connection.

        Returns:
            Tls: ldap3 TLS configuration object
        """
        validation = ssl.CERT_REQUIRED if self.verify_cert else ssl.CERT_NONE

        tls_kwargs = {"validate": validation}
        if self.ca_cert_file:
            tls_kwargs["ca_certs_file"] = self.ca_cert_file

        return Tls(**tls_kwargs)

    def _connect(self, username: str, password: str) -> Connection:
        """
        Establish LDAPS connection and bind as user.

        Args:
            username: sAMAccountName (not email or UPN)
            password: User's AD password

        Returns:
            Connection: Bound LDAP connection

        Raises:
            LDAPServiceUnavailableError: Server unreachable or connection timeout
            LDAPInvalidCredentialsError: Invalid username/password
            LDAPAccountDisabledError: Account is disabled or locked
        """
        try:
            tls = self._create_tls_config()
            server = Server(
                self.server_uri,
                use_ssl=True,
                tls=tls,
                get_info=ALL,
                connect_timeout=self.timeout,
            )

            # Try multiple bind formats for AD compatibility
            # Extract domain from base DN (e.g., QNSK12 from DC=QNSK12,DC=EDU)
            domain_parts = [
                part.split("=")[1]
                for part in self.base_dn.split(",")
                if part.strip().startswith("DC=")
            ]
            domain_name = domain_parts[0] if domain_parts else None
            upn_domain = ".".join(domain_parts) if domain_parts else None

            # Try different bind formats in order of preference
            bind_formats = []
            # Prefer explicit UPN suffix if configured (e.g., westerncusd12.org)
            if self.upn_suffix:
                bind_formats.append(f"{username}@{self.upn_suffix}")
            # Try UPN from DN (e.g., jmartin@QNSK12.EDU)
            if upn_domain and upn_domain != self.upn_suffix:
                bind_formats.append(f"{username}@{upn_domain}")
            # Try NT4 format (e.g., QNSK12\jmartin)
            if domain_name:
                bind_formats.append(f"{domain_name}\\{username}")

            last_error = None
            for user_dn in bind_formats:
                try:
                    conn = Connection(
                        server,
                        user=user_dn,
                        password=password,
                        authentication=SIMPLE,
                        auto_bind=True,
                        receive_timeout=self.timeout,
                    )
                    logger.info(
                        f"LDAP connection established for user: {username} using format: {user_dn}"
                    )
                    return conn
                except (LDAPBindError, LDAPInvalidCredentialsResult) as e:
                    last_error = e
                    logger.debug(f"Bind failed with format {user_dn}: {e}")
                    continue

            # If all formats failed, raise the last error
            if last_error:
                raise last_error

        except LDAPInvalidCredentialsResult as e:
            logger.warning(f"Invalid credentials for user: {username}")
            raise LDAPInvalidCredentialsError("Invalid username or password") from e

        except LDAPBindError as e:
            error_message = str(e).lower()

            # Detect disabled/locked accounts from AD error messages
            if any(
                keyword in error_message
                for keyword in ["disabled", "locked", "expired", "must change password"]
            ):
                logger.warning(f"Account issue for user {username}: {error_message}")
                raise LDAPAccountDisabledError(
                    "Account is disabled, locked, or requires password change"
                ) from e

            logger.warning(f"LDAP bind error for user {username}: {e}")
            raise LDAPInvalidCredentialsError("Authentication failed") from e

        except (LDAPException, OSError, TimeoutError) as e:
            logger.error(f"LDAP service unavailable: {e}")
            raise LDAPServiceUnavailableError(
                "Authentication service unavailable"
            ) from e

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[dict]]:
        """
        Authenticate user and retrieve user information.

        Args:
            username: sAMAccountName
            password: User's AD password

        Returns:
            Tuple[bool, Optional[dict]]: (success, user_info)
            user_info contains: dn, username, display_name, email, groups

        Raises:
            LDAPServiceUnavailableError: Server unreachable
            LDAPInvalidCredentialsError: Invalid credentials
            LDAPAccountDisabledError: Account disabled/locked
        """
        conn = self._connect(username, password)

        try:
            # Query user attributes and group membership
            search_filter = f"(sAMAccountName={username})"
            conn.search(
                search_base=self.base_dn,
                search_filter=search_filter,
                attributes=["distinguishedName", "displayName", "mail", "memberOf"],
            )

            if not conn.entries:
                logger.warning(f"User not found in directory: {username}")
                raise LDAPInvalidCredentialsError("User not found")

            entry = conn.entries[0]

            # Extract user attributes
            user_dn = str(entry.distinguishedName)
            display_name = str(entry.displayName) if entry.displayName else username
            email = str(entry.mail) if entry.mail else None

            # Extract group CNs from memberOf DNs
            groups = []
            if entry.memberOf:
                for group_dn in entry.memberOf:
                    # Parse CN from DN: "CN=tech-team,OU=Groups,DC=domain,DC=com" -> "tech-team"
                    cn_part = str(group_dn).split(",")[0]
                    if cn_part.startswith("CN="):
                        groups.append(cn_part[3:])

            user_info = {
                "dn": user_dn,
                "username": username,
                "display_name": display_name,
                "email": email,
                "groups": groups,
            }

            logger.info(
                f"Authentication successful for user: {username} (groups: {groups})"
            )
            return True, user_info

        finally:
            conn.unbind()

    def get_user_role(self, groups: List[str]) -> Optional[str]:
        """
        Determine user role from AD group membership.

        Args:
            groups: List of AD group CNs user belongs to

        Returns:
            Optional[str]: 'technology_staff', 'teacher', or None

        Rules:
            - tech-team membership -> technology_staff (highest privilege)
            - Any teacher group membership -> teacher
            - Both groups -> technology_staff (higher privilege wins)
            - Neither group -> None (unauthorized)
        """
        # Case-insensitive group matching
        groups_lower = [g.lower() for g in groups]
        is_tech = self.tech_group.lower() in groups_lower
        is_teacher = any(group.lower() in groups_lower for group in self.teacher_groups)

        if is_tech:
            return "technology_staff"
        elif is_teacher:
            return "teacher"
        else:
            return None
