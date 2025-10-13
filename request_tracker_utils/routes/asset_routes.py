"""
Asset creation routes for batch asset entry feature.

This module provides endpoints for creating assets with automatic asset tag assignment,
serial number validation, and asset catalog option retrieval from RT.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
import urllib.parse
import time
from ..utils.rt_api import rt_api_request, sanitize_json
from ..utils.name_generator import InternalNameGenerator
from .tag_routes import AssetTagManager

bp = Blueprint('asset_routes', __name__, url_prefix='/assets')

# Cache for catalog and manufacturer options
# Format: {'data': [...], 'timestamp': time.time()}
_catalog_cache = None
_manufacturer_cache = None
CACHE_TTL = 3600  # Cache for 1 hour (3600 seconds)


def validate_serial_uniqueness(serial_number, config):
    """
    Validate that a serial number is unique across all assets in RT.
    
    Args:
        serial_number: Serial number to validate
        config: Flask app config with RT credentials
        
    Returns:
        tuple: (is_valid, error_message, existing_asset_id)
    """
    try:
        # Query RT for existing assets with this serial number
        query = f'CF.{{Serial Number}} = "{serial_number}"'
        encoded_query = urllib.parse.quote(query)
        response = rt_api_request('GET', f'/assets?query={encoded_query}', config=config)
        
        items = response.get('items', [])
        if len(items) > 0:
            existing_id = items[0].get('id')
            return (False, f'Serial number {serial_number} already exists (Asset #{existing_id})', existing_id)
        
        return (True, None, None)
        
    except Exception as e:
        current_app.logger.error(f'Serial validation failed: {e}')
        raise


@bp.route('/form', methods=['GET'])
def asset_form():
    """Render the batch asset creation form."""
    return render_template('asset_create.html')


@bp.route('/preview-internal-name', methods=['GET'])
def preview_internal_name():
    """
    Preview the next internal name that will be generated.
    Returns a unique adjective-animal combination without committing it.
    """
    try:
        name_generator = InternalNameGenerator(current_app.config)
        internal_name = name_generator.generate_unique_name()
        return jsonify({
            'internal_name': internal_name
        }), 200
    except Exception as e:
        current_app.logger.error(f'Internal name preview failed: {e}')
        return jsonify({
            'error': str(e),
            'internal_name': 'Error generating name'
        }), 500


@bp.route('/catalogs', methods=['GET'])
def get_catalogs():
    """
    Get list of available asset catalogs from RT.
    Returns catalog names for dropdown selection.
    Uses caching to improve performance.
    """
    global _catalog_cache
    
    # Check if cache is valid
    if _catalog_cache and (time.time() - _catalog_cache['timestamp']) < CACHE_TTL:
        current_app.logger.debug(f'Returning {len(_catalog_cache["data"])} catalogs from cache')
        return jsonify({
            'success': True,
            'catalogs': _catalog_cache['data']
        }), 200
    
    try:
        current_app.logger.info('Fetching catalogs from RT (cache miss or expired)')
        response = rt_api_request('GET', '/catalogs/all', config=current_app.config)
        current_app.logger.debug(f'Raw RT catalogs response: {response}')
        catalogs = []
        
        # The /catalogs/all endpoint returns items with id, type, and _url
        # We need to fetch each catalog to get its Name
        for item in response.get('items', []):
            catalog_id = item.get('id')
            if catalog_id:
                # Fetch individual catalog details to get the Name
                catalog_detail = rt_api_request('GET', f'/catalog/{catalog_id}', config=current_app.config)
                catalog_name = catalog_detail.get('Name', '')
                if catalog_name:
                    catalogs.append(catalog_name)
                    current_app.logger.debug(f'Found catalog: {catalog_name} (id={catalog_id})')
        
        current_app.logger.info(f'Found {len(catalogs)} catalogs: {catalogs}')
        
        # Update cache
        _catalog_cache = {
            'data': catalogs,
            'timestamp': time.time()
        }
        
        return jsonify({
            'success': True,
            'catalogs': catalogs
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error fetching catalogs: {e}')
        return jsonify({
            'success': False,
            'error': f'Failed to fetch catalogs: {str(e)}',
            'catalogs': []
        }), 500


@bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """
    Clear the cached catalog and manufacturer data.
    Useful when catalog options have been updated in RT.
    """
    global _catalog_cache, _manufacturer_cache
    
    _catalog_cache = None
    _manufacturer_cache = None
    
    current_app.logger.info('Cache cleared for catalogs and manufacturer options')
    
    return jsonify({
        'success': True,
        'message': 'Cache cleared successfully'
    }), 200


@bp.route('/preview-next-tag', methods=['GET'])
def preview_next_tag():
    """Preview the next asset tag without incrementing the sequence."""
    try:
        tag_manager = AssetTagManager(current_app.config)
        next_tag = tag_manager.get_next_tag()
        sequence = tag_manager.get_current_sequence()
        
        return jsonify({
            'next_tag': next_tag,
            'prefix': tag_manager.prefix,
            'sequence_number': sequence
        })
    except Exception as e:
        current_app.logger.error(f'Tag preview error: {e}')
        return jsonify({'error': 'Failed to get next tag'}), 500


@bp.route('/validate-serial', methods=['GET'])
def validate_serial():
    """Validate serial number uniqueness without creating an asset."""
    serial_number = request.args.get('serial_number')
    
    if not serial_number:
        return jsonify({'error': 'Missing required parameter: serial_number'}), 400
    
    try:
        is_valid, error_msg, existing_id = validate_serial_uniqueness(serial_number, current_app.config)
        
        if not is_valid:
            # Query for existing asset tag
            existing_tag = None
            try:
                response = rt_api_request('GET', f'/asset/{existing_id}', config=current_app.config)
                existing_tag = response.get('Name')
            except:
                pass
            
            return jsonify({
                'valid': False,
                'serial_number': serial_number,
                'error': error_msg,
                'existing_asset_id': existing_id,
                'existing_asset_tag': existing_tag
            })
        
        return jsonify({'valid': True, 'serial_number': serial_number})
        
    except Exception as e:
        current_app.logger.error(f'Serial validation error: {e}')
        return jsonify({'error': 'Validation failed', 'retry': True}), 500


@bp.route('/create', methods=['POST'])
def create_asset():
    """Create new asset with automatic tag assignment."""
    data = request.get_json()
    
    # Validate required fields
    serial_number = data.get('serial_number')
    if not serial_number:
        return jsonify({
            'success': False,
            'error': 'Missing required field: serial_number',
            'field': 'serial_number'
        }), 400
    
    manufacturer = data.get('manufacturer')
    if not manufacturer:
        return jsonify({
            'success': False,
            'error': 'Missing required field: manufacturer',
            'field': 'manufacturer'
        }), 400
    
    model = data.get('model')
    if not model:
        return jsonify({
            'success': False,
            'error': 'Missing required field: model',
            'field': 'model'
        }), 400
    
    # Validate serial number uniqueness
    try:
        is_valid, error_msg, existing_id = validate_serial_uniqueness(serial_number, current_app.config)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg,
                'field': 'serial_number',
                'existing_asset_id': existing_id
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to validate serial number',
            'retry': True
        }), 500
    
    # Get next asset tag
    tag_manager = AssetTagManager(current_app.config)
    try:
        asset_tag = tag_manager.get_next_tag()
    except Exception as e:
        current_app.logger.error(f'Asset tag generation failed: {e}')
        return jsonify({
            'success': False,
            'error': 'Asset tag sequence unavailable',
            'retry': True
        }), 500
    
    # Generate unique internal name
    try:
        name_generator = InternalNameGenerator(current_app.config)
        internal_name = name_generator.generate_unique_name()
        current_app.logger.info(f'Generated internal name: {internal_name}')
    except Exception as e:
        current_app.logger.error(f'Internal name generation failed: {e}')
        return jsonify({
            'success': False,
            'error': f'Failed to generate internal name: {str(e)}',
            'retry': True
        }), 500
    
    # Create asset in RT
    catalog = data.get('catalog')
    if not catalog:
        return jsonify({
            'success': False,
            'error': 'Catalog is required',
            'retry': False
        }), 400
    
    try:
        # Create asset with basic fields first
        asset_data = {
            'Name': asset_tag,
            'Catalog': catalog,
            'Description': f'Asset {asset_tag} - {internal_name}'  # Friendly description
        }
        
        current_app.logger.debug(f'Creating asset with data: {asset_data}')
        
        response = rt_api_request('POST', '/asset', data=asset_data, config=current_app.config)
        asset_id = response.get('id')
        
        current_app.logger.info(f'Asset {asset_tag} created with ID: {asset_id}')
        
        # Now update with custom fields using correct RT API format
        # Per RT REST2 API docs: CustomFields should be an object with field names as keys
        custom_fields = {
            'Serial Number': serial_number,
            'Manufacturer': manufacturer,
            'Model': model,
            'Internal Name': internal_name
        }
        
        # Add optional fields
        # Note: 'category' in the form maps to 'Type' custom field in RT
        if data.get('category'):
            custom_fields['Type'] = data.get('category')
        if data.get('funding_source'):
            custom_fields['Funding Source'] = data.get('funding_source')
        
        custom_fields_data = {'CustomFields': custom_fields}
        current_app.logger.debug(f'Updating asset {asset_id} with custom fields: {custom_fields}')
        
        rt_api_request('PUT', f'/asset/{asset_id}', data=custom_fields_data, config=current_app.config)
        
        # Increment sequence and log
        tag_manager.increment_sequence()
        tag_manager.log_confirmation(asset_tag, asset_id)
        
        current_app.logger.info(f'Asset {asset_tag} created successfully (ID: {asset_id}, Internal: {internal_name})')
        
        # Generate label URL for the newly created asset
        label_url = f'/labels/print?assetId={asset_id}'
        
        return jsonify({
            'success': True,
            'asset_id': asset_id,
            'asset_tag': asset_tag,
            'serial_number': serial_number,
            'internal_name': internal_name,
            'label_url': label_url,
            'label_printed': False,
            'message': f'Asset {asset_tag} ({internal_name}) created successfully'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Asset creation failed: {e}')
        return jsonify({
            'success': False,
            'error': f'Failed to create asset in RT: {str(e)}',
            'retry': True
        }), 500


@bp.route('/catalog-options', methods=['GET'])
def get_catalog_options():
    """
    Get distinct catalog options from existing assets in RT for dropdown population.
    Uses caching to improve performance.
    
    Returns JSON with arrays of unique values for:
    - manufacturers
    - models
    - categories
    - funding_sources
    """
    global _manufacturer_cache
    
    # Check if cache is valid
    if _manufacturer_cache and (time.time() - _manufacturer_cache['timestamp']) < CACHE_TTL:
        current_app.logger.debug('Returning catalog options from cache')
        return jsonify(sanitize_json(_manufacturer_cache['data']))
    
    try:
        current_app.logger.info('Fetching catalog options from RT (cache miss or expired)')
        # Fetch custom field definitions directly from RT API
        # This is more efficient than querying all assets
        current_app.logger.debug('Fetching custom field definitions from RT')
        
        result = {
            'manufacturers': [],
            'models': [],
            'categories': [],
            'funding_sources': []
        }
        
        # Map custom field names to result keys
        field_mapping = {
            'Manufacturer': 'manufacturers',
            'Model': 'models',
            'Category': 'categories',
            'Funding Source': 'funding_sources'
        }
        
        # First, search for all custom fields (not just Select type)
        # We'll filter by name instead
        search_query = [
            {"field": "id", "operator": ">=", "value": 0}
        ]
        cf_response = rt_api_request('POST', '/customfields', data=search_query, config=current_app.config)
        
        custom_field_ids = [cf.get('id') for cf in cf_response.get('items', [])]
        current_app.logger.debug(f'Found {len(custom_field_ids)} custom fields total')
        
        # Fetch full details for each custom field to get names and values
        for cf_id in custom_field_ids:
            try:
                # Get the custom field details
                cf_detail = rt_api_request('GET', f'/customfield/{cf_id}', config=current_app.config)
                cf_name = cf_detail.get('Name', '')
                cf_type = cf_detail.get('Type', '')
                
                current_app.logger.debug(f'Found custom field: {cf_name} (id={cf_id}, type={cf_type})')
                
                if cf_name in field_mapping:
                    value_names = []
                    
                    # For Select fields, values are included in the field details
                    if cf_type == 'Select':
                        values = cf_detail.get('Values', [])
                        # Note: Select values use lowercase 'name', not 'Name'
                        value_names = [v.get('name', '') for v in values if v.get('name')]
                    
                    # For Combobox fields, we need to fetch values separately
                    elif cf_type == 'Combobox':
                        try:
                            values_response = rt_api_request('GET', f'/customfield/{cf_id}/values', config=current_app.config)
                            values = values_response.get('items', [])
                            # Note: Combobox values use lowercase 'name', not 'Name'
                            value_names = [v.get('name', '') for v in values if v.get('name')]
                        except Exception as e:
                            current_app.logger.warning(f'Error fetching values for Combobox field {cf_name}: {str(e)}')
                    
                    if value_names:
                        # Store in result
                        result_key = field_mapping[cf_name]
                        result[result_key] = sorted(value_names)
                        current_app.logger.debug(f'Found {len(value_names)} values for {cf_name}')
                    else:
                        current_app.logger.debug(f'No values found for {cf_name} (type={cf_type})')
            except Exception as e:
                current_app.logger.warning(f'Error fetching custom field {cf_id}: {str(e)}')
                continue
        
        current_app.logger.info(
            f'Catalog options extracted: {len(result["manufacturers"])} manufacturers, '
            f'{len(result["models"])} models, {len(result["categories"])} categories, '
            f'{len(result["funding_sources"])} funding sources'
        )
        
        # Update cache
        _manufacturer_cache = {
            'data': result,
            'timestamp': time.time()
        }
        
        return jsonify(sanitize_json(result))
        
    except Exception as e:
        current_app.logger.error(f'Error fetching catalog options: {e}')
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'error': f'Failed to fetch catalog options: {str(e)}',
            'manufacturers': [],
            'models': [],
            'categories': [],
            'funding_sources': []
        }), 500
