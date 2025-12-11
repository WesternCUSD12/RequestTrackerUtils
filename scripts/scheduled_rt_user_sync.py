#!/usr/bin/env python3
"""
Scheduled script to automatically sync student data to RT user custom fields.
This script is designed to be run as a cron job or scheduled task.
"""
import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path to import request_tracker_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
load_dotenv()

# Import RT API utilities (imports after sys.path and dotenv by design)
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN  # noqa: E402

# Create a Flask app context for testing
"""
This scheduled sync script previously created a Flask app context.
Flask has been removed from the project. If you still need to run
scheduled syncs outside Django, convert this to use `django.setup()`
and call the appropriate management commands.
"""

# Configure logging to file
log_dir = Path(os.environ.get('LOG_DIR') or (Path.home() / '.rtutils' / 'logs'))
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"rt_user_sync_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for the scheduled sync script.
    """
    try:
        logger.info("Starting scheduled RT user custom fields sync")
        
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
        
        results = sync_student_data_to_rt(config, dry_run=False)
        
        logger.info("RT user custom fields sync complete")
        logger.info(f"Total students: {results['total_students']}")
        logger.info(f"RT users updated: {results['updated_users']}")
        logger.info(f"Skipped (no RT user ID): {results['skipped_no_rt']}")
        logger.info(f"Errors: {results['errors']}")
        
        # Exit with error code if there were issues
        if results['errors'] > 0:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error running scheduled sync: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
