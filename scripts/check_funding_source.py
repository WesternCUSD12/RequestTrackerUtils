#!/usr/bin/env python3
"""
Check and update Funding Source field on TEST-0003
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from request_tracker_utils.utils.rt_api import rt_api_request
from request_tracker_utils.config import RT_URL, RT_TOKEN, API_ENDPOINT

def check_funding_source():
    """Check the Funding Source custom field on TEST-0003."""
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT
    }
    
    asset_id = 2243  # TEST-0003
    
    print("Fetching TEST-0003 asset details...")
    response = rt_api_request('GET', f'/asset/{asset_id}', config=config)
    
    print("\nSearching for Funding Source field...")
    found = False
    for cf in response.get('CustomFields', []):
        if cf.get('id') == '3' or 'Funding' in cf.get('name', ''):
            print(f"\nFound: {cf.get('name')} (ID: {cf.get('id')})")
            print(f"  Current values: {cf.get('values', [])}")
            found = True
    
    if not found:
        print("❌ Funding Source field (ID 3) not found in CustomFields list")
        print("\nAll custom fields on this asset:")
        for cf in response.get('CustomFields', []):
            print(f"  - {cf.get('name')} (ID: {cf.get('id')}): {cf.get('values', [])}")
    
    # Try to get the custom field definition
    print("\n" + "="*60)
    print("Fetching Funding Source custom field definition (ID 3)...")
    try:
        cf_detail = rt_api_request('GET', '/customfield/3', config=config)
        print(f"\nField Name: {cf_detail.get('Name')}")
        print(f"Field Type: {cf_detail.get('Type')}")
        print(f"Description: {cf_detail.get('Description', 'N/A')}")
        
        # Get valid values if it's a Select or Combobox field
        if cf_detail.get('Type') in ['Select', 'Combobox']:
            print(f"\nValid values for this field:")
            if cf_detail.get('Type') == 'Select':
                values = cf_detail.get('Values', [])
                for v in values:
                    print(f"  - {v.get('name', v)}")
            else:
                try:
                    values_response = rt_api_request('GET', '/customfield/3/values', config=config)
                    for v in values_response.get('items', []):
                        print(f"  - {v.get('name', v)}")
                except:
                    print("  (Could not fetch values)")
    except Exception as e:
        print(f"❌ Error fetching field definition: {e}")
    
    # Now try to update it
    print("\n" + "="*60)
    print("Attempting to set Funding Source to 'General Fund'...")
    try:
        update_data = {
            'CustomFields': {
                'Funding Source': 'General Fund'
            }
        }
        rt_api_request('PUT', f'/asset/{asset_id}', data=update_data, config=config)
        print("✅ Update request sent successfully")
        
        # Verify
        print("\nVerifying update...")
        response = rt_api_request('GET', f'/asset/{asset_id}', config=config)
        for cf in response.get('CustomFields', []):
            if cf.get('id') == '3' or 'Funding' in cf.get('name', ''):
                print(f"✅ {cf.get('name')}: {cf.get('values', [])}")
                
    except Exception as e:
        print(f"❌ Error updating field: {e}")

if __name__ == '__main__':
    check_funding_source()
