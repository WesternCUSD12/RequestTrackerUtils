#!/usr/bin/env python3
"""
Script to inspect an RT asset and its custom fields.
"""
import sys
import logging
import os
from pathlib import Path

# Ensure RT utils are on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RT config first  
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import search_assets, fetch_asset_data

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

def inspect_asset():
    """Inspect asset custom fields."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # RT API configuration
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }
    
    # Search for our test asset
    serial = "PF3WKRFC"
    filter_data = [{"field": "CF.{Serial Number}", "operator": "=", "value": serial}]
    
    try:
        assets = search_assets(filter_data, config=config)
        if assets:
            asset = assets[0]
            asset_id = asset.get('id')
            print(f"\nAsset ID: {asset_id}")
            print(f"Asset Name: {asset.get('Name', 'N/A')}")
            
            # Fetch full asset details
            full_asset = fetch_asset_data(asset_id, config=config)
            
            print("\n=== CUSTOM FIELDS ===")
            custom_fields = full_asset.get('CustomFields', [])
            print(f"Custom fields type: {type(custom_fields)}")
            
            if isinstance(custom_fields, list):
                print("Custom fields is a list:")
                for i, field_item in enumerate(custom_fields):
                    print(f"  [{i}] {field_item}")
                    if isinstance(field_item, dict):
                        field_name = field_item.get('name', 'Unknown')
                        field_values = field_item.get('values', [])
                        print(f"    Field Name: {field_name}")
                        print(f"    Values: {field_values}")
                        print()
            elif isinstance(custom_fields, dict):
                print("Custom fields is a dictionary:")
                for field_name, field_data in custom_fields.items():
                    print(f"Field: {field_name}")
                    if isinstance(field_data, dict):
                        print(f"  Values: {field_data.get('values', [])}")
                        print(f"  Type: {field_data.get('type', 'unknown')}")
                    else:
                        print(f"  Value: {field_data}")
                    print()
            else:
                print(f"Custom fields is unexpected type: {type(custom_fields)}")
                print(f"Content: {custom_fields}")
                
            # Look specifically for battery health related fields
            print("\n=== BATTERY HEALTH FIELDS ===")
            battery_fields = []
            if isinstance(custom_fields, list):
                battery_fields = [field for field in custom_fields 
                                if isinstance(field, dict) and 
                                ('battery' in field.get('name', '').lower() or 'health' in field.get('name', '').lower())]
                for field in battery_fields:
                    print(f"Found battery field: {field.get('name', 'Unknown')}")
                    print(f"  Current values: {field.get('values', [])}")
            elif isinstance(custom_fields, dict):
                battery_fields = [name for name in custom_fields.keys() if 'battery' in name.lower() or 'health' in name.lower()]
                for field_name in battery_fields:
                    print(f"Found battery field: {field_name}")
                    field_data = custom_fields[field_name]
                    if isinstance(field_data, dict):
                        print(f"  Current values: {field_data.get('values', [])}")
                    else:
                        print(f"  Current value: {field_data}")
            
            if not battery_fields:
                print("No battery health fields found")
                
            print("\n=== ALL FIELDS (for debugging) ===")
            for key, value in full_asset.items():
                if key != 'CustomFields':  # Skip custom fields as we already printed them
                    print(f"{key}: {value}")
                    
        else:
            print(f"No asset found with serial {serial}")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    inspect_asset()
