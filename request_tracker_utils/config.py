import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

RT_TOKEN = os.getenv("RT_TOKEN", "default-token-if-not-set")
WORKING_DIR = os.getenv("WORKING_DIR", "/var/lib/request-tracker-utils")  # Default working directory

RT_URL = os.getenv("RT_URL", "https://tickets.wc-12.com")  # Default RT URL
API_ENDPOINT = "/REST/2.0"
LABEL_WIDTH_MM = int(os.getenv("LABEL_WIDTH_MM", 100))  # Default label width
LABEL_HEIGHT_MM = int(os.getenv("LABEL_HEIGHT_MM", 62))  # Default label height
PREFIX = os.getenv("PREFIX", "W12-")  # Default prefix for asset tags
PADDING = int(os.getenv("PADDING", 4))  # Default padding for labels
PORT = int(os.getenv("PORT", 8080))  # Default port for the Flask app

# Redis configuration for Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")