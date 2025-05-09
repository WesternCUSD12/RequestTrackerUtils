import csv
import os
import time
import fcntl
import datetime
import logging
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

class DeviceCheckInLogger:
    """Utility for logging device check-in activities to a CSV file with concurrency support"""
    
    def __init__(self, log_dir=None):
        """
        Initialize the CSV logger
        
        Args:
            log_dir (str, optional): Directory to store log files. If None, uses WORKING_DIR from config.
        """
        if log_dir is None:
            self.log_dir = Path(current_app.config.get('WORKING_DIR', '/var/lib/request-tracker-utils'))
        else:
            self.log_dir = Path(log_dir)
            
        # Ensure the logs directory exists
        self.logs_path = self.log_dir / 'logs'
        
        # First try to create the regular logs directory
        try:
            self.logs_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using logs directory at: {self.logs_path}")
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Failed to create logs directory at {self.logs_path}: {e}")
            
            # Fall back to using the nested logs structure that exists
            try:
                # Check if a nested logs/logs path is needed (based on the observed directory structure)
                nested_logs_path = self.log_dir / 'logs' / 'logs'
                nested_logs_path.mkdir(parents=True, exist_ok=True)
                self.logs_path = nested_logs_path
                logger.info(f"Using nested logs directory at: {self.logs_path}")
            except Exception as nested_e:
                logger.error(f"Failed to create nested logs directory: {nested_e}")
                raise
        
        # Define the path for the current day's log file
        self._set_current_log_file()
    
    def _set_current_log_file(self):
        """Set the current day's log file name based on date"""
        today = datetime.datetime.now()
        # Format file with date: checkins_2025-05-08.csv (YYYY-MM-DD format)
        self.current_log_file = self.logs_path / f"checkins_{today.strftime('%Y-%m-%d')}.csv"
        
        # Check if we need to create a new file with headers
        if not self.current_log_file.exists():
            self._create_new_log_file()
    
    def _create_new_log_file(self):
        """Create a new log file with headers"""
        try:
            with open(self.current_log_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Define CSV headers
                writer.writerow([
                    'Timestamp', 
                    'Date',
                    'Time',
                    'Asset ID', 
                    'Asset Tag', 
                    'Device Type',
                    'Serial Number',
                    'Previous Owner',
                    'Ticket ID',
                    'Has Ticket',
                    'Ticket Description',
                    'Broken Screen',
                    'Checked By'
                ])
            logger.info(f"Created new device check-in log file: {self.current_log_file}")
        except Exception as e:
            logger.error(f"Error creating new log file: {e}")
            raise
    
    def log_checkin(self, asset_data, owner_info, ticket_id, description, broken_screen, user):
        """
        Log a device check-in event to the CSV file
        
        Args:
            asset_data (dict): Asset data from RT
            owner_info (dict): Owner information
            ticket_id (str): ID of the created ticket, or None if no ticket
            description (str): Ticket description
            broken_screen (bool): Whether the screen was marked as broken
            user (str): Username of person doing the check-in
        """
        # Make sure we're using the correct log file for current day
        self._set_current_log_file()
        
        try:
            # Prepare row data
            now = datetime.datetime.now()
            
            # Get asset details
            asset_id = asset_data.get('id', '')
            asset_tag = asset_data.get('Name', '')
            
            # Extract device type and serial from CustomFields
            device_type = 'Unknown'
            serial_number = ''
            
            if 'CustomFields' in asset_data:
                for field in asset_data['CustomFields']:
                    if field.get('name') == 'Type' and field.get('values'):
                        device_type = field['values'][0]
                    elif field.get('name') == 'Serial Number' and field.get('values'):
                        serial_number = field['values'][0]
            
            # Previous owner name
            previous_owner = owner_info.get('display_name', 'None')
            
            # Write to CSV with file locking to handle concurrent access
            with open(self.current_log_file, 'a', newline='') as csvfile:
                # Use file locking to prevent concurrent write issues
                fcntl.flock(csvfile, fcntl.LOCK_EX)
                
                try:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        int(time.time()),                      # Unix timestamp
                        now.strftime('%Y-%m-%d'),              # Date in YYYY-MM-DD format
                        now.strftime('%H:%M:%S'),              # Time in HH:MM:SS format
                        asset_id,                              # RT Asset ID
                        asset_tag,                             # Asset tag
                        device_type,                           # Device type
                        serial_number,                         # Serial number
                        previous_owner,                        # Previous owner
                        ticket_id or '',                       # Ticket ID (if created)
                        'Yes' if ticket_id else 'No',          # Has ticket
                        description or '',                     # Ticket description
                        'Yes' if broken_screen else 'No',      # Broken screen
                        user or 'Unknown'                      # Checked by
                    ])
                finally:
                    # Always release the lock
                    fcntl.flock(csvfile, fcntl.LOCK_UN)
                    
            logger.info(f"Logged check-in for asset {asset_tag} by {user}")
            return True
        except Exception as e:
            logger.error(f"Error logging check-in event: {e}")
            return False
    
    def get_available_logs(self):
        """
        Get a list of available log files
        
        Returns:
            list: List of dictionaries with log file info
        """
        try:
            log_files = sorted(self.logs_path.glob("checkins_*.csv"), reverse=True)
            results = []
            
            for log_file in log_files:
                # Get file stats
                stats = log_file.stat()
                
                # Extract date from filename (format: checkins_YYYY-MM-DD.csv)
                filename = log_file.name
                # Parse the date from the filename
                try:
                    date_str = filename[9:-4]  # Remove "checkins_" prefix and ".csv" suffix
                    # Convert to datetime for formatting
                    log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                    # Format as a readable date
                    display_date = log_date.strftime('%A, %B %d, %Y')  # e.g., "Thursday, May 8, 2025"
                except ValueError:
                    display_date = date_str
                
                # Count rows
                try:
                    with open(log_file, 'r') as f:
                        row_count = sum(1 for _ in f) - 1  # Subtract header row
                        if row_count < 0:
                            row_count = 0
                except:
                    row_count = "Error"
                
                results.append({
                    'filename': filename,
                    'path': str(log_file),
                    'date': display_date,
                    'size': stats.st_size,
                    'modified': datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'device_count': row_count
                })
                
            return results
        except Exception as e:
            logger.error(f"Error getting available logs: {e}")
            return []