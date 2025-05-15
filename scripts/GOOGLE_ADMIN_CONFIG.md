# Google Admin API Configuration

# Copy this file to .env in the project root directory

# or set these environment variables in your environment

# Google Workspace Domain (required)

# This is your primary domain for Google Workspace Admin

GOOGLE_ADMIN_DOMAIN=example.com

# Google Admin Subject (required)

# This is the email address of an admin account in your domain

# The service account will impersonate this user

GOOGLE_ADMIN_SUBJECT=admin@example.com

# Google Credentials File Path (required)

# Path to the service account JSON credentials file

# This should be a file downloaded from the Google Cloud Console

GOOGLE_CREDENTIALS_FILE=/path/to/google-credentials.json

# Optional: Rate Limiting

# Delay in seconds between API calls to avoid hitting quota limits

GOOGLE_API_RATE_LIMIT=0.5
