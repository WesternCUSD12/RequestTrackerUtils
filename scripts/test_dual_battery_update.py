#!/usr/bin/env python3
"""
Test script to update both battery fields for a single device.
"""
import sys
import logging
import os
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

def test_dual_battery_update():
    """Test updating both battery fields for a single device."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test data from our earlier GAM run
    serial = "PF3WKRFC"
    health_percentage = 92.4
    health_status = "BATTERY_HEALTH_NORMAL"
    
    # Use the raw GAM status (RT expects exact GAM values)
    battery_status = health_status  # Keep original: BATTERY_HEALTH_NORMAL
    percentage_str = str(health_percentage)  # Just the number, no % symbol
    
    logging.info(f"Test device {serial}:")
    logging.info(f"  Battery Health Status: {battery_status}")
    logging.info(f"  Current Battery Level: {percentage_str}")
    
    # RT API configuration
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }
    
    # Search for asset
    filter_data = [{"field": "CF.{Serial Number}", "operator": "=", "value": serial}]
    try:
        assets = search_assets(filter_data, config=config)
        logging.info(f"Found {len(assets)} assets for serial {serial}")
        
        if assets:
            asset = assets[0]
            asset_id = asset.get('id')
            logging.info(f"Asset ID: {asset_id}")
            
            # Update Battery Health Status with raw GAM value
            try:
                result1 = update_asset_custom_field(asset_id, "Battery Health Status", battery_status, config=config)
                logging.info(f"Battery Health Status update successful: {result1}")
            except Exception as e:
                logging.error(f"Battery Health Status update failed: {e}")
                return
                
            # Update Current Battery Level with percentage
            try:
                result2 = update_asset_custom_field(asset_id, "Current Battery Level", percentage_str, config=config)
                logging.info(f"Current Battery Level update successful: {result2}")
            except Exception as e:
                logging.error(f"Current Battery Level update failed: {e}")
                return
                
            logging.info("Both battery fields updated successfully!")
                
    except Exception as e:
        logging.error(f"Search failed: {e}")

if __name__ == '__main__':
    test_dual_battery_update()
