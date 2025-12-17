import os
import sys
from pathlib import Path

# Ensure the repository root is on sys.path so the local `common` package is used
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set up environment variables before importing the app
os.environ["WORKING_DIR"] = str(Path.home().joinpath(".rtutils").absolute())

from request_tracker_utils import main

if __name__ == "__main__":
    main()
