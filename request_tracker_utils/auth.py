"""Authentication utilities for Request Tracker Utils.

Basic HTTP authentication to protect routes from unauthorized access.
"""

from functools import wraps
from flask import request, Response
from . import config


def check_auth(username, password):
    """Verify username and password.
    
    Args:
        username: Provided username
        password: Provided password
        
    Returns:
        bool: True if credentials are valid, False otherwise
    """
    return (username == config.AUTH_USERNAME and 
            password == config.AUTH_PASSWORD)


def authenticate():
    """Send 401 response that enables basic auth."""
    return Response(
        'Authentication required. Please provide valid credentials.',
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )


def requires_auth(f):
    """Decorator to require authentication for a route.
    
    Usage:
        @bp.route('/protected')
        @requires_auth
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
