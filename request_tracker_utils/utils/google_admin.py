#!/usr/bin/env python3
"""
Google Admin API utility functions for interacting with Google Workspace Admin Console.
Provides functionality for managing Chromebook devices.
"""
import os
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import googleapiclient.discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

# Configure logging
logger = logging.getLogger(__name__)

# Define explicitly which functions can be imported from this module
__all__ = [
    'get_google_admin_service',
    'list_chromebook_devices',
    'get_chromebook_device',
    'update_chromebook_device',
    'update_annotated_user',
    'update_device_name',
    'batch_update_chromebooks',
    'list_organizational_units',
    'find_chromebook_by_serial_number'
]

# Constants
# Use 'my_customer' as recommended by Google for customerId
# Note: Battery health data is not currently available in Google Admin SDK API
# Monitor API updates at: https://developers.google.com/admin-sdk/directory/reference/rest/v1/chromeosdevices
CHROMEOS_DEVICE_FIELDS = 'deviceId,serialNumber,macAddress,status,lastSync,model,orgUnitPath,annotatedUser,annotatedAssetId'

# Extended fields for hardware monitoring (when using FULL projection)
# These fields contain CPU, RAM, and disk data but NO battery information
CHROMEOS_HARDWARE_FIELDS = (
    'deviceId,serialNumber,macAddress,status,lastSync,model,orgUnitPath,'
    'annotatedUser,annotatedAssetId,cpuStatusReports,systemRamTotal,'
    'systemRamFreeReports,diskVolumeReports,cpuInfo,fanInfo,backlightInfo'
)

DEFAULT_SCOPES = ['https://www.googleapis.com/auth/admin.directory.device.chromeos']

def get_google_admin_service(config: Optional[Dict] = None, scopes: Optional[List[str]] = None):
    """
    Create and return an authenticated Google Admin Directory API service.
    
    Args:
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
        scopes (List[str], optional): List of API scopes to request access to.
                               Defaults to DEFAULT_SCOPES if None.
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated Google Admin SDK Directory service
        
    Raises:
        FileNotFoundError: If the service account credentials file doesn't exist
        ValueError: If required configuration is missing
    """
    if config is None:
        # Use Flask app config if available
        try:
            from flask import current_app
            config = current_app.config
            logger.debug("Using Flask app config for Google Admin API")
        except (ImportError, RuntimeError):
            logger.warning("Flask app context not available, using environment variables")
            # Fall back to environment variables if no config provided
            config = {
                'GOOGLE_ADMIN_DOMAIN': os.environ.get('GOOGLE_ADMIN_DOMAIN'),
                'GOOGLE_ADMIN_SUBJECT': os.environ.get('GOOGLE_ADMIN_SUBJECT'),
                'GOOGLE_CREDENTIALS_FILE': os.environ.get('GOOGLE_CREDENTIALS_FILE')
            }
    
    # Use provided scopes or default ones
    if scopes is None:
        scopes = DEFAULT_SCOPES
    
    # Validate required configuration
    credentials_file = config.get('GOOGLE_CREDENTIALS_FILE')
    admin_domain = config.get('GOOGLE_ADMIN_DOMAIN')
    admin_subject = config.get('GOOGLE_ADMIN_SUBJECT')
    
    if not credentials_file:
        raise ValueError("Google Admin API credentials file path not provided in config")
    if not admin_domain:
        raise ValueError("Google Admin domain not provided in config")
    if not admin_subject:
        raise ValueError("Google Admin subject (delegate email) not provided in config")
    
    # Check if credentials file exists
    credentials_path = Path(credentials_file)
    if not credentials_path.exists():
        raise FileNotFoundError(f"Google Admin API credentials file not found at {credentials_file}")
    
    try:
        # Load credentials from service account file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=scopes,
            subject=admin_subject  # Delegate authority to admin user
        )
        
        # Build and return the service
        service = googleapiclient.discovery.build(
            'admin', 'directory_v1', credentials=credentials, cache_discovery=False
        )
        
        logger.debug(f"Successfully created Google Admin API service for domain {admin_domain}")
        return service
        
    except Exception as e:
        logger.error(f"Failed to create Google Admin API service: {str(e)}")
        raise

