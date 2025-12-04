"""
LDAP/Active Directory authentication middleware.

Feature: 006-ldap-auth - LDAP Authentication with Role-Based Access Control
"""

import logging
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse


logger = logging.getLogger('auth')


class LDAPAuthenticationMiddleware:
    """
    Middleware to enforce LDAP authentication and role-based access control.
    
    Tasks: T020 (authentication), T026 (role-based access)
    Flow:
    1. Check if request path is in PUBLIC_PATHS
    2. If not public and user not in session, redirect to login
    3. Check role-based access if authenticated
    4. Return 403 if role doesn't have access to path
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = getattr(settings, 'PUBLIC_PATHS', [])
        self.role_access_rules = getattr(settings, 'ROLE_ACCESS_RULES', {})
    
    def __call__(self, request):
        # Check if path is public
        if self._is_public_path(request.path):
            return self.get_response(request)
        
        # Check if user is authenticated (has session)
        if not request.session.get('ldap_user'):
            # Store the requested URL to redirect after login
            login_url = reverse('authentication:login')
            if request.path != '/':
                return redirect(f'{login_url}?next={request.path}')
            return redirect(login_url)
        
        # Check role-based access
        user_role = request.session.get('user_role')
        if not self._check_access(request.path, user_role):
            logger.warning(
                f"User {request.session.get('username')} (role: {user_role}) "
                f"denied access to {request.path}"
            )
            return render(request, 'auth/403.html', {
                'user_role': user_role
            }, status=403)
        
        response = self.get_response(request)
        return response
    
    def _is_public_path(self, path: str) -> bool:
        """Check if a path matches any public path pattern."""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False
    
    def _check_access(self, path: str, user_role: str) -> bool:
        """
        Check if a user role has access to a specific path.
        
        Rules:
        - If role has ['*'], allow all paths
        - Otherwise, check if path starts with any allowed path pattern
        """
        allowed_paths = self.role_access_rules.get(user_role, [])
        
        # Wildcard access
        if '*' in allowed_paths:
            return True
        
        # Check specific path patterns
        for allowed_path in allowed_paths:
            if path.startswith(allowed_path):
                return True
        
        return False

