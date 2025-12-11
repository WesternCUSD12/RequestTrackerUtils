#!/usr/bin/env python3
"""
Script to collect Chromebook battery health from CSV file and update RT asset custom fields.
This version reads from a pre-generated CSV file instead of calling GAM every time.
Updated to filter for WHS-C prefix devices only (changed from W12-CH).
"""
import csv
import sys

"""
CSV battery collector previously relied on a Flask app context. Flask has
been removed; turn this into a Django management command or use
`django.setup()` if you need to run it outside the web app.
"""

# Ensure RT utils are on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RT config first  
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import search_assets, update_asset_custom_field


def read_battery_data_from_csv(csv_path):
    """
    Read battery data from CSV file instead of calling GAM.
    Returns list of dict rows from CSV.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    logging.info(f"Reading battery data from CSV: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = list(reader)
    
    logging.info(f"Loaded battery data for {len(data)} devices from CSV")
    return data

def calculate_battery_health(row):
    """
    Calculate battery health percentage and extract status from CSV data.
    Returns tuple of (health_percentage, health_status, cycle_count).
    """
    # Extract battery data from CSV columns
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

def update_battery_fields(data, config):
    """
    Update RT asset custom fields for battery data.
    Updates both "Battery Health Status" and "Current Battery Level" fields.
    Only processes devices with WHS-C prefix in their RT asset names.
    """
    updated_count = 0
    skipped_no_serial = 0
    skipped_no_battery = 0
    skipped_no_asset = 0
    skipped_wrong_prefix = 0
    
    logging.info(f"Processing {len(data)} devices from CSV, filtering for WHS-C prefix devices only")
    
    for row in data:
        # Get serial number from CSV data
        serial = row.get('serialNumber', '').strip()
        if not serial:
            logging.warning("Row missing serial number, skipping")
            skipped_no_serial += 1
            continue
        
        # Calculate battery health
        health_percentage, health_status, cycle_count = calculate_battery_health(row)
        
        if health_percentage is None and health_status == 'UNKNOWN':
            logging.warning(f"No battery data available for device {serial}")
            skipped_no_battery += 1
            continue
        
        # Prepare values for RT fields
        # Battery Health Status: Raw GAM status (BATTERY_HEALTH_NORMAL, BATTERY_REPLACE_SOON, BATTERY_REPLACE_NOW)
        battery_status_value = health_status
        
        # Current Battery Level: Just the percentage number (no % symbol due to validation regex)
        battery_level_value = str(health_percentage) if health_percentage is not None else ""
        
        logging.debug(f"Processing device {serial}: {battery_level_value}% health, status: {battery_status_value}")
        
        # Search RT assets by serial number custom field
        filter_data = [{"field": "CF.{Serial Number}", "operator": "=", "value": serial}]
        try:
            assets = search_assets(filter_data, config=config)
        except Exception as e:
            logging.error(f"RT search error for serial {serial}: {e}")
            continue

        if not assets:
            logging.warning(f"No RT asset found for serial {serial}")
            skipped_no_asset += 1
            continue

        asset = assets[0]
        asset_id = asset.get('id')
        asset_name = asset.get('Name', '')
        
        # Filter to only process devices with WHS-C prefix
        if not asset_name.startswith('WHS-C'):
            logging.debug(f"Skipping device {serial} (asset: {asset_name}) - not WHS-C prefix")
            skipped_wrong_prefix += 1
            continue
        
        logging.info(f"Processing WHS-C device: {asset_name} (serial: {serial})")
        
        # Update Battery Health Status field
        if battery_status_value:
            try:
                update_asset_custom_field(asset_id, "Battery Health Status", battery_status_value, config=config)
                logging.info(f"Updated Battery Health Status for asset {asset_id} ({serial}): {battery_status_value}")
            except Exception as e:
                logging.error(f"Failed to update Battery Health Status for asset {asset_id} ({serial}): {e}")
                continue
        
        # Update Current Battery Level field  
        if battery_level_value:
            try:
                update_asset_custom_field(asset_id, "Current Battery Level", battery_level_value, config=config)
                logging.info(f"Updated Current Battery Level for asset {asset_id} ({serial}): {battery_level_value}")
            except Exception as e:
                logging.error(f"Failed to update Current Battery Level for asset {asset_id} ({serial}): {e}")
                continue
        
        updated_count += 1
    
    # Print summary statistics
    logging.info("=== BATTERY SYNC SUMMARY ===")
    logging.info(f"Total devices in CSV: {len(data)}")
    logging.info(f"Successfully updated: {updated_count}")
    logging.info(f"Skipped - no serial number: {skipped_no_serial}")
    logging.info(f"Skipped - no battery data: {skipped_no_battery}")
    logging.info(f"Skipped - no RT asset found: {skipped_no_asset}")
    logging.info(f"Skipped - not WHS-C prefix: {skipped_wrong_prefix}")
    logging.info("========================")

def main():
    parser = argparse.ArgumentParser(description="Sync Chromebook battery health to RT from CSV file (WHS-C devices only)")
    parser.add_argument('--csv', default='chromebook_battery_data.csv', help='Path to CSV file with battery data')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable debug logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

    # RT API configuration
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }

    # Determine CSV file path
    csv_path = args.csv
    if not os.path.isabs(csv_path):
        # If relative path, make it relative to script directory
        script_dir = Path(__file__).parent.parent
        csv_path = script_dir / csv_path
    
    try:
        # Read battery data from CSV
        data = read_battery_data_from_csv(csv_path)

        if args.dry_run:
            logging.info("DRY RUN - Would process the following devices:")
            _whs_c_count = 0
            for row in data[:10]:  # Show first 10 as example
                serial = row.get('serialNumber', '').strip()
                if serial:
                    health_percentage, health_status, cycle_count = calculate_battery_health(row)

                    # Mock RT asset search for dry run
                    logging.info(f"  {serial}: {health_percentage}% ({health_status})")
                    # In a real dry run, we'd need to actually search RT to check the prefix
                    # For now, just show what data we have

            logging.info(f"Total devices in CSV: {len(data)}")
            logging.info("Note: Dry run does not check RT asset names for WHS-C prefix")
        else:
            # Update battery data in RT
            update_battery_fields(data, config)

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