def list_chromebook_devices(
    org_unit_path: str = '/',
    max_results: int = 200,
    query: Optional[str] = None,
    config: Optional[Dict] = None
) -> List[Dict[str, Any]]:
    """
    List Chromebook devices in the Google Workspace domain.
    
    Args:
        org_unit_path (str, optional): The organizational unit path to list devices from.
                                     Defaults to '/' (root).
        max_results (int, optional): Maximum number of results to return.
                                   Defaults to 200.
        query (str, optional): Search query filter in the format supported by the Admin SDK.
                             (e.g., "status:ACTIVE")
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        List[Dict[str, Any]]: List of Chromebook devices
        
    Raises:
        Exception: If there's an error listing the devices
    """
    if config is None:
        try:
            from flask import current_app
            config = current_app.config
        except (ImportError, RuntimeError):
            config = {}
    
    admin_domain = config.get('GOOGLE_ADMIN_DOMAIN', os.environ.get('GOOGLE_ADMIN_DOMAIN'))
    if not admin_domain:
        raise ValueError("Google Admin domain not provided in config")
    
    try:
        # Get authenticated service
        service = get_google_admin_service(config)
        
        # Initialize result storage
        all_devices = []
        page_token = None
        
        # Loop to handle pagination
        while True:
            request = service.chromeosdevices().list(
                customerId='my_customer',  # Use 'my_customer' for all API calls
                orgUnitPath=org_unit_path,
                maxResults=min(max_results, 200),  # API limit is 200 per page
                pageToken=page_token,
                query=query,
                projection='FULL',
                fields=f'nextPageToken,chromeosdevices({CHROMEOS_DEVICE_FIELDS})'
            )
            response = request.execute()
            devices = response.get('chromeosdevices', [])
            all_devices.extend(devices)
            
            # Log progress
            logger.info(f"Retrieved {len(devices)} Chromebook devices (total: {len(all_devices)})")
            
            # Check if we need to get another page of results
            page_token = response.get('nextPageToken')
            if not page_token or len(all_devices) >= max_results:
                break
        
        logger.info(f"Successfully retrieved {len(all_devices)} Chromebook devices")
        return all_devices
        
    except HttpError as e:
        logger.error(f"Google API HTTP Error listing Chromebook devices: {e}")
        raise Exception(f"Failed to list Chromebook devices: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing Chromebook devices: {str(e)}")
        raise Exception(f"Unexpected error listing Chromebook devices: {str(e)}")

