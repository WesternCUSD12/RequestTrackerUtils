#!/usr/bin/env python3
"""
Script to inspect RT asset custom fields.
"""
import sys
import logging
import os
from pathlib import Path

# Ensure RT utils are on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RT config first  
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import search_assets, rt_api_request

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

def inspect_asset_fields():
    """Inspect what custom fields exist on an RT asset."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    serial = "PF3WKRFC"
    
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
        
        if assets:
            asset = assets[0]
            asset_id = asset.get('id')
            
            print(f"Asset ID: {asset_id}")
            print(f"Asset Name: {asset.get('Name', 'N/A')}")
            print("\nAll Custom Fields:")
            
            # Print all custom fields
            for key, value in asset.items():
                if key.startswith('CF.'):
                    print(f"  {key}: {value}")
            
            # Also check what custom fields are available in the system
            print("\n" + "="*50)
            print("Checking available custom fields in RT...")
            
            try:
                cf_response = rt_api_request("GET", "/customfields", config=config)
                if cf_response and 'items' in cf_response:
                    print(f"\nFound {len(cf_response['items'])} custom fields:")
                    for cf in cf_response['items']:
                        cf_name = cf.get('Name', 'Unknown')
                        cf_type = cf.get('Type', 'Unknown')
                        cf_applies_to = cf.get('LookupType', 'Unknown')
                        print(f"  - {cf_name} (Type: {cf_type}, Applies to: {cf_applies_to})")
                        
                        # Check if this is our battery health field
                        if 'battery' in cf_name.lower() or 'health' in cf_name.lower():
                            print(f"    *** BATTERY FIELD FOUND: {cf_name} ***")
                            if 'Values' in cf:
                                print(f"    Allowed values: {[v.get('Name', str(v)) for v in cf.get('Values', [])]}")
                            
            except Exception as e:
                print(f"Error fetching custom fields: {e}")
                
    except Exception as e:
        logging.error(f"Search failed: {e}")

if __name__ == '__main__':
    inspect_asset_fields()
