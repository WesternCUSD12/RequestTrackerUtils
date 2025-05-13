#!/usr/bin/env python3
"""
Migration script to import existing CSV log files into the SQLite database.
Run this script once to populate the database with historical check-in records.
"""
import os
import sys
import csv
import glob
import logging
from pathlib import Path
from flask import Flask

# Add parent directory to path so we can import request_tracker_utils modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from request_tracker_utils.utils.db import get_db_connection, init_db
from request_tracker_utils.config import WORKING_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a minimal Flask app for the database context
app = Flask(__name__, instance_path=WORKING_DIR)

def import_csv_file(file_path):
    """Import a single CSV file into the database"""
    logger.info(f"Importing {file_path}")
    
    # Extract date from filename (format: checkins_YYYY-MM-DD.csv)
    filename = os.path.basename(file_path)
    if not filename.startswith("checkins_") or not filename.endswith(".csv"):
        logger.warning(f"Skipping file with invalid format: {filename}")
        return 0
        
    date_str = filename[9:-4]  # Remove "checkins_" prefix and ".csv" suffix
    
    with app.app_context():
        # Ensure database is initialized
        init_db()
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            imported_count = 0
            
            # Check if we already have entries for this date
            cursor.execute("SELECT COUNT(*) FROM device_logs WHERE date = ?", (date_str,))
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                logger.warning(f"Found {existing_count} existing records for date {date_str}. Skipping to avoid duplicates.")
                logger.warning(f"To reimport this file, first delete existing records with: DELETE FROM device_logs WHERE date = '{date_str}'")
                return 0
            
            # Open and parse CSV file
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)  # Skip header row
                
                # Process each row
                for row in reader:
                    if len(row) < 12:  # Ensure we have enough columns
                        logger.warning(f"Skipping row with insufficient data: {row}")
                        continue
                    
                    try:
                        # Extract data from row
                        timestamp = int(row[0]) if row[0].isdigit() else 0
                        date = row[1]
                        time = row[2]
                        asset_id = row[3]
                        asset_tag = row[4]
                        device_type = row[5]
                        serial_number = row[6]
                        previous_owner = row[7]
                        ticket_id = row[8] if row[8] else None
                        has_ticket = 1 if row[9].lower() == 'yes' else 0
                        ticket_description = row[10]
                        broken_screen = 1 if row[11].lower() == 'yes' else 0
                        checked_by = row[12] if len(row) > 12 else 'Unknown'
                        
                        # Insert into database
                        cursor.execute('''
                        INSERT INTO device_logs (
                            timestamp, date, time, asset_id, asset_tag, device_type,
                            serial_number, previous_owner, ticket_id, has_ticket,
                            ticket_description, broken_screen, checked_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp, date, time, asset_id, asset_tag, device_type,
                            serial_number, previous_owner, ticket_id, has_ticket,
                            ticket_description, broken_screen, checked_by
                        ))
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error importing row: {e}")
                        logger.error(f"Row data: {row}")
                        
            # Commit changes
            conn.commit()
            logger.info(f"Successfully imported {imported_count} records from {filename}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing file {file_path}: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

def find_csv_files(directories):
    """Find all check-in CSV files in the specified directories"""
    log_files = []
    
    for directory in directories:
        directory_path = Path(directory)
        if not directory_path.exists():
            logger.warning(f"Directory does not exist: {directory_path}")
            continue
            
        # Look for CSV files directly in the directory
        pattern = str(directory_path / "checkins_*.csv")
        log_files.extend(glob.glob(pattern))
        
        # Look for CSV files in a logs subdirectory
        logs_pattern = str(directory_path / "logs" / "checkins_*.csv")
        log_files.extend(glob.glob(logs_pattern))
        
        # Look for CSV files in a logs/logs subdirectory (nested structure)
        nested_logs_pattern = str(directory_path / "logs" / "logs" / "checkins_*.csv")
        log_files.extend(glob.glob(nested_logs_pattern))
    
    return sorted(log_files)

def main():
    """Main function to find and import CSV files"""
    # Set up search directories
    script_dir = Path(__file__).parent.parent
    instance_dir = script_dir / 'instance'
    home_dir = Path.home() / 'western_admin' / 'RT'
    
    # Define all places to look for CSV files
    search_dirs = [
        script_dir,
        instance_dir,
        instance_dir / 'logs',
        '/var/lib/request-tracker-utils',
        '/var/lib/request-tracker-utils/logs',
        home_dir,
        home_dir / 'logs'
    ]
    
    # Find all CSV files
    log_files = find_csv_files(search_dirs)
    
    if not log_files:
        logger.warning("No CSV files found in search directories.")
        return
        
    logger.info(f"Found {len(log_files)} CSV files to process")
    
    # Import each file
    total_imported = 0
    for file_path in log_files:
        imported = import_csv_file(file_path)
        total_imported += imported
        
    logger.info(f"Migration complete. Imported {total_imported} records from {len(log_files)} files.")

if __name__ == "__main__":
    main()