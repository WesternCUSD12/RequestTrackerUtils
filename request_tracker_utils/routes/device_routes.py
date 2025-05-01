from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from ..utils.rt_api import find_asset_by_name, get_assets_by_owner, fetch_asset_data, fetch_user_data
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

        # Extract owner information and log it
        owner_data = asset_data.get('Owner', {})
        logger.info(f"\n=== Owner Information ===")
        logger.info(f"Raw owner data: {json.dumps(owner_data, indent=2)}")
        
        owner_info = {
            'id': None,
            'name': None,
            'raw': owner_data,
            'display_name': None,
            'numeric_id': None  # Add field for numeric ID
        }
        
        # Handle different Owner field formats and fetch user details
        if isinstance(owner_data, dict):
            owner_id = owner_data.get('id')
            logger.info(f"Owner ID from dict: {owner_id}")
            owner_info['id'] = owner_id
            try:
                # Fetch full user details
                logger.info(f"Fetching user details for ID: {owner_id}")
                user_data = fetch_user_data(owner_id)
                logger.info(f"User data retrieved: {json.dumps(user_data, indent=2)}")
                owner_info['name'] = owner_data.get('Name', owner_data.get('id'))
                owner_info['display_name'] = user_data.get('RealName', user_data.get('Name', owner_info['id']))
                
                # Extract numeric ID from hyperlinks
                hyperlinks = user_data.get('_hyperlinks', [])
                for link in hyperlinks:
                    if link.get('ref') == 'self' and link.get('type') == 'user':
                        owner_info['numeric_id'] = str(link.get('id'))
                        logger.info(f"Found numeric user ID: {owner_info['numeric_id']}")
                        break
                
            except Exception as e:
                logger.error(f"Error fetching user details: {e}")
                owner_info['name'] = owner_data.get('id')
                owner_info['display_name'] = owner_data.get('id')
        elif isinstance(owner_data, str):
            owner_info['id'] = owner_data
            try:
                # Fetch full user details
                logger.info(f"Fetching user details for ID: {owner_data}")
                user_data = fetch_user_data(owner_data)
                logger.info(f"User data retrieved: {json.dumps(user_data, indent=2)}")
                owner_info['name'] = owner_data
                owner_info['display_name'] = user_data.get('RealName', user_data.get('Name', owner_data))
                
                # Extract numeric ID from hyperlinks
                hyperlinks = user_data.get('_hyperlinks', [])
                for link in hyperlinks:
                    if link.get('ref') == 'self' and link.get('type') == 'user':
                        owner_info['numeric_id'] = str(link.get('id'))
                        logger.info(f"Found numeric user ID: {owner_info['numeric_id']}")
                        break
                
            except Exception as e:
                logger.error(f"Error fetching user details: {e}")
                owner_info['name'] = owner_data
                owner_info['display_name'] = owner_data

        logger.info(f"Final owner_info: {json.dumps(owner_info, indent=2)}")

        # Print owner information
        logger.info(f"\n=== Owner Information [{time.strftime('%H:%M:%S')}] ===")
        logger.info(f"Owner ID: {owner_info['id']}")
        logger.info(f"Owner Name: {owner_info['display_name']}")
        logger.info(f"Owner Numeric ID: {owner_info['numeric_id']}")

        # Get other devices for this owner if we have one
        other_assets = []
        if owner_info['numeric_id']:  # Use numeric_id instead of id
            logger.info(f"\n=== Looking up other assets for owner {owner_info['numeric_id']} ===")
            try:
                other_assets = get_assets_by_owner(owner_info['numeric_id'], exclude_id=asset_id)
                logger.info(f"Found {len(other_assets)} other assets")
                
                # Log details about each asset found
                for asset in other_assets:
                    logger.info(f"Other asset found:")
                    logger.info(f"  ID: {asset.get('id')}")
                    logger.info(f"  Name: {asset.get('Name')}")
                    logger.info(f"  Status: {asset.get('Status')}")
                    logger.info(f"  Type: {next((cf['values'][0] for cf in asset.get('CustomFields', []) if cf['name'] == 'Type'), 'N/A')}")
                
            except Exception as e:
                logger.error(f"Error getting other assets: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
            # Ensure custom fields are included in other assets
            for other_asset in other_assets:
                if 'id' in other_asset and 'CustomFields' not in other_asset:
                    try:
                        logger.info(f"Fetching full details for other asset {other_asset['id']}")
                        full_asset_data = fetch_asset_data(other_asset['id'])
                        other_asset.update(full_asset_data)
                        logger.info(f"Successfully updated other asset {other_asset['id']} with full details")
                    except Exception as e:
                        logger.error(f"Error fetching details for other asset {other_asset['id']}: {e}")
        else:
            logger.warning("No owner ID available to lookup other assets")

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