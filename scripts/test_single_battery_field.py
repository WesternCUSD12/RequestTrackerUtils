#!/usr/bin/env python3
"""
Test updating a single battery field to isolate RT API issues
"""

import sys
import os
import logging
# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from request_tracker_utils.utils.rt_api import update_asset_custom_field
from request_tracker_utils.utils.asset_search import search_assets

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_single_field():
    """Test updating just the Current Battery Level field"""
    # Test data - using simple numeric value
    serial = "PF3WKRFC"
    percentage_value = "92.4"  # Just digits and a dot

    logging.info("Testing Current Battery Level field update")
    logging.info(f"Device: {serial}")
    logging.info(f"Value: '{percentage_value}'")

    # RT API configuration
    config = {
        'rt_url': 'https://tickets.wc-12.com/REST/2.0/',
        'username': 'jmartin',
        'password': 'SinSaVer2022!'
    }

    try:
        # Find the asset
        assets = search_assets([{'field': 'CF.{Serial Number}', 'operator': '=', 'value': serial}], config=config)
        logging.info(f"Found {len(assets)} assets for serial {serial}")

        if assets:
            asset = assets[0]
            asset_id = asset.get('id')
            logging.info(f"Asset ID: {asset_id}")

            # Test Current Battery Level field only
            try:
                logging.info(f"Updating 'Current Battery Level' with value: '{percentage_value}'")
                result = update_asset_custom_field(asset_id, "Current Battery Level", percentage_value, config=config)
                logging.info(f"Update successful: {result}")
            except Exception as e:
                logging.error(f"Update failed: {e}")

                # Try with an even simpler value
                simple_value = "92"
                logging.info(f"Trying simpler value: '{simple_value}'")
                try:
                    result = update_asset_custom_field(asset_id, "Current Battery Level", simple_value, config=config)
                    logging.info(f"Simple value update successful: {result}")
                except Exception as e2:
                    logging.error(f"Simple value update also failed: {e2}")

    except Exception as e:
        logging.error(f"Asset search failed: {e}")

if __name__ == '__main__':
    test_single_field()
