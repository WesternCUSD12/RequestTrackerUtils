#!/usr/bin/env python3
"""
Test script to create an asset in the Student Devices catalog with all fields populated.
This helps troubleshoot asset creation issues.
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path so we can import from request_tracker_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from request_tracker_utils.utils.rt_api import rt_api_request
from request_tracker_utils.config import RT_URL, RT_TOKEN, API_ENDPOINT
from request_tracker_utils.utils.name_generator import InternalNameGenerator

def get_next_asset_tag():
    """Get the next asset tag from the sequence file."""
    from request_tracker_utils.routes.tag_routes import AssetTagManager
    
    # Create a minimal config dict
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT,
        'WORKING_DIR': os.getenv('WORKING_DIR', str(Path.home() / '.rtutils')),
        'PREFIX': os.getenv('PREFIX', 'W12-')
    }
    
    tag_manager = AssetTagManager(config)
    return tag_manager.get_next_tag(), tag_manager

def generate_internal_name():
    """Generate a unique internal name."""
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT,
        'WORKING_DIR': os.getenv('WORKING_DIR', str(Path.home() / '.rtutils'))
    }
    
    name_generator = InternalNameGenerator(config)
    return name_generator.generate_unique_name()

def test_create_asset():
    """Create a test asset in Student Devices catalog with all fields."""
    config = {
        'RT_URL': RT_URL,
        'RT_TOKEN': RT_TOKEN,
        'API_ENDPOINT': API_ENDPOINT
    }
    
    print("=" * 80)
    print("Test Asset Creation in Student Devices Catalog")
    print("=" * 80)
    print()
    
    # Use fixed test asset tag
    print("Step 1: Using test asset tag...")
    asset_tag = "TEST-0004"
    print(f"✓ Asset tag: {asset_tag}")
    print()
    
    # Generate internal name
    print("Step 2: Generating internal name...")
    try:
        internal_name = generate_internal_name()
        print(f"✓ Generated internal name: {internal_name}")
    except Exception as e:
        print(f"✗ Failed to generate internal name: {e}")
        return False
    print()
    
    # Create test asset data - start with basic fields only
    print("Step 3: Preparing asset data...")
    asset_data = {
        'Name': asset_tag,
        'Catalog': 'Student Devices',
        'Description': f'Test asset {asset_tag} - {internal_name} - Full field test'
    }
    
    print("Asset data to be created:")
    print(json.dumps(asset_data, indent=2))
    print()
    
    # Create the asset
    print("Step 4: Creating asset in RT...")
    try:
        response = rt_api_request('POST', '/asset', data=asset_data, config=config)
        asset_id = response.get('id')
        print(f"✓ Asset created successfully!")
        print(f"  Asset ID: {asset_id}")
        print(f"  Asset Tag: {asset_tag}")
        print(f"  Internal Name: {internal_name}")
        print(f"  Label URL: {config['RT_URL']}/labels/print?assetId={asset_id}")
        print()
        
        # Now update with custom fields
        # Per RT API docs: CustomFields should be an object with field names as keys
        # Single-value fields get string values, multi-value fields get arrays
        print("Step 4b: Updating custom fields...")
        custom_fields_data = {
            'CustomFields': {
                'Serial Number': f'TEST-SERIAL-{asset_tag}',
                'Manufacturer': 'Apple',
                'Model': 'Test MacBook Air',
                'Internal Name': internal_name,
                'Type': 'Chromebook',  # This is the actual field name (not 'Category')
                'Funding Source': 'General Fund'
            }
        }
        
        update_response = rt_api_request('PUT', f'/asset/{asset_id}', data=custom_fields_data, config=config)
        print("✓ Custom fields updated successfully")
        print()
        
    except Exception as e:
        print(f"✗ Failed to create asset: {e}")
        print()
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())
        return False
    
    # Verify the asset was created
    print("Step 5: Verifying asset creation...")
    try:
        verify_response = rt_api_request('GET', f'/asset/{asset_id}', config=config)
        print(f"✓ Asset verified in RT")
        print()
        print("Asset details:")
        print(json.dumps(verify_response, indent=2, default=str))
        print()
    except Exception as e:
        print(f"⚠ Warning: Could not verify asset: {e}")
        print()
    
    print("=" * 80)
    print("Test completed successfully!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    try:
        success = test_create_asset()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
