import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

RT_TOKEN = os.getenv("RT_TOKEN", "default-token-if-not-set")

RT_URL = "https://tickets.wc-12.com"
API_ENDPOINT = "/REST/2.0"
LABEL_WIDTH_MM = 100
LABEL_HEIGHT_MM = 62
PREFIX = 'W12-'
PADDING = 4