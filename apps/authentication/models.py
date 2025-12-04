"""
User model extensions for OAuth2 authentication.

Feature: 006-google-auth - Google OAuth2 Domain-Restricted Authentication
Task: T025 - Add helper method for user role display

Note: google_user_id and user_role fields are added via migrations to Django's User model.
This module provides helper functions for working with these fields.
"""

from django.contrib.auth.models import User


# Role choices (matching migration 0002_add_user_role.py)
USER_ROLE_CHOICES = {
    'technology_staff': 'Technology Staff',
    'teacher': 'Teacher',
}


def get_user_role_display(user: User) -> str:
    """
    Get the human-readable display name for a user's role.
    
    Args:
        user: Django User instance
        
    Returns:
        str: Display name for user role (e.g., "Technology Staff", "Teacher")
             Returns empty string if no role assigned
    """
    user_role = getattr(user, 'user_role', None)
    if not user_role:
        return ''
    return USER_ROLE_CHOICES.get(user_role, user_role)


# Monkey-patch User model to add get_user_role_display method
User.get_user_role_display = lambda self: get_user_role_display(self)
