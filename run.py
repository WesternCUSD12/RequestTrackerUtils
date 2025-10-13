import os
from pathlib import Path

# Set up environment variables before importing the app
os.environ['WORKING_DIR'] = str(Path.home().joinpath(".rtutils").absolute())

from request_tracker_utils import main

if __name__ == "__main__":
    main()