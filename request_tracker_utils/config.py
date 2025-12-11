import os
from dotenv import load_dotenv
from pathlib import Path
import platform

# Load environment variables from the .env file
load_dotenv()

# Determine platform-appropriate working directory
def get_default_working_dir():
    """Return a platform-appropriate default working directory."""
    system = platform.system()
    if system == "Darwin":  # macOS
        # Use the user's home directory on macOS
        return str(Path.home().joinpath(".rtutils").absolute())
    elif system == "Linux":
        # Use the traditional Linux path
        return "/var/lib/request-tracker-utils"
    else:
        # Fallback for other platforms (Windows, etc.)
        return str(Path.home().joinpath(".rtutils").absolute())

RT_TOKEN = os.getenv("RT_TOKEN", "default-token-if-not-set")

# Authentication credentials
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "admin")

# Ensure WORKING_DIR is always an absolute path
working_dir_env = os.getenv("WORKING_DIR")
if working_dir_env:
    # Convert to absolute path if environment variable is provided
    WORKING_DIR = os.path.abspath(working_dir_env)
else:
    # Use the default working directory
    WORKING_DIR = get_default_working_dir()

RT_URL = os.getenv("RT_URL", "https://tickets.wc-12.com")  # Default RT URL
API_ENDPOINT = "/REST/2.0"
LABEL_WIDTH_MM = int(os.getenv("LABEL_WIDTH_MM", 100))  # Default label width
LABEL_HEIGHT_MM = int(os.getenv("LABEL_HEIGHT_MM", 62))  # Default label height
PREFIX = os.getenv("PREFIX", "W12-")  # Default prefix for asset tags
PADDING = int(os.getenv("PADDING", 4))  # Default padding for labels
def _get_env_int(name, default):
    val = os.getenv(name)
    if val is None:
        return default
    try:
        # Strip quotes and whitespace that might be present when values are passed
        cleaned = val.strip().strip('\"').strip("\'")
        return int(cleaned)
    except Exception:
        return default

PORT = _get_env_int('PORT', 8080)  # Default port for the Flask app
RT_CATALOG = os.getenv("RT_CATALOG", "General assets")  # Default RT catalog for assets
