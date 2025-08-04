#!/usr/bin/env python3
"""
Script to collect Chromebook battery health via GAM and update RT asset custom field.
"""
import csv
import subprocess
import sys
import logging
import os
import argparse
from pathlib import Path

# Ensure RT utils are on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RT config first  
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import search_assets, update_asset_custom_field

# Create Flask app context for RT utils
from flask import Flask
app = Flask(__name__)
app.config.update({
    'RT_URL': os.environ.get('RT_URL') or RT_URL,
    'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
    'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
})
ctx = app.app_context()
ctx.push()

def collect_battery_data(gam_path='gam', gam_cmd=None):
    """
    Run GAM print crostelemetry to retrieve ChromeOS battery health data.
    Returns list of dict rows from CSV output.
    """
    # Build GAM command; default to print crostelemetry with battery fields
    default_cmd = ['print', 'crostelemetry', 'fields', 'batterystatusreport,batteryinfo,serialnumber']
    cmd = [gam_path] + (gam_cmd or default_cmd)
    
    logging.info(f"Running GAM command: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logging.error(f"GAM command failed: {proc.stderr.strip()}")
        sys.exit(proc.returncode)
    
    # Parse CSV output
    reader = csv.DictReader(proc.stdout.splitlines())
    data = list(reader)
    logging.info(f"Retrieved battery data for {len(data)} devices")
    return data

def categorize_battery_health(health_percentage, health_status):
    """
    Categorize battery health percentage into RT custom field values.
    Returns the appropriate category string.
    """
    if health_percentage is not None:
        if health_percentage >= 90:
            return "Excellent (90-100%)"
        elif health_percentage >= 80:
            return "Good (80-89%)"
        elif health_percentage >= 70:
            return "Fair (70-79%)"
        elif health_percentage >= 60:
            return "Poor (60-69%)"
        else:
            return "Critical (<60%)"
    elif health_status and "NORMAL" in health_status:
        return "Good (80-89%)"  # Default for NORMAL status without percentage
    else:
        return "Unknown"

def calculate_battery_health(row):
    """
    Calculate battery health percentage and status from GAM telemetry data.
    Returns tuple of (health_percentage, health_status, cycle_count).
    """
    # Extract battery data from telemetry fields
    full_charge_capacity = row.get('batteryStatusReport.0.fullChargeCapacity')
    design_capacity = row.get('batteryInfo.0.designCapacity')
    battery_health_status = row.get('batteryStatusReport.0.batteryHealth', 'UNKNOWN')
    cycle_count = row.get('batteryStatusReport.0.cycleCount', '0')
    
    health_percentage = None
    if full_charge_capacity and design_capacity:
        try:
            full_charge = float(full_charge_capacity)
            design = float(design_capacity)
            if design > 0:
                health_percentage = round((full_charge / design) * 100, 1)
        except (ValueError, ZeroDivisionError):
            logging.warning(f"Invalid battery capacity values: full={full_charge_capacity}, design={design_capacity}")
    
    return health_percentage, battery_health_status, cycle_count

def update_battery_health(data, config):
    """
    Update RT asset custom fields for battery health based on GAM telemetry data.
    Updates both Battery Health Status and Current Battery Level fields.
    """
    updated_count = 0
    for row in data:
        # Get serial number from telemetry data
        serial = row.get('serialNumber', '').strip()
        if not serial:
            logging.warning("Row missing serial number, skipping")
            continue
        
        # Calculate battery health
        health_percentage, health_status, cycle_count = calculate_battery_health(row)
        
        if health_percentage is None and health_status == 'UNKNOWN':
            logging.warning(f"No battery data available for device {serial}")
            continue
        
        # Log detailed info for debugging
        if health_percentage is not None:
            logging.info(f"Device {serial}: {health_percentage}% ({health_status}, {cycle_count} cycles)")
        else:
            logging.info(f"Device {serial}: {health_status} ({cycle_count} cycles)")
        
        # Search RT assets by serial number custom field
        filter_data = [{"field": "CF.{Serial Number}", "operator": "=", "value": serial}]
        try:
            assets = search_assets(filter_data, config=config)
        except Exception as e:
            logging.error(f"RT search error for serial {serial}: {e}")
            continue

        if not assets:
            logging.warning(f"No RT asset found for serial {serial}")
            continue

        asset = assets[0]
        asset_id = asset.get('id')
        
        # Update Battery Health Status field (GAM device status)
        try:
            # Use raw GAM status as RT expects exact values
            update_asset_custom_field(asset_id, "Battery Health Status", health_status, config=config)
            logging.info(f"Updated RT asset {asset_id} ({serial}) Battery Health Status: {health_status}")
        except Exception as e:
            logging.error(f"Failed to update Battery Health Status for asset {asset_id} ({serial}): {e}")
            continue
            
        # Update Current Battery Level field (calculated percentage - no % symbol due to regex)
        if health_percentage is not None:
            try:
                percentage_str = str(health_percentage)  # Just the number, no % symbol
                update_asset_custom_field(asset_id, "Current Battery Level", percentage_str, config=config)
                logging.info(f"Updated RT asset {asset_id} ({serial}) Current Battery Level: {percentage_str}")
            except Exception as e:
                logging.error(f"Failed to update Current Battery Level for asset {asset_id} ({serial}): {e}")
                continue
        
        updated_count += 1
    
    logging.info(f"Successfully updated {updated_count} RT assets with battery data")

def main():
    parser = argparse.ArgumentParser(description="Sync Chromebook battery health to RT via GAM")
    parser.add_argument('--gam', default='gam', help='Path to GAM executable')
    parser.add_argument(
        '--gam-cmd',
        type=str,
        default='print crostelemetry fields batterystatusreport,batteryinfo,serialnumber',
        help='GAM command after executable (default: print crostelemetry fields batterystatusreport,batteryinfo,serialnumber)'
    )
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    # RT API configuration
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }

    # Collect and update battery data
    import shlex
    gam_cmd_list = shlex.split(args.gam_cmd)  # Properly handle quoted arguments
    data = collect_battery_data(args.gam, gam_cmd=gam_cmd_list)
    update_battery_health(data, config)

if __name__ == '__main__':
    main()
