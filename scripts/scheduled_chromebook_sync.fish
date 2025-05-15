#!/usr/bin/env fish

# Scheduled script to sync Chromebook data between Google Admin Console and RT
# This should be set up to run as a cron job or scheduled task

# Change to script directory
cd (dirname (status filename))
cd ..

# Set environment variables from .env file if it exists
if test -f .env
    for line in (cat .env | grep -v '^#' | grep '=')
        set -l key (echo $line | cut -d '=' -f 1)
        set -l value (echo $line | cut -d '=' -f 2-)
        set -gx $key $value
    end
end

# Set path to Python executable - modify if using a virtual environment
set PYTHON_CMD "python3"

# Set path to the sync script
set SCRIPT_PATH "./scripts/sync_chromebook_data.py"

# Set default options - modify as needed for your environment
set DEFAULT_OPTS "--org-unit='/Devices' --max-results=1000"

# Log file path
set LOG_DIR "./instance/logs"
set LOG_FILE "$LOG_DIR/chromebook_sync_$(date +%Y-%m-%d).log"

# Make sure log directory exists
mkdir -p $LOG_DIR

# Run the sync script
echo "Starting Chromebook sync at $(date)" >> $LOG_FILE
$PYTHON_CMD $SCRIPT_PATH $DEFAULT_OPTS >> $LOG_FILE 2>&1
echo "Finished Chromebook sync at $(date)" >> $LOG_FILE

# Exit with the script's exit code
exit $status
