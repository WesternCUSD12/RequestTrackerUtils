#!/usr/bin/env python3
"""
Script to sync Chromebook data between Google Admin Console and Request Tracker.

This script:
1. Pulls serial numbers and MAC addresses from Google Admin Console
2. Updates device names and annotated users in Google Admin based on RT data
3. Matches devices by serial number and MAC address
4. Performs batch updates with error handling and rate limiting
"""

import sys
import logging
import argparse
import os
from pathlib import Path
import traceback
from dotenv import load_dotenv

# Add parent directory to Python path to import request_tracker_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
load_dotenv()

# Import RT API utilities (after sys.path changes)
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN  # noqa: E402
from request_tracker_utils.utils.rt_api import fetch_asset_data, search_assets  # noqa: E402

# Import Google Admin API utilities
from request_tracker_utils.utils.google_admin import (  # noqa: E402
    list_chromebook_devices,
    batch_update_chromebooks,
)

# Create a Flask app context for testing
from flask import Flask  # noqa: E402
app = Flask(__name__)
app.config.update({
    'RT_URL': RT_URL,
    'API_ENDPOINT': API_ENDPOINT,
    'RT_TOKEN': RT_TOKEN,
    'INSTANCE_PATH': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance'),
    'GOOGLE_ADMIN_DOMAIN': os.environ.get('GOOGLE_ADMIN_DOMAIN'),
    'GOOGLE_ADMIN_SUBJECT': os.environ.get('GOOGLE_ADMIN_SUBJECT'),
    'GOOGLE_CREDENTIALS_FILE': os.environ.get('GOOGLE_CREDENTIALS_FILE')
})

# Set up the app context
ctx = app.app_context()
ctx.push()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_assets_by_serial(serial_numbers, config=None):
    """
    Fetch RT assets by serial number.
    
    Args:
        serial_numbers (list): List of serial numbers to search for
        config (dict, optional): Configuration dictionary
        
    Returns:
        dict: Dictionary mapping serial numbers to RT asset data
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
    
    result = {}
    
    try:
        # Use search to find assets
        for serial in serial_numbers:
            # Skip empty or invalid serial numbers
            if not serial or len(serial) < 4:
                continue
            
            # Use JSON filter format for custom field search
            filter_data = [
                {
                    "field": "CF.{Serial Number}",
                    "operator": "=",
                    "value": serial
                }
            ]
            logger.debug(f"Searching for asset with filter: {filter_data}")
            
            try:
                search_result = search_assets(filter_data, config=config)
                assets = search_result
                
                if assets and len(assets) > 0:
                    logger.info(f"Found {len(assets)} assets matching serial number: {serial}")
                    # Use the first match if multiple found
                    result[serial] = assets[0]
                else:
                    logger.info(f"No asset found with serial number: {serial}")
            except Exception as e:
                logger.warning(f"Error searching assets for serial {serial}: {e}")
                
    except Exception as e:
        logger.error(f"Error fetching assets by serial numbers: {e}")
        
    logger.info(f"Total assets found by serial number: {len(result)}")
    return result

def get_assets_by_mac_address(mac_addresses, config=None):
    """
    Fetch RT assets by MAC address.
    
    Args:
        mac_addresses (list): List of MAC addresses to search for
        config (dict, optional): Configuration dictionary
        
    Returns:
        dict: Dictionary mapping MAC addresses to RT asset data
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
    
    result = {}
    
    try:
        # Use search to find assets
        for mac in mac_addresses:
            # Skip empty or invalid MAC addresses
            if not mac or len(mac) < 8:
                continue
                
            # Normalize MAC address format for search
            # Remove delimiters and convert to lowercase
            mac_normalized = mac.lower().replace(':', '').replace('-', '').replace('.', '')
            
            # Search for asset with matching MAC address in any of the typical MAC fields
            query = f"'MAC Address' LIKE '*{mac_normalized}*' OR 'Wi-Fi MAC' LIKE '*{mac_normalized}*' OR 'Ethernet MAC' LIKE '*{mac_normalized}*'"
            logger.debug(f"Searching for asset with query: {query}")
            
            try:
                search_result = search_assets(query, config=config)
                assets = search_result
                
                if assets and len(assets) > 0:
                    logger.info(f"Found {len(assets)} assets matching MAC address: {mac}")
                    # Use the first match if multiple found
                    result[mac] = assets[0]
                else:
                    logger.info(f"No asset found with MAC address: {mac}")
            except Exception as e:
                logger.warning(f"Error searching assets for MAC {mac}: {e}")
                
    except Exception as e:
        logger.error(f"Error fetching assets by MAC addresses: {e}")
        
    logger.info(f"Total assets found by MAC address: {len(result)}")
    return result

