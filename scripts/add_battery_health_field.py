#!/usr/bin/env python3
"""
Script to add Battery Health custom field to RT assets.

Since Google Admin SDK API does not provide battery health data for Chromebooks,
this script creates a custom field in RT that can be manually updated during 
device check-ins or through other data collection methods.

Usage:
    python scripts/add_battery_health_field.py [--dry-run]
"""

import sys
import logging
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import RT API utilities
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import rt_api_request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_battery_health_custom_field(config=None, dry_run=False):
    """
    Create a Battery Health custom field in RT for Chromebook assets.
    
    Args:
        config (dict, optional): Configuration dictionary
        dry_run (bool): If True, don't actually create the field
        
    Returns:
        bool: True if successful, False otherwise
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
    
    # Custom field definition
    field_data = {
        'Name': 'Battery Health',
        'Type': 'Select',  # or 'Text' if you prefer free-form entry
        'Description': 'Battery health percentage for Chromebook devices',
        'LookupType': 'Assets',  # Apply to assets
        'ApplyTo': ['Asset'],
        'Values': [
            {'Name': 'Excellent (90-100%)', 'SortOrder': 1},
            {'Name': 'Good (80-89%)', 'SortOrder': 2},
            {'Name': 'Fair (70-79%)', 'SortOrder': 3},
            {'Name': 'Poor (60-69%)', 'SortOrder': 4},
            {'Name': 'Critical (<60%)', 'SortOrder': 5},
            {'Name': 'Unknown', 'SortOrder': 6}
        ]
    }
    
    if dry_run:
        logger.info("DRY RUN - Would create Battery Health custom field with data:")
        logger.info(f"  Name: {field_data['Name']}")
        logger.info(f"  Type: {field_data['Type']}")
        logger.info(f"  Description: {field_data['Description']}")
        logger.info(f"  Values: {[v['Name'] for v in field_data['Values']]}")
        return True
    
    try:
        # Create the custom field
        response = rt_api_request(
            endpoint='/customfields',
            method='POST',
            data=field_data,
            config=config
        )
        
        if response:
            logger.info("Successfully created Battery Health custom field")
            logger.info(f"Field ID: {response.get('id', 'Unknown')}")
            return True
        else:
            logger.error("Failed to create custom field - no response data")
            return False
            
    except Exception as e:
        logger.error(f"Error creating Battery Health custom field: {e}")
        return False

def update_asset_battery_health(asset_id, battery_health, config=None, dry_run=False):
    """
    Update battery health for a specific asset.
    
    Args:
        asset_id (str): The RT asset ID
        battery_health (str): Battery health value
        config (dict, optional): Configuration dictionary
        dry_run (bool): If True, don't actually update
        
    Returns:
        bool: True if successful, False otherwise
    """
    if config is None:
        config = {
            'RT_URL': RT_URL,
            'API_ENDPOINT': API_ENDPOINT,
            'RT_TOKEN': RT_TOKEN
        }
    
    if dry_run:
        logger.info(f"DRY RUN - Would update asset {asset_id} battery health to: {battery_health}")
        return True
    
    try:
        # Update the asset with battery health
        update_data = {
            'CF.{Battery Health}': battery_health
        }
        
        response = rt_api_request(
            endpoint=f'/assets/{asset_id}',
            method='PUT',
            data=update_data,
            config=config
        )
        
        if response:
            logger.info(f"Successfully updated battery health for asset {asset_id}")
            return True
        else:
            logger.error(f"Failed to update battery health for asset {asset_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating battery health for asset {asset_id}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Add Battery Health custom field to RT")
    parser.add_argument('--dry-run', action='store_true', help="Don't actually create the field")
    parser.add_argument('--test-asset', type=str, help="Test updating battery health for a specific asset ID")
    parser.add_argument('--test-value', type=str, default='Good (80-89%)', help="Battery health value for testing")
    args = parser.parse_args()

    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }

    logger.info(f"{'DRY RUN: ' if args.dry_run else ''}Creating Battery Health custom field in RT")
    
    # Create the custom field
    success = create_battery_health_custom_field(config=config, dry_run=args.dry_run)
    
    if success:
        print("\n✅ Battery Health custom field setup complete!")
        print("\nNext steps:")
        print("1. The field will be available in RT for asset records")
        print("2. You can manually update battery health during device check-ins")
        print("3. Consider integrating battery health collection into your check-in workflow")
        print("4. Monitor Google Admin SDK API updates for future battery health support")
        
        # Test updating an asset if requested
        if args.test_asset:
            logger.info(f"Testing battery health update for asset {args.test_asset}")
            test_success = update_asset_battery_health(
                asset_id=args.test_asset,
                battery_health=args.test_value,
                config=config,
                dry_run=args.dry_run
            )
            if test_success:
                print(f"\n✅ Test update successful for asset {args.test_asset}")
            else:
                print(f"\n❌ Test update failed for asset {args.test_asset}")
    else:
        print("\n❌ Failed to create Battery Health custom field")
        sys.exit(1)

if __name__ == "__main__":
    main()
