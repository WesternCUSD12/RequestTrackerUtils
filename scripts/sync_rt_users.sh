#!/usr/bin/env bash

# Sync RT User Custom Fields - Shell wrapper script
# This script is intended to be used by cron to run the sync process

# Define base directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Ensure working in correct directory
cd "$BASE_DIR" || { echo "Failed to change to base directory"; exit 1; }

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment"
    source venv/bin/activate
fi

# Run the sync script
echo "Running RT user custom fields sync script"
python "$SCRIPT_DIR/scheduled_rt_user_sync.py"

# Capture exit code
EXIT_CODE=$?

# Deactivate virtual environment if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi

# Exit with the same code as the Python script
exit $EXIT_CODE
