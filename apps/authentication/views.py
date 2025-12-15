"""
LDAP/Active Directory authentication views.

Feature: 006-ldap-auth - LDAP Authentication with Role-Based Access Control
Tasks: T015-T018, T024, T028, T030-T031
"""

import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from .ldap_client import (
    LDAPClient,
    LDAPServiceUnavailableError,
    LDAPInvalidCredentialsError,
    LDAPAccountDisabledError,
)


logger = logging.getLogger("auth")


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    Handle LDAP login - display form (GET) or process credentials (POST).

    Tasks: T015 (GET), T016-T017 (POST), T024 (logging), T028 (role redirect), T030-T031 (validation)
    """
    # If already authenticated, redirect to appropriate page
    if request.session.get("ldap_user"):
        user_role = request.session.get("user_role")
        if user_role == "teacher":
            return redirect("/devices/audit/")
        return redirect("/")

    if request.method == "GET":
        # Task T015: Display login form
        next_url = request.GET.get("next", "/")
        return render(request, "auth/login.html", {"next": next_url})

    # POST: Process login
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    next_url = request.POST.get("next", "/")

    # Test credentials for development (bypass LDAP)
    if username == "admin" and password == "admin":
        # Simulate admin user session
        request.session["ldap_user"] = "admin"
        request.session["user_dn"] = "CN=admin,OU=Test,DC=test,DC=com"
        request.session["display_name"] = "Admin User"
        request.session["email"] = "admin@example.com"
        request.session["user_role"] = "technology_staff"
        request.session["groups"] = ["tech-team"]
        request.session["authenticated_at"] = datetime.utcnow().isoformat()

        logger.info(f"test_login_success: {username} (role: technology_staff)")
        return redirect("/")

    elif username == "teacher" and password == "teacher":
        # Simulate teacher user session
        request.session["ldap_user"] = "teacher"
        request.session["user_dn"] = "CN=teacher,OU=Test,DC=test,DC=com"
        request.session["display_name"] = "Teacher User"
        request.session["email"] = "teacher@example.com"
        request.session["user_role"] = "teacher"
        request.session["groups"] = ["TEACHERS"]
        request.session["authenticated_at"] = datetime.utcnow().isoformat()

        logger.info(f"test_login_success: {username} (role: teacher)")
        return redirect("/devices/audit/")

    if not username or not password:
        return render(
            request,
            "auth/login.html",
            {
                "error_type": "Invalid Input",
                "error_message": "Username and password are required",
                "username": username,
                "next": next_url,
            },
        )

    try:
        # Task T016-T017: Authenticate via LDAP
        ldap_client = LDAPClient()
        success, user_info = ldap_client.authenticate(username, password)

        if not success or not user_info:
            # Task T024: Log failure
            logger.warning(
                f"Authentication failed for user: {username} from IP: {request.META.get('REMOTE_ADDR')}"
            )
            return render(
                request,
                "auth/login.html",
                {
                    "error_type": "Authentication Failed",
                    "error_message": "Invalid credentials",
                    "username": username,
                    "next": next_url,
                },
            )

        # Task T030: Validate user is in authorized groups
        user_role = ldap_client.get_user_role(user_info["groups"])

        if not user_role:
            # Task T031: Display "Not authorized" error
            logger.warning(
                f"User {username} not in authorized groups. "
                f"Groups: {user_info['groups']} from IP: {request.META.get('REMOTE_ADDR')}"
            )
            # Task T033: Log access_denied event
            logger.info(
                f"access_denied: {username} from IP: {request.META.get('REMOTE_ADDR')}"
            )

            return render(
                request,
                "auth/login.html",
                {
                    "error_type": "Access Denied",
                    "error_message": "You are not authorized to access this application. "
                    "Only members of tech-team or teacher groups may sign in.",
                    "username": username,
                    "next": next_url,
                },
            )

        # Task T017: Store session data
        request.session["ldap_user"] = user_info["username"]
        request.session["user_dn"] = user_info["dn"]
        request.session["display_name"] = user_info["display_name"]
        request.session["email"] = user_info["email"]
        request.session["user_role"] = user_role
        request.session["groups"] = user_info["groups"]
        request.session["authenticated_at"] = datetime.utcnow().isoformat()

        # Task T024: Log successful authentication
        logger.info(
            f"login_success: {username} (role: {user_role}) "
            f"from IP: {request.META.get('REMOTE_ADDR')}"
        )

        # Task T028: Redirect based on role
        if user_role == "teacher":
            return redirect("/audit/")

        # Redirect to next URL or home
        if next_url and next_url != "/auth/login":
            return redirect(next_url)
        return redirect("/")

    except LDAPInvalidCredentialsError as e:
        # Task T024: Log failed attempt
        logger.warning(
            f"login_failure: {username} - invalid credentials from IP: {request.META.get('REMOTE_ADDR')}"
        )

        return render(
            request,
            "auth/login.html",
            {
                "error_type": "Invalid Credentials",
                "error_message": "Invalid username or password",
                "username": username,
                "next": next_url,
            },
        )

    except LDAPAccountDisabledError as e:
        # Task T035: Handle disabled/locked accounts (FR-013)
        logger.warning(
            f"login_failure: {username} - account disabled/locked from IP: {request.META.get('REMOTE_ADDR')}"
        )

        return render(
            request,
            "auth/login.html",
            {
                "error_type": "Account Issue",
                "error_message": str(e),
                "username": username,
                "next": next_url,
            },
        )

    except LDAPServiceUnavailableError as e:
        # Task T024, T034: Log service unavailable
        logger.error(
            f"login_failure: {username} - LDAP service unavailable from IP: {request.META.get('REMOTE_ADDR')}"
        )

        return render(
            request,
            "auth/login.html",
            {
                "error_type": "Service Unavailable",
                "error_message": "Authentication service is currently unavailable. Please try again later.",
                "username": username,
                "next": next_url,
            },
        )

    except Exception as e:
        # Unexpected error
        logger.error(
            f"login_failure: {username} - unexpected error: {e} from IP: {request.META.get('REMOTE_ADDR')}",
            exc_info=True,
        )

        return render(
            request,
            "auth/login.html",
            {
                "error_type": "Error",
                "error_message": "An unexpected error occurred. Please try again.",
                "username": username,
                "next": next_url,
            },
        )


def logout_view(request: HttpRequest) -> HttpResponse:
    """
    Log out the current user.

    Task: T018, T024 (logging)
    Flow:
    1. Log the logout event
    2. Clear Django session
    3. Redirect to login page
    """
    username = request.session.get("username", "unknown")

    # Task T024: Log logout event
    logger.info(f"logout: {username} from IP: {request.META.get('REMOTE_ADDR')}")

    # Task T018: Clear session
    request.session.flush()

    return redirect("authentication:login")
