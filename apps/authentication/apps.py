"""Django app configuration for OAuth2 authentication."""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """Configuration for the OAuth2 authentication app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'OAuth2 Authentication'
    
    def ready(self):
        """Import models to apply User model monkey-patches."""
        from . import models  # noqa: F401
