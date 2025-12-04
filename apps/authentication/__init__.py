"""
Google OAuth2 Authentication App

This Django app provides OAuth2 authentication for RequestTracker Utils,
restricted to the westerncusd12.org domain. It includes:

- OAuth2 flow handlers (login, callback, logout)
- Role-based access control middleware
- User role management (technology_staff, teacher)
- Local superuser failsafe
"""

default_app_config = 'apps.authentication.apps.AuthenticationConfig'
