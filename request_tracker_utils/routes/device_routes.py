from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from ..utils.rt_api import find_asset_by_name, get_assets_by_owner, fetch_asset_data
import logging
import urllib.parse
import requests
import json
import time

bp = Blueprint('devices', __name__)
logger = logging.getLogger(__name__)

@bp.route('/asset', strict_slashes=False)
def asset_checkin():
    """Display the device check-in form without a pre-filled asset name"""
    return render_template('device_checkin.html')

@bp.route('/asset/<asset_name>')
def asset_details(asset_name):
    """Display asset details and check-in form"""
    return render_template('device_checkin.html', asset_name=asset_name)

@bp.route('/api/asset/<asset_name>')
def get_asset_info(asset_name):
    """API endpoint to get asset and related devices info"""
    try:
        logger.info("\n")
        logger.info("==========================================")
        logger.info(f"Device Lookup - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Request for: {asset_name}")
        logger.info("==========================================")
        
        # Make request directly to RT API using asset name
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        token = current_app.config.get('RT_TOKEN')
        
        url = f"{base_url}{api_endpoint}/assets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # First try exact match using JSON filter format
        filter_data = [
            {
                "field": "Name",
                "operator": "=",
                "value": asset_name
            }
        ]
        
        logger.info(f"Making POST request with exact match filter: {json.dumps(filter_data)}")
        response = requests.post(url, headers=headers, json=filter_data)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        logger.info(f"POST exact match response: {json.dumps(result)}")
        
        # Look for assets in the response
        items = []
        if 'items' in result:
            items = result.get('items', [])
        elif 'assets' in result:
            items = result.get('assets', [])
            
        if items and len(items) > 0:
            logger.info(f"Found {len(items)} assets with exact match")
            matching_asset = items[0]  # Take the first match
        else:
            # If exact match fails, try LIKE match
            logger.info("No exact match found, trying LIKE operator")
            
            # Try with LIKE operator
            filter_data = [
                {
                    "field": "Name",
                    "operator": "LIKE",
                    "value": asset_name
                }
            ]
            
            logger.info(f"Making POST request with LIKE filter: {json.dumps(filter_data)}")
            response = requests.post(url, headers=headers, json=filter_data)
            response.raise_for_status()
            
            # Process the response
            result = response.json()
            
            # Look for assets in the response
            items = []
            if 'items' in result:
                items = result.get('items', [])
            elif 'assets' in result:
                items = result.get('assets', [])
            
            if not items:
                logger.warning(f"No asset found with name: {asset_name}")
                return jsonify({
                    "error": f"No asset found with name: {asset_name}",
                    "tip": "Check the asset name and try again"
                }), 404
                
            matching_asset = items[0]  # Take the first match
            
        # Get the complete asset data
        asset_id = matching_asset.get('id')
        logger.info(f"Fetching complete data for asset ID: {asset_id}")
        asset_data = fetch_asset_data(asset_id)

        # Print detailed device information to console
        logger.info(f"\n=== Device Details [{time.strftime('%H:%M:%S')}] ===")
        logger.info(f"Asset ID: {asset_data.get('id')}")
        logger.info(f"Asset Tag: {asset_data.get('Name')}")
        logger.info(f"Status: {asset_data.get('Status')}")
        
        # Print custom fields
        logger.info(f"\n=== Custom Fields [{time.strftime('%H:%M:%S')}] ===")
        for field in asset_data.get('CustomFields', []):
            field_name = field.get('name', 'Unknown')
            field_values = field.get('values', [])
            value = field_values[0] if field_values else 'N/A'
            logger.info(f"{field_name}: {value}")

        # Extract owner information
        owner_data = asset_data.get('Owner', {})
        owner_info = {
            'id': None,
            'name': None,
            'raw': owner_data
        }
        
        # Handle different Owner field formats
        if isinstance(owner_data, dict):
            owner_info['id'] = owner_data.get('id')
            owner_info['name'] = owner_data.get('Name', owner_data.get('id'))
        elif isinstance(owner_data, str):
            owner_info['id'] = owner_data
            owner_info['name'] = owner_data

        # Print owner information
        logger.info(f"\n=== Owner Information [{time.strftime('%H:%M:%S')}] ===")
        logger.info(f"Owner ID: {owner_info['id']}")
        logger.info(f"Owner Name: {owner_info['name']}")

        # Get other devices for this owner if we have one
        other_assets = []
        if owner_info['id']:
            logger.info(f"\n=== Other Devices for Owner {owner_info['id']} [{time.strftime('%H:%M:%S')}] ===")
            other_assets = get_assets_by_owner(owner_info['id'], exclude_id=asset_id)
            logger.info(f"Found {len(other_assets)} other assets")
            
            # Print summary of other devices
            for other_asset in other_assets:
                logger.info(f"- {other_asset.get('Name')} (ID: {other_asset.get('id')}, Status: {other_asset.get('Status')})")
            
            # Ensure custom fields are included in other assets
            for other_asset in other_assets:
                if 'id' in other_asset and 'CustomFields' not in other_asset:
                    try:
                        full_asset_data = fetch_asset_data(other_asset['id'])
                        other_asset.update(full_asset_data)
                    except Exception as e:
                        logger.error(f"Error fetching details for other asset {other_asset['id']}: {e}")

        logger.info("----------------------------------------\n")
        
        # Include the full asset data with prominent owner info
        return jsonify({
            "asset": asset_data,
            "owner": owner_info,
            "other_assets": other_assets
        })

    except Exception as e:
        logger.error(f"Error getting asset info: {e}")
        return jsonify({
            "error": "Failed to get asset information",
            "details": str(e)
        }), 500