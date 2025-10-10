#!/usr/bin/env python3
"""
Try different approaches to creating an asset with custom fields.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from request_tracker_utils.utils.rt_api import rt_api_request
from request_tracker_utils.config import RT_URL, RT_TOKEN, API_ENDPOINT

def test_minimal_asset():
    """Create a minimal test asset to see if basic creation works."""
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT
    }
    
    print("Test 1: Create minimal asset (Name + Catalog only)")
    print("=" * 60)
    
    asset_data = {
        'Name': 'TEST-0002',
        'Catalog': 'Student Devices'
    }
    
    print(f"Data: {asset_data}")
    try:
        response = rt_api_request('POST', '/asset', data=asset_data, config=config)
        print(f"✓ SUCCESS! Asset ID: {response.get('id')}")
        return response.get('id')
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return None

if __name__ == '__main__':
    asset_id = test_minimal_asset()
    if asset_id:
        print(f"\nAsset {asset_id} created successfully!")
        print("Now let's try updating it with custom fields...")
