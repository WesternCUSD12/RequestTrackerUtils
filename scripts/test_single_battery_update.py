#!/usr/bin/env python3
"""
Test script to update just one device's battery health in RT.
"""
import csv
import subprocess
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

def categorize_battery_health(health_percentage, health_status):
    """Categorize battery health percentage into RT custom field values."""
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
        return "Good (80-89%)"  
    else:
        return "Unknown"

def test_single_device():
    """Test updating battery health for a single device."""
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Test data from our earlier run
    serial = "PF3WKRFC"
    full_charge_capacity = 3451
    design_capacity = 3735
    health_status = "BATTERY_HEALTH_NORMAL"
    cycle_count = 70
    
    # Calculate health percentage
    health_percentage = round((full_charge_capacity / design_capacity) * 100, 1)
    health_category = categorize_battery_health(health_percentage, health_status)
    
    logging.info(f"Test device {serial}: {health_percentage}% -> {health_category}")
    
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
            
            # Try to update battery health
            field_name = "Battery Health"
            logging.info(f"Attempting to update {field_name} to: {health_category}")
            
            try:
                result = update_asset_custom_field(asset_id, field_name, health_category, config=config)
                logging.info(f"Update successful: {result}")
            except Exception as e:
                logging.error(f"Update failed: {e}")
                logging.error(f"Exception type: {type(e)}")
                
    except Exception as e:
        logging.error(f"Search failed: {e}")

if __name__ == '__main__':
    test_single_device()
