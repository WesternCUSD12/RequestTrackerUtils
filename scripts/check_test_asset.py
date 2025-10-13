#!/usr/bin/env python3
"""
Check the custom field values for the TEST-0001 asset we just created.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from request_tracker_utils.utils.rt_api import rt_api_request
from request_tracker_utils.config import RT_URL, RT_TOKEN, API_ENDPOINT

def check_asset_fields():
    """Check the custom field values for TEST-0001."""
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT
    }
    
    print("Fetching TEST-0001 asset details...")
    print()
    
    # Search for the asset by name
    response = rt_api_request('GET', '/asset/2241', config=config)
    
    print("Asset Name:", response.get('Name'))
    print("Asset ID:", response.get('id'))
    print("Status:", response.get('Status'))
    print("Description:", response.get('Description'))
    print()
    print("=" * 80)
    print("Custom Fields:")
    print("=" * 80)
    
    for cf in response.get('CustomFields', []):
        cf_name = cf.get('name')
        cf_id = cf.get('id')
        cf_values = cf.get('values', [])
        
        print(f"\nField: {cf_name} (ID: {cf_id})")
        print(f"  Type: {cf.get('type')}")
        print(f"  Values: {cf_values}")
        
        if cf_values:
            print("  ✓ Has data")
        else:
            print("  ✗ Empty")

if __name__ == '__main__':
    check_asset_fields()
