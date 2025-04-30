from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from ..utils.rt_api import find_asset_by_name, get_assets_by_owner, fetch_asset_data
import logging

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
        # Find the asset by name
        asset = find_asset_by_name(asset_name)
        if not asset:
            return jsonify({
                "error": f"No asset found with name: {asset_name}",
                "tip": "Check the asset name and try again"
            }), 404

        # Get the complete asset data
        asset_id = asset.get('id')
        asset_data = fetch_asset_data(asset_id)

        # Extract owner based on the RT API response format
        owner_data = asset_data.get('Owner', {})
        owner_name = None
        
        # Handle different Owner field formats
        if isinstance(owner_data, dict):
            # Handle Owner as object with id/name fields
            owner_name = owner_data.get('id')  # Use id field as it's more reliable
        elif isinstance(owner_data, str):
            # Handle Owner as simple string
            owner_name = owner_data

        # Get other devices for this owner if we have one
        other_assets = []
        if owner_name:
            logger.info(f"Looking up other assets for owner: {owner_name}")
            other_assets = get_assets_by_owner(owner_name, exclude_id=asset_id)
            logger.info(f"Found {len(other_assets)} other assets for owner {owner_name}")
        
        return jsonify({
            "asset": asset_data,
            "other_assets": other_assets
        })

    except Exception as e:
        logger.error(f"Error getting asset info: {e}")
        return jsonify({
            "error": "Failed to get asset information",
            "details": str(e)
        }), 500