def get_chromebook_device(
    device_id: str,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Get a specific Chromebook device by ID.
    
    Args:
        device_id (str): The device ID of the Chromebook to retrieve.
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        Dict[str, Any]: The Chromebook device details
        
    Raises:
        Exception: If there's an error retrieving the device
    """
    if config is None:
        try:
            from flask import current_app
            config = current_app.config
        except (ImportError, RuntimeError):
            config = {}
    
    admin_domain = config.get('GOOGLE_ADMIN_DOMAIN', os.environ.get('GOOGLE_ADMIN_DOMAIN'))
    if not admin_domain:
        raise ValueError("Google Admin domain not provided in config")
    
    try:
        # Get authenticated service
        service = get_google_admin_service(config)
        
        # Get the device
        request = service.chromeosdevices().get(
            customerId='my_customer',  # Use 'my_customer' for all API calls
            deviceId=device_id,
            projection='FULL',
            fields=CHROMEOS_DEVICE_FIELDS
        )
        response = request.execute()
        logger.info(f"Successfully retrieved Chromebook device: {device_id}")
        return response
        
    except HttpError as e:
        logger.error(f"Google API HTTP Error getting Chromebook device {device_id}: {e}")
        raise Exception(f"Failed to get Chromebook device: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting Chromebook device {device_id}: {str(e)}")
        raise Exception(f"Unexpected error getting Chromebook device: {str(e)}")

def update_chromebook_device(
    device_id: str,
    update_data: Dict[str, Any],
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Update a Chromebook device with the provided data.
    
    Args:
        device_id (str): The device ID of the Chromebook to update.
        update_data (Dict[str, Any]): The data to update on the device.
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        Dict[str, Any]: The updated Chromebook device details
        
    Raises:
        Exception: If there's an error updating the device
    """
    if config is None:
        try:
            from flask import current_app
            config = current_app.config
        except (ImportError, RuntimeError):
            config = {}
    
    admin_domain = config.get('GOOGLE_ADMIN_DOMAIN', os.environ.get('GOOGLE_ADMIN_DOMAIN'))
    if not admin_domain:
        raise ValueError("Google Admin domain not provided in config")
    
    try:
        # Get authenticated service
        service = get_google_admin_service(config)
        
        # Update the device
        request = service.chromeosdevices().update(
            customerId='my_customer',  # Use 'my_customer' for all API calls
            deviceId=device_id,
            body=update_data
        )
        
        response = request.execute()
        logger.info(f"Successfully updated Chromebook device: {device_id}")
        return response
        
    except HttpError as e:
        logger.error(f"Google API HTTP Error updating Chromebook device {device_id}: {e}")
        raise Exception(f"Failed to update Chromebook device: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating Chromebook device {device_id}: {str(e)}")
        raise Exception(f"Unexpected error updating Chromebook device: {str(e)}")

def update_annotated_user(
    device_id: str,
    annotated_user: str,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Update the annotated user for a Chromebook device.
    
    Args:
        device_id (str): The device ID of the Chromebook to update.
        annotated_user (str): The new annotated user value.
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        Dict[str, Any]: The updated Chromebook device details
        
    Raises:
        Exception: If there's an error updating the device
    """
    update_data = {
        "annotatedUser": annotated_user
    }
    
    return update_chromebook_device(device_id, update_data, config)

def update_device_name(
    device_id: str,
    device_name: str,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Update the device name (annotatedAssetId) for a Chromebook device.
    
    Args:
        device_id (str): The device ID of the Chromebook to update.
        device_name (str): The new device name value.
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        Dict[str, Any]: The updated Chromebook device details
        
    Raises:
        Exception: If there's an error updating the device
    """
    update_data = {
        "annotatedAssetId": device_name
    }
    
    return update_chromebook_device(device_id, update_data, config)

def batch_update_chromebooks(
    updates: List[Dict[str, Any]],
    config: Optional[Dict] = None,
    rate_limit: float = 0.5,
    max_retries: int = 3
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Update multiple Chromebook devices in a batch, with rate limiting and retries.
    
    Args:
        updates (List[Dict[str, Any]]): List of updates to apply.
                                        Each update is a dict with 'device_id' and 'update_data' keys.
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
        rate_limit (float): Delay in seconds between API calls. Defaults to 0.5.
        max_retries (int): Maximum number of retry attempts per device. Defaults to 3.
                               
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 
            Tuple containing (successful updates, failed updates)
        
    Example:
        updates = [
            {
                'device_id': '123abc',
                'update_data': {'annotatedUser': 'user@example.com', 'annotatedAssetId': 'CB-123'}
            },
            {
                'device_id': '456def',
                'update_data': {'annotatedUser': 'user2@example.com'}
            }
        ]
        successful, failed = batch_update_chromebooks(updates)
    """
    if config is None:
        try:
            from flask import current_app
            config = current_app.config
        except (ImportError, RuntimeError):
            config = {}
    
    successful_updates = []
    failed_updates = []
    
    for update in updates:
        device_id = update.get('device_id')
        update_data = update.get('update_data', {})
        
        if not device_id or not update_data:
            failed_updates.append({
                'device_id': device_id,
                'update_data': update_data,
                'error': 'Missing device_id or update_data'
            })
            continue
        
        # Try to update with retries
        retries = 0
        success = False
        last_error = None
        
        while retries < max_retries and not success:
            try:
                # Add delay for rate limiting (skip on first attempt)
                if retries > 0:
                    time.sleep(rate_limit * (1 + retries))
                    logger.info(f"Retry {retries} for device {device_id}")
                
                result = update_chromebook_device(device_id, update_data, config)
                successful_updates.append({
                    'device_id': device_id,
                    'update_data': update_data,
                    'result': result
                })
                success = True
                
            except Exception as e:
                last_error = str(e)
                retries += 1
                logger.warning(f"Failed to update device {device_id} (attempt {retries}): {last_error}")
        
        # If all retries failed, add to failed list
        if not success:
            failed_updates.append({
                'device_id': device_id,
                'update_data': update_data,
                'error': last_error
            })
        
        # Add rate limiting delay between devices
        time.sleep(rate_limit)
    
    # Log summary
    logger.info(f"Batch update complete: {len(successful_updates)} successful, {len(failed_updates)} failed")
    return successful_updates, failed_updates

def list_organizational_units(config: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    List all organizational units in the Google Workspace domain.
    
    Args:
        config (Dict, optional): Configuration dictionary with Google Admin settings.
                               Defaults to current_app.config if None.
                               
    Returns:
        List[Dict[str, Any]]: List of organizational units
    """
    if config is None:
        try:
            from flask import current_app
            config = current_app.config
        except (ImportError, RuntimeError):
            config = {}
    
    admin_domain = config.get('GOOGLE_ADMIN_DOMAIN', os.environ.get('GOOGLE_ADMIN_DOMAIN'))
    if not admin_domain:
        raise ValueError("Google Admin domain not provided in config")
    
    try:
        # Get authenticated service
        service = get_google_admin_service(config)
        
        # List OUs
        request = service.orgunits().list(
            customerId='my_customer',  # Use 'my_customer' for all API calls
            type='ALL'
        )
        
        response = request.execute()
        org_units = response.get('organizationUnits', [])
        
        logger.info(f"Successfully retrieved {len(org_units)} organizational units")
        return org_units
        
    except HttpError as e:
        logger.error(f"Google API HTTP Error listing organizational units: {e}")
        raise Exception(f"Failed to list organizational units: {str(e)}")
    except Exception as e:
        logger.error(f"Error listing organizational units: {str(e)}")
        raise Exception(f"Unexpected error listing organizational units: {str(e)}")

def find_chromebook_by_serial_number(
    serial_number: str,
    config: Optional[Dict] = None
) -> Optional[Dict[str, Any]]:
    """
    Find a Chromebook device by its serial number.

    Args:
        serial_number (str): The serial number to search for.
        config (Dict, optional): Configuration dictionary with Google Admin settings.

    Returns:
        Dict[str, Any] or None: The Chromebook device details if found, else None.
    """
    query = f'serialNumber:{serial_number}'
    devices = list_chromebook_devices(query=query, max_results=1, config=config)
    if devices:
        return devices[0]
    return None

def check_for_battery_fields(device_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if battery-related fields are present in device data.
    This function can help detect when Google adds battery health to the API.
    
    Args:
        device_data: ChromeOS device data from API
        
    Returns:
        Dict containing any battery-related fields found
    """
    battery_keywords = ['battery', 'power', 'charge', 'energy']
    battery_fields = {}
    
    for key, value in device_data.items():
        if any(keyword in key.lower() for keyword in battery_keywords):
            battery_fields[key] = value
    
    if battery_fields:
        logger.info(f"Battery-related fields detected: {list(battery_fields.keys())}")
    
    return battery_fields

if __name__ == "__main__":
    # Simple test if run as a script
    import sys
    import argparse
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Google Admin API utilities test")
    parser.add_argument("--list-devices", action="store_true", help="List Chromebook devices")
    parser.add_argument("--list-ous", action="store_true", help="List organizational units")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results")
    parser.add_argument("--ou", type=str, default="/", help="Organizational unit path")
    
    args = parser.parse_args()
    
    try:
        if args.list_devices:
            devices = list_chromebook_devices(org_unit_path=args.ou, max_results=args.max_results)
            print(f"Found {len(devices)} devices:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device.get('serialNumber')} - {device.get('annotatedUser', 'No user')} - {device.get('annotatedAssetId', 'No asset ID')}")
                
        elif args.list_ous:
            ous = list_organizational_units()
            print(f"Found {len(ous)} organizational units:")
            for i, ou in enumerate(ous):
                print(f"{i+1}. {ou.get('name')} - {ou.get('orgUnitPath')}")
        
        else:
            print("No action specified. Use --list-devices or --list-ous")
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