def get_rt_current_user(asset_id, config=None):
    """
    Get the current user of an RT asset.
    
    Args:
        asset_id (str): The RT asset ID
        config (dict, optional): Configuration dictionary
        
    Returns:
        str: Email address of the current user, or None if not found
    """
    try:
        asset_data = fetch_asset_data(asset_id, config=config)
        # Check for user email in custom fields
        if 'CustomFields' in asset_data:
            for field in asset_data.get('CustomFields', []):
                if isinstance(field, dict) and field.get('name', '').lower() in ['current user', 'user', 'assigned to']:
                    value = field.get('values', [None])[0]
                    if value and isinstance(value, str):
                        return value
        # Fallback: check Owner field in asset data
        owner = asset_data.get('Owner')
        if owner:
            # If owner is a string, return as is
            if isinstance(owner, str):
                return owner
            # If owner is a dict, extract email from 'id' field
            if isinstance(owner, dict):
                user_id = owner.get('id')
                if user_id and user_id.lower() != 'nobody':
                    # Use Google Admin domain from config or environment
                    domain = (config or {}).get('GOOGLE_ADMIN_DOMAIN') or os.environ.get('GOOGLE_ADMIN_DOMAIN')
                    if domain:
                        return f"{user_id}@{domain}"
                    else:
                        return user_id  # fallback to just username
                else:
                    return None  # skip 'Nobody'
        return None
    except Exception as e:
        logger.error(f"Error getting current user for asset {asset_id}: {e}")
        return None

def get_rt_device_name(asset_data):
    """
    Get the device name from RT asset data.
    
    Args:
        asset_data (dict): RT asset data
        
    Returns:
        str: Device name, or None if not found
    """
    # First try to use the asset Name
    if asset_data.get('Name'):
        return asset_data['Name']
    
    # Then try common custom fields
    if 'CustomFields' in asset_data:
        for field in asset_data.get('CustomFields', []):
            if isinstance(field, dict) and field.get('name', '').lower() in ['device name', 'computer name', 'hostname']:
                return field.get('values', [None])[0]
    
    # Fall back to asset ID if it exists
    if asset_data.get('id'):
        return f"RT-{asset_data['id']}"
    
    return None

