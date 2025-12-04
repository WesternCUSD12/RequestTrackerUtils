# Authentication

Request Tracker Utils implements HTTP Basic Authentication to protect routes from unauthorized access.

## Configuration

Authentication credentials are configured via environment variables:

```bash
# In your .env file or environment:
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_secure_password
```

**Default credentials** (should be changed in production):

- Username: `admin`
- Password: `admin`

## Public Routes

The `/labels` route and all its sub-routes are **public** and do not require authentication:

- `/labels/`
- `/labels/print`
- `/labels/batch`
- `/labels/assets`
- All other `/labels/*` endpoints

This allows external systems (like RT webhooks, label printers, etc.) to access label generation without authentication.

## Protected Routes

All other routes require HTTP Basic Authentication:

- `/` (homepage)
- `/devices/*` (device check-in/out, audit routes)
- `/students/*`
- `/assets/*`
- `/next-asset-tag`, `/confirm-asset-tag`, etc. (tag management)

## Usage

### From Browser

When accessing protected routes in a browser, you'll be prompted for username and password.

### From Command Line (curl)

```bash
# With authentication
curl -u username:password http://localhost:8080/

# Without authentication (public route)
curl http://localhost:8080/labels/print?assetId=123
```

### From Python

```python
import requests

# Protected route
response = requests.get(
    'http://localhost:8080/',
    auth=('username', 'password')
)

# Public route (no auth needed)
response = requests.get(
    'http://localhost:8080/labels/print?assetId=123'
)
```

## Security Notes

1. **Change default credentials** in production environments
2. **Use HTTPS** in production to encrypt credentials in transit
3. Consider implementing more robust authentication (OAuth, JWT, etc.) for production use
4. Store credentials securely (environment variables, secrets management)
5. Never commit credentials to version control

## Implementation Details

Authentication is implemented using Flask's `before_request` hook in `request_tracker_utils/__init__.py`:

```python
@app.before_request
def require_authentication():
    """Require authentication for all routes except /labels/*."""
    if request.path.startswith('/labels'):
        return None  # Allow without authentication

    # Check authentication for all other routes
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    return None
```

The authentication logic is in `request_tracker_utils/auth.py`.