def sync_chromebooks_with_rt(config=None, dry_run=False, org_unit_path='/', max_results=1000):
    """
    Sync Chromebook data between Google Admin Console and RT.
    
    Args:
        config (dict, optional): Configuration dictionary
        dry_run (bool): If True, don't actually make changes
        org_unit_path (str): The organizational unit path to list devices from
        max_results (int): Maximum number of devices to process
        
    Returns:
        dict: Summary of results
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN,
            'GOOGLE_ADMIN_DOMAIN': os.environ.get('GOOGLE_ADMIN_DOMAIN'),
            'GOOGLE_ADMIN_SUBJECT': os.environ.get('GOOGLE_ADMIN_SUBJECT'),
            'GOOGLE_CREDENTIALS_FILE': os.environ.get('GOOGLE_CREDENTIALS_FILE')
        }
    
    # Initialize results
    results = {
        'total_devices': 0,
        'matched_devices': 0,
        'updated_device_names': 0,
        'updated_users': 0,
        'errors': 0,
        'skipped': 0
    }
    
    try:
        # 1. Fetch Chromebook devices from Google Admin
        logger.info(f"Fetching Chromebook devices from Google Admin Console (org unit: {org_unit_path})...")
        chromebooks = list_chromebook_devices(
            org_unit_path=org_unit_path,
            max_results=max_results,
            config=config
        )
        results['total_devices'] = len(chromebooks)
        logger.info(f"Retrieved {len(chromebooks)} Chromebook devices from Google Admin")
        
        # Extract serial numbers and MAC addresses
        serial_numbers = [device.get('serialNumber') for device in chromebooks if device.get('serialNumber')]
        mac_addresses = []
        for device in chromebooks:
            if device.get('macAddress'):
                mac_addresses.append(device.get('macAddress'))
            if device.get('ethernetMacAddress'):
                mac_addresses.append(device.get('ethernetMacAddress'))
        
        # 2. Match devices with RT assets
        logger.info(f"Matching {len(serial_numbers)} devices with RT assets by serial number...")
        rt_assets_by_serial = get_assets_by_serial(serial_numbers, config)
        
        logger.info(f"Matching {len(mac_addresses)} devices with RT assets by MAC address...")
        rt_assets_by_mac = get_assets_by_mac_address(mac_addresses, config)
        
        # 3. Prepare updates for Google Admin
        updates = []
        
        for device in chromebooks:
            device_id = device.get('deviceId')
            serial = device.get('serialNumber')
            mac = device.get('macAddress')
            ethernet_mac = device.get('ethernetMacAddress')
            
            if not device_id:
                logger.warning(f"Skipping device with missing device ID: {serial}")
                results['skipped'] += 1
                continue
                
            # Try to match with RT asset
            rt_asset = None
            
            # First try by serial number
            if serial and serial in rt_assets_by_serial:
                rt_asset = rt_assets_by_serial[serial]
                logger.info(f"Matched device {serial} with RT asset by serial number")
            
            # Then try by MAC addresses if not found by serial
            elif mac and mac in rt_assets_by_mac:
                rt_asset = rt_assets_by_mac[mac]
                logger.info(f"Matched device {serial} with RT asset by WiFi MAC address")
            elif ethernet_mac and ethernet_mac in rt_assets_by_mac:
                rt_asset = rt_assets_by_mac[ethernet_mac]
                logger.info(f"Matched device {serial} with RT asset by Ethernet MAC address")
                
            if rt_asset:
                results['matched_devices'] += 1
                
                # Get device name and current user from RT
                device_name = get_rt_device_name(rt_asset)
                current_user = get_rt_current_user(rt_asset.get('id'), config)
                
                update_needed = False
                update_data = {}
                
                # Check if device name needs updating
                if device_name and device_name != device.get('annotatedAssetId'):
                    update_data['annotatedAssetId'] = device_name
                    update_needed = True
                    logger.info(f"Device name update needed for {serial}: {device.get('annotatedAssetId')} -> {device_name}")
                    
                # Check if current user needs updating
                if current_user and current_user != device.get('annotatedUser'):
                    update_data['annotatedUser'] = current_user
                    update_needed = True
                    logger.info(f"Current user update needed for {serial}: {device.get('annotatedUser')} -> {current_user}")
                
                if update_needed:
                    updates.append({
                        'device_id': device_id,
                        'update_data': update_data,
                        'serial': serial
                    })
        
        # 4. Apply updates to Google Admin
        if updates:
            logger.info(f"Preparing to update {len(updates)} devices in Google Admin")
            
            if dry_run:
                logger.info("DRY RUN - Not making actual changes")
                for update in updates:
                    serial = update.get('serial')
                    update_data = update.get('update_data', {})
                    
                    if 'annotatedAssetId' in update_data:
                        results['updated_device_names'] += 1
                        logger.info(f"DRY RUN - Would update device name for {serial}: {update_data['annotatedAssetId']}")
                        
                    if 'annotatedUser' in update_data:
                        results['updated_users'] += 1
                        logger.info(f"DRY RUN - Would update annotated user for {serial}: {update_data['annotatedUser']}")
            else:
                logger.info("Applying updates to Google Admin devices...")
                successful_updates, failed_updates = batch_update_chromebooks(
                    updates, 
                    config=config,
                    rate_limit=0.5
                )
                
                # Count successful updates
                for update in successful_updates:
                    update_data = update.get('update_data', {})
                    
                    if 'annotatedAssetId' in update_data:
                        results['updated_device_names'] += 1
                        
                    if 'annotatedUser' in update_data:
                        results['updated_users'] += 1
                
                # Count failed updates
                results['errors'] = len(failed_updates)
                
                logger.info(f"Successfully updated {len(successful_updates)} devices in Google Admin")
                if failed_updates:
                    logger.warning(f"Failed to update {len(failed_updates)} devices")
        else:
            logger.info("No updates needed for Google Admin devices")
        
        return results
        
    except Exception as e:
        logger.error(f"Error syncing Chromebooks with RT: {e}")
        logger.error(traceback.format_exc())
        results['errors'] += 1
        return results
        
def main():
    parser = argparse.ArgumentParser(description="Sync Chromebook data between Google Admin Console and RT")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually update Google Admin, just show what would be done")
    parser.add_argument('--org-unit', type=str, default='/', help="Organizational unit path to list devices from")
    parser.add_argument('--max-results', type=int, default=1000, help="Maximum number of devices to process")
    parser.add_argument('--rate-limit', type=float, default=0.5, help="Delay in seconds between API calls")
    parser.add_argument('--credentials-file', type=str, help="Path to Google API credentials JSON file")
    parser.add_argument('--admin-domain', type=str, help="Google Admin domain")
    parser.add_argument('--admin-subject', type=str, help="Google Admin subject (delegate email)")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    # Always use imported defaults if env vars are missing
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN,
        'GOOGLE_ADMIN_DOMAIN': args.admin_domain or os.environ.get('GOOGLE_ADMIN_DOMAIN'),
        'GOOGLE_ADMIN_SUBJECT': args.admin_subject or os.environ.get('GOOGLE_ADMIN_SUBJECT'),
        'GOOGLE_CREDENTIALS_FILE': args.credentials_file or os.environ.get('GOOGLE_CREDENTIALS_FILE'),
        'GOOGLE_API_RATE_LIMIT': args.rate_limit,
    }

    missing_settings = []
    if not config['GOOGLE_ADMIN_DOMAIN']:
        missing_settings.append('Google Admin domain (--admin-domain or GOOGLE_ADMIN_DOMAIN)')
    if not config['GOOGLE_ADMIN_SUBJECT']:
        missing_settings.append('Google Admin subject (--admin-subject or GOOGLE_ADMIN_SUBJECT)')
    if not config['GOOGLE_CREDENTIALS_FILE']:
        missing_settings.append('Google credentials file (--credentials-file or GOOGLE_CREDENTIALS_FILE)')
    if missing_settings:
        logger.error(f"Missing required settings: {', '.join(missing_settings)}")
        sys.exit(1)

    logger.info(f"{'DRY RUN: ' if args.dry_run else ''}Syncing Chromebooks from {args.org_unit}")
    stats = sync_chromebooks_with_rt(
        config=config,
        dry_run=args.dry_run,
        org_unit_path=args.org_unit,
        max_results=args.max_results
    )

    print("\nSync Summary:")
    print(f"  Devices processed: {stats.get('total_devices', 0)}")
    print(f"  Matching assets found: {stats.get('matched_devices', 0)}")
    print(f"  Name updates: {stats.get('updated_device_names', 0)}")
    print(f"  User updates: {stats.get('updated_users', 0)}")
    print(f"  Errors encountered: {stats.get('errors', 0)}")
    print(f"  Skipped: {stats.get('skipped', 0)}")
    if args.dry_run:
        print("\nThis was a dry run. No changes were applied.")
        print("Use the same command without --dry-run to apply changes.")

if __name__ == "__main__":
    main()
