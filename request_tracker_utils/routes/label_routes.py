from flask import Blueprint, request, jsonify, render_template, current_app, Response
import json
import io
import base64
import urllib.parse
import qrcode
import traceback
from PIL import Image
from barcode import Code128
from barcode.writer import ImageWriter
from request_tracker_utils.utils.rt_api import fetch_asset_data, search_assets, update_asset_custom_field, find_asset_by_name, rt_api_request

bp = Blueprint('label_routes', __name__, url_prefix='/labels')

def get_custom_field_value(custom_fields, field_name, default="N/A"):
    """
    Extract a value from the custom fields array by field name.
    
    Args:
        custom_fields (list): List of custom field dictionaries
        field_name (str): Name of the field to extract
        default (str): Default value if field not found
        
    Returns:
        str: The value of the field or default if not found
    """
    return next(
        (field.get("values", [None])[0] 
         for field in custom_fields 
         if field.get("name") == field_name and field.get("values")),
        default
    )

def generate_qr_code(url):
    """
    Generate a QR code image and return as base64 string.
    
    Args:
        url (str): URL to encode in the QR code
        
    Returns:
        str: Base64 encoded QR code image
    """
    try:
        # QR code with higher error correction for better resilience
        qr = qrcode.QRCode(
            version=1,  # Fixed version to avoid issues
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # Medium error correction (15% damage recovery)
            box_size=10,  # Increased box size for larger QR code
            border=2      # Maintain smaller border
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Generate image directly to buffer
        qr_buffer = io.BytesIO()
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_buffer, format="PNG")
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")
        qr_buffer.close()
        return qr_base64
        
    except Exception as e:
        current_app.logger.error(f"QR code generation failed: {e}")
        # Create a simple fallback QR code with plain PIL
        try:
            # Generate a simple black square as fallback
            size = 200
            fallback = Image.new('RGB', (size, size), color='white')
            # Add a border to make it look like a QR code
            for i in range(10):
                for j in range(10):
                    if (i == 0 or j == 0 or i == 9 or j == 9) or (i in [2,7] and j in [2,7]):
                        # Draw black squares in QR pattern
                        x, y = i*20, j*20
                        block = Image.new('RGB', (20, 20), color='black')
                        fallback.paste(block, (x, y))
                        
            fallback_buffer = io.BytesIO()
            fallback.save(fallback_buffer, format="PNG")
            fallback_base64 = base64.b64encode(fallback_buffer.getvalue()).decode("utf-8")
            fallback_buffer.close()
            return fallback_base64
        except Exception as fallback_error:
            current_app.logger.error(f"QR code fallback failed: {fallback_error}")
            # If all else fails, return an empty string
            return ""

def calculate_checksum(content):
    """
    Calculate a simple verification checksum for barcode data.
    
    Args:
        content (str): The content to calculate checksum for
        
    Returns:
        str: The original content followed by a verification digit
    """
    # Simple checksum algorithm - sum ASCII values and take modulo 10
    checksum = sum(ord(c) for c in content) % 10
    return f"{content}*{checksum}"

def generate_barcode(content):
    """
    Generate a barcode image and return as base64 string.
    Appends a verification checksum to the content for error detection.
    
    Args:
        content (str): Content to encode in the barcode
        
    Returns:
        str: Base64 encoded barcode image
    """
    # Add verification checksum to content
    verified_content = calculate_checksum(content)
    barcode = Code128(verified_content, writer=ImageWriter())
    # Adjust barcode parameters for better printing
    barcode_writer_options = {
        "module_width": 0.5,  # Increased width for better resolution
        "module_height": 10,  # Increased height for better resolution
        "quiet_zone": 1,      # Minimal quiet zone
        "write_text": False,
        "dpi": 300            # Higher DPI for better print quality
    }
    barcode_buffer = io.BytesIO()
    barcode.write(barcode_buffer, options=barcode_writer_options)
    
    # Resize the barcode to make it wider
    try:
        barcode_buffer.seek(0)  # Reset buffer position
        barcode_image = Image.open(barcode_buffer)
        width, height = barcode_image.size
        
        # Make the barcode wider while maintaining quality
        new_width = min(width * 1.2, 450)  # Controlled width increase
        new_height = min(int(height * 0.8), 28)  # Less height reduction for better clarity
        
        # Use LANCZOS for best quality resizing
        resize_method = getattr(Image, 'LANCZOS', getattr(Image, 'BICUBIC', Image.BICUBIC))
        resized_barcode = barcode_image.resize((int(new_width), new_height), resize_method)
        
        # Save the resized image with high quality settings
        resized_buffer = io.BytesIO()
        resized_barcode.save(
            resized_buffer, 
            format="PNG", 
            optimize=True, 
            compress_level=1  # Lower compression for better quality
        )
        barcode_base64 = base64.b64encode(resized_buffer.getvalue()).decode("utf-8")
        
        # Close buffers
        resized_buffer.close()
    except Exception as img_error:
        current_app.logger.error(f"Error processing barcode image: {img_error}")
        # Fall back to original barcode if resize fails
        barcode_buffer.seek(0)  # Reset buffer position
        barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")
        
    # Close buffer
    barcode_buffer.close()
    return barcode_base64

@bp.route('/')
def label_home():
    """
    Display the label printing form.
    """
    return render_template('label_form.html')

@bp.route('/print')
def print_label():
    """
    Handles the request to print a label for a specific asset.

    This function retrieves either the asset ID or asset name from the request arguments,
    fetches the corresponding asset data from the RT API, and renders a label using
    the "label.html" template.

    Returns:
        Response: A Flask response object containing the rendered label template
        or an error message with the appropriate HTTP status code.

    Raises:
        400 Bad Request: If neither 'assetId' nor 'assetName' parameter is in the request.
        404 Not Found: If the asset name provided doesn't match any asset.
        500 Internal Server Error: If there is an error fetching asset data from the RT API.
    """
    asset_id = request.args.get('assetId')
    asset_name = request.args.get('assetName')
    direct_lookup = request.args.get('direct', 'false').lower() == 'true'
    
    # Log what we received with higher log level for debugging
    current_app.logger.info(f"Received parameters: assetId={asset_id}, assetName={asset_name}, direct={direct_lookup}")
    
    # Check if we have at least one of the required parameters
    if not asset_id and not asset_name:
        current_app.logger.info("Missing both assetId and assetName parameters in the request")
        return jsonify({"error": "You must provide either assetId or assetName parameter"}), 400
        
    try:
        # If we have an asset name but no ID, look up the asset by name
        if asset_name and not asset_id:
            current_app.logger.info(f"Looking up asset by name: {asset_name}")
            
            # Try the JSON filter approach first (matching the curl command format)
            try:
                current_app.logger.info(f"Looking up asset by name using JSON filter: {asset_name}")
                
                # Construct the same filter format used in the curl command
                import requests
                import json
                
                base_url = current_app.config.get('RT_URL')
                api_endpoint = current_app.config.get('API_ENDPOINT')
                token = current_app.config.get('RT_TOKEN')
                
                url = f"{base_url}{api_endpoint}/assets"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"token {token}"
                }
                
                # First try exact match
                filter_data = [
                    {
                        "field": "Name",
                        "operator": "=",
                        "value": asset_name
                    }
                ]
                
                current_app.logger.info(f"Making POST request with exact match filter: {json.dumps(filter_data)}")
                response = requests.post(url, headers=headers, json=filter_data)
                response.raise_for_status()
                
                # Process the response
                result = response.json()
                current_app.logger.info(f"POST exact match response: {json.dumps(result)}")
                
                # Look for assets in the response
                items = []
                if 'items' in result:
                    items = result.get('items', [])
                elif 'assets' in result:
                    items = result.get('assets', [])
                
                if items and len(items) > 0:
                    asset = items[0]  # Take the first match
                    asset_id = asset.get('id')
                    current_app.logger.info(f"Found asset ID: {asset_id} for exact name match: {asset_name}")
                else:
                    # If exact match fails, try LIKE match
                    current_app.logger.info(f"No exact match found, trying LIKE operator")
                    
                    # Try with LIKE operator
                    filter_data = [
                        {
                            "field": "Name",
                            "operator": "LIKE",
                            "value": asset_name
                        }
                    ]
                    
                    current_app.logger.info(f"Making POST request with LIKE filter: {json.dumps(filter_data)}")
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
                    
                    if items and len(items) > 0:
                        asset = items[0]  # Take the first match
                        asset_id = asset.get('id')
                        current_app.logger.info(f"Found asset ID: {asset_id} for LIKE name match: {asset_name}")
                    else:
                        # If that fails too, try with prefix search
                        # Try searching with prefix (for W12-XXXX format)
                        if '-' in asset_name:
                            prefix = asset_name.split('-')[0]
                            filter_data = [
                                {
                                    "field": "Name",
                                    "operator": "LIKE",
                                    "value": f"{prefix}-"
                                }
                            ]
                            
                            current_app.logger.info(f"Making POST request with prefix filter: {json.dumps(filter_data)}")
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
                            
                            if items and len(items) > 0:
                                # Find exact match or closest match
                                exact_matches = [
                                    item for item in items
                                    if item.get("Name", "").lower() == asset_name.lower()
                                ]
                                
                                if exact_matches:
                                    asset = exact_matches[0]
                                else:
                                    # Just take the first one as approximate match
                                    asset = items[0]
                                    
                                asset_id = asset.get('id')
                                asset_name_found = asset.get("Name")
                                current_app.logger.info(f"Found asset ID: {asset_id} for prefix match: {asset_name_found}")
                            else:
                                # All JSON filter approaches failed
                                if direct_lookup:
                                    # Fall back to direct lookup if requested
                                    current_app.logger.info("JSON filter failed, falling back to direct lookup approach")
                                    direct_query = "id>0 LIMIT 1000" 
                                    response = rt_api_request("GET", f"/assets?query={urllib.parse.quote(direct_query)}", current_app.config)
                                    all_assets = response.get("assets", [])
                                    current_app.logger.info(f"Retrieved {len(all_assets)} assets for filtering")
                                    
                                    # Case-insensitive exact match
                                    matching_assets = [
                                        a for a in all_assets 
                                        if a.get("Name") and a.get("Name").lower() == asset_name.lower()
                                    ]
                                    
                                    if matching_assets:
                                        asset = matching_assets[0]
                                        asset_id = asset.get('id')
                                        current_app.logger.info(f"Direct lookup found asset ID: {asset_id} for name: {asset_name}")
                                    else:
                                        # Try for approximate matches (contains)
                                        approx_matches = [
                                            a for a in all_assets 
                                            if a.get("Name") and asset_name.lower() in a.get("Name").lower()
                                        ]
                                        
                                        if approx_matches:
                                            asset = approx_matches[0]
                                            asset_id = asset.get('id')
                                            current_app.logger.info(f"Direct lookup found approximate match with ID: {asset_id}, name: {asset.get('Name')}")
                                        else:
                                            raise Exception(f"No asset found with name similar to: {asset_name}")
                                else:
                                    # Fall back to standard find_asset_by_name as last resort
                                    current_app.logger.info("JSON filter failed, falling back to standard find_asset_by_name")
                                    asset = find_asset_by_name(asset_name, current_app.config)
                                    
                                    if not asset:
                                        raise Exception(f"No asset found with name: {asset_name}")
                                        
                                    asset_id = asset.get('id')
                                    current_app.logger.info(f"Found asset ID: {asset_id} for name: {asset_name}")
                
            except Exception as e:
                current_app.logger.error(f"Error looking up asset by name: {e}")
                return jsonify({
                    "error": f"No asset found with name: {asset_name}",
                    "tip": "Try checking the asset name in RT or use an asset ID instead.",
                    "details": str(e)
                }), 404
        
        # Fetch asset data from RT API using the ID
        current_app.logger.info(f"Fetching asset data for ID: {asset_id}")
        asset_data = fetch_asset_data(asset_id, current_app.config)
        
        # Extract custom fields
        custom_fields = asset_data.get("CustomFields", [])
        
        # Build the asset_label_data object
        asset_label_data = {
            "name": asset_data.get("Name", "Unknown Asset"),
            "description": asset_data.get("Description", "No description available."),
            "tag": asset_data.get("Name", "Unknown Tag"),
            "internal_name": get_custom_field_value(custom_fields, "Internal Name"),
            "model_number": get_custom_field_value(custom_fields, "Model"),
            "funding_source": get_custom_field_value(custom_fields, "Funding Source"),
            "serial_number": get_custom_field_value(custom_fields, "Serial Number"),
            "label_width": current_app.config.get("LABEL_WIDTH_MM", 100) - 4,
            "label_height": current_app.config.get("LABEL_HEIGHT_MM", 62) - 4
        }

        # Generate QR Code with the RT URL
        try:
            rt_asset_url = f"https://tickets.wc-12.com/Asset/Display.html?id={asset_id}"
            current_app.logger.debug(f"Generating QR code for URL: {rt_asset_url}")
            asset_label_data["qr_code"] = generate_qr_code(rt_asset_url)
            current_app.logger.debug("QR code generation successful")
        except Exception as qr_error:
            current_app.logger.error(f"Error generating QR code: {qr_error}")
            # Provide a placeholder if QR code generation fails
            asset_label_data["qr_code"] = ""
        
        # Generate Barcode
        try:
            current_app.logger.debug(f"Generating barcode for content: {asset_label_data['name']}")
            asset_label_data["barcode"] = generate_barcode(asset_label_data["name"])
            current_app.logger.debug("Barcode generation successful")
        except Exception as barcode_error:
            current_app.logger.error(f"Error generating barcode: {barcode_error}")
            # Provide a placeholder if barcode generation fails
            asset_label_data["barcode"] = ""
        
        # Log the final data - be careful not to log large binary data
        log_data = {k: v if k not in ["qr_code", "barcode"] else "[binary data]" for k, v in asset_label_data.items()}
        import json as json_for_logging
        current_app.logger.debug(f"Asset label data: {json_for_logging.dumps(log_data, indent=4)}")

    except Exception as e:
        import traceback
        import json as json_module  # Import with a different name to avoid conflicts
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"Error processing asset data: {e}")
        current_app.logger.error(f"Traceback: {error_traceback}")
        
        # Provide more detailed error for debugging - using jsonify directly which doesn't require json module
        return jsonify({
            "error": "Failed to process asset data", 
            "details": str(e),
            "asset_id": asset_id
        }), 500

    # Render the label using the template
    current_app.logger.debug("Rendering the label template with asset label data")
    return render_template("label.html", **asset_label_data)


@bp.route('/batch', methods=['GET', 'POST'])
def batch_labels():
    """
    Generate labels for a batch of assets.
    
    GET: Display the batch label form
    POST: Generate batch labels based on the submitted query or asset names
    
    Returns:
        GET: Rendered template with the batch label form
        POST: Rendered template with labels for all matching assets
    """
    # Log all request details to debug form submission issues
    current_app.logger.info(f"Batch labels route called with method: {request.method}")
    current_app.logger.info(f"Request form data: {request.form}")
    current_app.logger.info(f"Request headers: {request.headers}")
    
    if request.method == 'GET':
        return render_template('batch_labels_form.html')
    
    # POST method - process the submitted query or asset names
    query = request.form.get('query', '')
    asset_names = request.form.get('asset_names', '')
    direct_lookup = request.form.get('direct', 'false').lower() == 'true'
    
    current_app.logger.info(f"Batch labels request: query={query}, asset_names={asset_names}, direct={direct_lookup}")
    
    # Check if we have at least one input method
    if not query and not asset_names:
        return render_template('batch_labels_form.html', 
                              error="Please provide either a query or a list of asset names")
    
    try:
        # Variable to hold the assets we'll process
        assets = []
        warning_message = None
        
        # If we have asset names, process them individually instead of using a query
        if asset_names:
            # Split the asset names by newlines, commas, or spaces
            names_list = [name.strip() for name in asset_names.replace(',', '\n').split('\n')]
            names_list = [name for name in names_list if name]  # Remove empty entries
            
            if not names_list:
                return render_template('batch_labels_form.html', 
                                      error="No valid asset names found")
            
            current_app.logger.info(f"Processing {len(names_list)} asset names: {', '.join(names_list)}")
            
            # Process each asset name individually
            failed_names = []
            
            # If direct lookup is enabled, fetch all assets once and then filter
            all_assets = []
            if direct_lookup:
                current_app.logger.info("Using direct lookup for batch processing")
                try:
                    # Fetch up to 1000 assets (adjust limit as needed)
                    direct_query = "id>0 LIMIT 1000"
                    response = rt_api_request("GET", f"/assets?query={urllib.parse.quote(direct_query)}", current_app.config)
                    all_assets = response.get("assets", [])
                    current_app.logger.info(f"Direct lookup retrieved {len(all_assets)} assets to search through")
                except Exception as e:
                    current_app.logger.error(f"Error fetching assets for direct lookup: {e}")
                    # Fall back to standard search if direct lookup fails
                    all_assets = []
            
            for asset_name in names_list:
                try:
                    asset = None
                    
                    # Direct lookup method
                    if direct_lookup and all_assets:
                        current_app.logger.info(f"Searching for {asset_name} in local asset list")
                        # Case-insensitive match
                        matching_assets = [
                            a for a in all_assets 
                            if a.get("Name") and a.get("Name").lower() == asset_name.lower()
                        ]
                        
                        if matching_assets:
                            asset = matching_assets[0]
                            current_app.logger.info(f"Direct lookup found asset {asset_name} with ID: {asset.get('id')}")
                        else:
                            # Try for approximate matches
                            approx_matches = [
                                a for a in all_assets 
                                if a.get("Name") and asset_name.lower() in a.get("Name").lower()
                            ]
                            
                            if approx_matches:
                                asset = approx_matches[0]
                                current_app.logger.info(f"Direct lookup found approximate match for {asset_name}: {asset.get('Name')} (ID: {asset.get('id')})")
                    else:
                        # Use JSON filter lookup method
                        current_app.logger.info(f"Using JSON filter lookup for asset: {asset_name}")
                        
                        # Construct the filter in the same format as the curl command
                        import requests
                        import json
                        
                        base_url = current_app.config.get('RT_URL')
                        api_endpoint = current_app.config.get('API_ENDPOINT')
                        token = current_app.config.get('RT_TOKEN')
                        
                        url = f"{base_url}{api_endpoint}/assets"
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"token {token}"
                        }
                        
                        # Try exact match filter first
                        filter_data = [
                            {
                                "field": "Name",
                                "operator": "=",
                                "value": asset_name
                            }
                        ]
                        
                        try:
                            response = requests.post(url, headers=headers, json=filter_data)
                            response.raise_for_status()
                            result = response.json()
                            
                            # Extract assets from the response
                            items = []
                            if 'items' in result:
                                items = result.get('items', [])
                            elif 'assets' in result:
                                items = result.get('assets', [])
                            
                            if items and len(items) > 0:
                                # Take the first match
                                asset = items[0]
                                current_app.logger.info(f"Found exact match for {asset_name}")
                            else:
                                # If exact match fails, try LIKE operator
                                filter_data = [
                                    {
                                        "field": "Name",
                                        "operator": "LIKE",
                                        "value": asset_name
                                    }
                                ]
                                
                                response = requests.post(url, headers=headers, json=filter_data)
                                response.raise_for_status()
                                result = response.json()
                                
                                # Extract assets from the response
                                items = []
                                if 'items' in result:
                                    items = result.get('items', [])
                                elif 'assets' in result:
                                    items = result.get('assets', [])
                                
                                if items and len(items) > 0:
                                    # Take the first match
                                    asset = items[0]
                                    current_app.logger.info(f"Found LIKE match for {asset_name}")
                                else:
                                    # If that fails, try with prefix search for W12-XXXX format
                                    if '-' in asset_name:
                                        prefix = asset_name.split('-')[0]
                                        filter_data = [
                                            {
                                                "field": "Name",
                                                "operator": "LIKE",
                                                "value": f"{prefix}-"
                                            }
                                        ]
                                        
                                        response = requests.post(url, headers=headers, json=filter_data)
                                        response.raise_for_status()
                                        result = response.json()
                                        
                                        # Extract assets from the response
                                        items = []
                                        if 'items' in result:
                                            items = result.get('items', [])
                                        elif 'assets' in result:
                                            items = result.get('assets', [])
                                        
                                        if items and len(items) > 0:
                                            # Find exact match in the results if possible
                                            exact_matches = [
                                                item for item in items
                                                if item.get("Name", "").lower() == asset_name.lower()
                                            ]
                                            
                                            if exact_matches:
                                                asset = exact_matches[0]
                                                current_app.logger.info(f"Found exact match within prefix results for {asset_name}")
                                            else:
                                                # Just take first one as approximate match
                                                asset = items[0]
                                                current_app.logger.info(f"Found approximate match for {asset_name}: {asset.get('Name')}")
                                        else:
                                            # Fall back to the original method if JSON approach fails
                                            current_app.logger.info(f"JSON filter method failed, falling back to find_asset_by_name")
                                            asset = find_asset_by_name(asset_name, current_app.config)
                                    else:
                                        # Fall back to the original method if JSON approach fails
                                        current_app.logger.info(f"JSON filter method failed, falling back to find_asset_by_name")
                                        asset = find_asset_by_name(asset_name, current_app.config)
                        except Exception as json_error:
                            current_app.logger.warning(f"JSON filter lookup failed: {json_error}, falling back to find_asset_by_name")
                            # Fall back to the original method if JSON approach fails with an exception
                            asset = find_asset_by_name(asset_name, current_app.config)
                    
                    if asset:
                        current_app.logger.info(f"Found asset {asset_name} with ID: {asset.get('id')}")
                        assets.append(asset)
                    else:
                        current_app.logger.error(f"Asset not found: {asset_name}")
                        failed_names.append(asset_name)
                except Exception as e:
                    current_app.logger.error(f"Error processing asset name {asset_name}: {e}")
                    failed_names.append(asset_name)
            
            # If we have any failures, show a message
            if failed_names:
                warning_message = f"Some assets could not be found: {', '.join(failed_names)}"
                current_app.logger.warning(warning_message)
                
                # If no assets were found at all, return an error
                if not assets:
                    return render_template('batch_labels_form.html',
                                          error=f"None of the specified assets could be found. Failed names: {', '.join(failed_names)}")
                                         
            # Log success
            current_app.logger.info(f"Successfully found {len(assets)} assets")
            
        # If we're using a query, search for assets
        else:
            current_app.logger.info(f"Searching for assets with query: {query}")
            
            # Try using the JSON filter format first if the query looks like a prefix (like W12)
            import re
            if re.match(r'^[A-Za-z0-9]+$', query):  # Simple prefix like W12
                try:
                    current_app.logger.info(f"Query looks like a prefix, trying JSON filter approach")
                    
                    # Construct the filter in the same format as the curl command
                    import requests
                    import json
                    
                    base_url = current_app.config.get('RT_URL')
                    api_endpoint = current_app.config.get('API_ENDPOINT')
                    token = current_app.config.get('RT_TOKEN')
                    
                    url = f"{base_url}{api_endpoint}/assets"
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"token {token}"
                    }
                    
                    # Use the LIKE operator with prefix
                    filter_data = [
                        {
                            "field": "Name",
                            "operator": "LIKE",
                            "value": f"{query}-"  # Add hyphen for prefix match
                        }
                    ]
                    
                    current_app.logger.info(f"Making POST request with filter: {json.dumps(filter_data)}")
                    response = requests.post(url, headers=headers, json=filter_data)
                    response.raise_for_status()
                    
                    # Process the response
                    result = response.json()
                    
                    # Extract assets from the response
                    items = []
                    if 'items' in result:
                        items = result.get('items', [])
                    elif 'assets' in result:
                        items = result.get('assets', [])
                    
                    if items and len(items) > 0:
                        current_app.logger.info(f"JSON filter found {len(items)} assets")
                        assets = items
                        
                        # Fetch complete details for each asset
                        complete_assets = []
                        for item in assets:
                            asset_id = item.get('id')
                            if not asset_id:
                                continue
                                
                            try:
                                # Fetch complete asset data
                                asset_data = fetch_asset_data(asset_id, current_app.config)
                                complete_assets.append(asset_data)
                            except Exception as e:
                                current_app.logger.error(f"Error fetching details for asset {asset_id}: {e}")
                                # Include the basic item anyway so we have something
                                complete_assets.append(item)
                        
                        # Replace the assets list with the complete data
                        assets = complete_assets
                    else:
                        # Fall back to the original search method
                        current_app.logger.info(f"JSON filter found no assets, falling back to standard search")
                        assets = search_assets(query, current_app.config)
                except Exception as e:
                    current_app.logger.warning(f"JSON filter search failed: {e}, falling back to standard search")
                    # Fall back to standard search if JSON approach fails
                    assets = search_assets(query, current_app.config)
            else:
                # Use standard search for complex queries
                assets = search_assets(query, current_app.config)
                
            if not assets:
                return render_template('batch_labels_form.html', 
                                      error="No assets found matching your query.")
                                      
            current_app.logger.info(f"Query found {len(assets)} assets")
        
        # Prepare label data for each asset
        labels_data = []
        
        for asset in assets:
            asset_id = asset.get('id')
            custom_fields = asset.get('CustomFields', [])
            
            # Ensure we have complete asset data with custom fields
            if not custom_fields and asset_id:
                try:
                    # Fetch complete asset data if it doesn't already have custom fields
                    current_app.logger.info(f"Fetching complete data for asset ID: {asset_id}")
                    complete_asset = fetch_asset_data(asset_id, current_app.config)
                    custom_fields = complete_asset.get("CustomFields", [])
                    
                    # Update asset data with the complete version
                    asset = complete_asset
                except Exception as e:
                    current_app.logger.error(f"Error fetching complete asset data: {e}")
            
            # Log the custom fields for debugging
            cf_names = [cf.get("name") for cf in custom_fields if cf.get("name")]
            current_app.logger.debug(f"Custom fields for asset {asset_id}: {cf_names}")
            
            # Build label data for this asset
            label_data = {
                "id": asset_id,
                "name": asset.get("Name", "Unknown Asset"),
                "description": asset.get("Description", "No description available."),
                "tag": asset.get("Name", "Unknown Tag"),
                "internal_name": get_custom_field_value(custom_fields, "Internal Name"),
                "model_number": get_custom_field_value(custom_fields, "Model"),
                "funding_source": get_custom_field_value(custom_fields, "Funding Source"),
                "serial_number": get_custom_field_value(custom_fields, "Serial Number"),
                "label_width": current_app.config.get("LABEL_WIDTH_MM", 100) - 4,
                "label_height": current_app.config.get("LABEL_HEIGHT_MM", 62) - 4
            }
            
            # Generate QR Code with the RT URL
            # Use the same URL format as single labels
            rt_asset_url = f"https://tickets.wc-12.com/Asset/Display.html?id={asset_id}"
            current_app.logger.debug(f"QR code URL for asset {asset_id}: {rt_asset_url}")
            label_data["qr_code"] = generate_qr_code(rt_asset_url)
            
            # Generate Barcode
            label_data["barcode"] = generate_barcode(label_data["name"])
            
            labels_data.append(label_data)
        
        # Render the batch labels template with all label data
        context = {'labels': labels_data}
        if warning_message:
            context['warning'] = warning_message
        
        # Log the context data for debugging
        current_app.logger.info(f"Rendering batch_labels.html with {len(labels_data)} labels")
        
        # Add debugging helper
        context['debug'] = True
        context['label_count'] = len(labels_data)
        
        # Ensure template exists and can be rendered
        try:
            response = render_template('batch_labels.html', **context)
            current_app.logger.info(f"Successfully rendered batch_labels.html, response length: {len(response)}")
            return response
        except Exception as template_error:
            current_app.logger.error(f"Error rendering template: {template_error}")
            return render_template('batch_labels_form.html', 
                                  error=f"Error rendering labels: {str(template_error)}")
        
    except Exception as e:
        import traceback
        import json as json_module  # Import with a different name to avoid conflicts
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"Error processing batch labels: {e}")
        current_app.logger.error(f"Traceback: {error_traceback}")
        
        # Return a more detailed error
        return render_template('batch_labels_form.html', 
                              error=f"Failed to process batch labels: {str(e)}. Please check the server logs for more information.")

def custom_jsonify(data):
    """
    Custom version of jsonify that handles types that normally can't be serialized.
    """
    import json
    from flask import Response
    
    class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, 'total_seconds'):
                return f"{obj.total_seconds()} seconds"
            return str(obj)  # Convert any non-serializable objects to strings
    
    response = Response(
        json.dumps(data, cls=CustomJSONEncoder, indent=2),
        mimetype='application/json'
    )
    return response

@bp.route('/test-api-methods', methods=['GET'])
def test_api_methods():
    """
    Test both GET and POST methods for the RT API to see which one works.
    This is a diagnostic tool to help troubleshoot API issues.
    """
    try:
        # Import requests library
        import requests
        
        # Prepare basic test query
        query = "id>0 LIMIT 10"  # Simple query to get a few assets
        
        results = {
            "query": query,
            "tests": []
        }
        
        # Test 1: Direct GET request
        try:
            base_url = current_app.config.get('RT_URL')
            api_endpoint = current_app.config.get('API_ENDPOINT')
            token = current_app.config.get('RT_TOKEN')
            
            url = f"{base_url}{api_endpoint}/assets?query={urllib.parse.quote(query)}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"token {token}"
            }
            
            current_app.logger.info(f"Testing direct GET request to: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            assets = response.json().get("assets", [])
            
            results["tests"].append({
                "method": "Direct GET",
                "status": "success",
                "asset_count": len(assets),
                "first_few_assets": [{"id": a.get("id"), "name": a.get("Name")} for a in assets[:3]]
            })
        except Exception as e:
            results["tests"].append({
                "method": "Direct GET",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        # Test 2: Direct POST request
        try:
            base_url = current_app.config.get('RT_URL')
            api_endpoint = current_app.config.get('API_ENDPOINT')
            token = current_app.config.get('RT_TOKEN')
            
            url = f"{base_url}{api_endpoint}/assets"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"token {token}"
            }
            
            data = {"query": query}
            
            current_app.logger.info(f"Testing direct POST request to: {url} with data: {data}")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            assets = response.json().get("assets", [])
            
            results["tests"].append({
                "method": "Direct POST with json",
                "status": "success",
                "asset_count": len(assets),
                "first_few_assets": [{"id": a.get("id"), "name": a.get("Name")} for a in assets[:3]]
            })
        except Exception as e:
            results["tests"].append({
                "method": "Direct POST with json",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        # Test 3: POST with data, not json
        try:
            base_url = current_app.config.get('RT_URL')
            api_endpoint = current_app.config.get('API_ENDPOINT')
            token = current_app.config.get('RT_TOKEN')
            
            url = f"{base_url}{api_endpoint}/assets"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"token {token}"
            }
            
            data = {"query": query}
            
            current_app.logger.info(f"Testing direct POST request to: {url} with data as string: {json.dumps(data)}")
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            
            assets = response.json().get("assets", [])
            
            results["tests"].append({
                "method": "Direct POST with data=json.dumps()",
                "status": "success",
                "asset_count": len(assets),
                "first_few_assets": [{"id": a.get("id"), "name": a.get("Name")} for a in assets[:3]]
            })
        except Exception as e:
            results["tests"].append({
                "method": "Direct POST with data=json.dumps()",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
            
        # Test 4: POST with form-urlencoded content type
        try:
            base_url = current_app.config.get('RT_URL')
            api_endpoint = current_app.config.get('API_ENDPOINT')
            token = current_app.config.get('RT_TOKEN')
            
            url = f"{base_url}{api_endpoint}/assets"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"token {token}"
            }
            
            # Format as form data
            form_data = {"query": query}
            
            current_app.logger.info(f"Testing POST with form-urlencoded: {url} with data: {form_data}")
            response = requests.post(url, headers=headers, data=form_data)
            response.raise_for_status()
            
            assets = response.json().get("assets", [])
            
            results["tests"].append({
                "method": "POST with form-urlencoded",
                "status": "success",
                "asset_count": len(assets),
                "first_few_assets": [{"id": a.get("id"), "name": a.get("Name")} for a in assets[:3]]
            })
        except Exception as e:
            results["tests"].append({
                "method": "POST with form-urlencoded",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
            
        # Test 5: Using the search_assets function (now using GET by default)
        try:
            assets = search_assets(query, current_app.config, try_post_fallback=False)
            
            results["tests"].append({
                "method": "search_assets function (GET)",
                "status": "success",
                "asset_count": len(assets),
                "first_few_assets": [{"id": a.get("id"), "name": a.get("Name")} for a in assets[:3]]
            })
        except Exception as e:
            results["tests"].append({
                "method": "search_assets function (GET)",
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        # Determine which methods work
        working_methods = [test["method"] for test in results["tests"] if test["status"] == "success"]
        results["working_methods"] = working_methods
        results["recommended_approach"] = working_methods[0] if working_methods else "None of the methods worked"
        
        # Add helpful links
        results["helpful_links"] = {
            "debug_page": "/labels/debug",
            "fetch_assets": "/labels/fetch-assets",
            "direct_lookup": "/labels/direct-lookup?name=ASSET_NAME",
            "search_assets": "/labels/search-assets?q=SEARCH_TERM"
        }
        
        return custom_jsonify(results)
        
    except Exception as e:
        import traceback
        return custom_jsonify({
            "error": f"API method test failed: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc().split("\n"),
            "partial_results": results if 'results' in locals() else {}
        })

@bp.route('/debug-asset', methods=['GET'])
def debug_asset():
    """
    Debug route to troubleshoot asset lookup issues.
    This route takes an asset name and runs a series of diagnostic checks.
    """
    asset_name = request.args.get('name')
    if not asset_name:
        return jsonify({"error": "Please provide an asset name parameter"}), 400
        
    results = {
        "asset_name": asset_name,
        "tests": []
    }
    
    try:
        # Test 1: Direct RT API call to fetch all assets
        try:
            # This will make a direct call to RT API to get a list of all assets
            # We'll limit the results to 100 to avoid overwhelming the response
            direct_query = "id>0 LIMIT 100"
            
            response = rt_api_request("GET", f"/assets?query={urllib.parse.quote(direct_query)}", current_app.config)
            assets_count = len(response.get("assets", []))
            
            asset_names = [asset.get("Name") for asset in response.get("assets", []) if asset.get("Name")]
            asset_in_list = asset_name in asset_names
            
            results["tests"].append({
                "name": "Direct API Call",
                "status": "success",
                "assets_count": assets_count,
                "asset_in_results": asset_in_list,
                "first_few_assets": asset_names[:10] if asset_names else []
            })
        except Exception as e:
            results["tests"].append({
                "name": "Direct API Call",
                "status": "error",
                "error": str(e)
            })
        
        # Test 2: Exact name search by multiple methods
        search_methods = [
            {"query": f"Name='{asset_name}'", "description": "Exact equals search"},
            {"query": f"Name LIKE '{asset_name}'", "description": "LIKE search"},
            {"query": f"{asset_name}", "description": "Simple text search"}
        ]
        
        for method in search_methods:
            try:
                query = method["query"]
                encoded_query = urllib.parse.quote(query)
                response = rt_api_request("GET", f"/assets?query={encoded_query}", current_app.config)
                assets = response.get("assets", [])
                
                results["tests"].append({
                    "name": method["description"],
                    "query": query,
                    "encoded_query": urllib.parse.quote(query),
                    "status": "success",
                    "assets_count": len(assets),
                    "assets": [{"id": asset.get("id"), "name": asset.get("Name")} for asset in assets[:5]]
                })
            except Exception as e:
                results["tests"].append({
                    "name": method["description"],
                    "query": method["query"],
                    "status": "error",
                    "error": str(e)
                })
        
        # Test 3: Try the actual find_asset_by_name function
        try:
            asset = find_asset_by_name(asset_name, current_app.config)
            
            if asset:
                results["tests"].append({
                    "name": "find_asset_by_name function",
                    "status": "success",
                    "asset_found": True,
                    "asset_id": asset.get("id"),
                    "asset_name": asset.get("Name")
                })
            else:
                results["tests"].append({
                    "name": "find_asset_by_name function",
                    "status": "success",
                    "asset_found": False
                })
        except Exception as e:
            results["tests"].append({
                "name": "find_asset_by_name function",
                "status": "error",
                "error": str(e)
            })
        
        # Test 4: Check for wildcard search
        try:
            # Try a wildcard search to see if we can match partial names
            if '-' in asset_name:
                parts = asset_name.split('-')
                prefix = parts[0]
                query = f"Name LIKE '{prefix}-*'"
                encoded_query = urllib.parse.quote(query)
                
                response = rt_api_request("GET", f"/assets?query={encoded_query}", current_app.config)
                assets = response.get("assets", [])
                
                results["tests"].append({
                    "name": "Wildcard search",
                    "query": query,
                    "status": "success",
                    "assets_count": len(assets),
                    "assets": [{"id": asset.get("id"), "name": asset.get("Name")} for asset in assets[:10]]
                })
            else:
                results["tests"].append({
                    "name": "Wildcard search",
                    "status": "skipped",
                    "reason": "Asset name doesn't contain a hyphen for prefix extraction"
                })
        except Exception as e:
            results["tests"].append({
                "name": "Wildcard search",
                "status": "error",
                "error": str(e)
            })
            
        # Test 5: Manual asset list scan
        try:
            # List all assets and manually scan for a match 
            direct_query = "id>0 LIMIT 1000" # Limit to 1000 assets
            response = rt_api_request("GET", f"/assets?query={direct_query}", current_app.config)
            all_assets = response.get("assets", [])
            
            # Case-insensitive search
            matching_assets = [
                asset for asset in all_assets 
                if asset.get("Name") and asset.get("Name").lower() == asset_name.lower()
            ]
            
            # Approximate matching (if asset name is W12-1234, check for "W12-1234" anywhere in the name)
            approx_matches = [
                asset for asset in all_assets 
                if asset.get("Name") and asset_name.lower() in asset.get("Name").lower()
                and asset not in matching_assets  # Don't include exact matches
            ]
            
            results["tests"].append({
                "name": "Manual scan",
                "status": "success",
                "exact_matches": [{"id": a.get("id"), "name": a.get("Name")} for a in matching_assets],
                "approx_matches": [{"id": a.get("id"), "name": a.get("Name")} for a in approx_matches[:5]]
            })
        except Exception as e:
            results["tests"].append({
                "name": "Manual scan",
                "status": "error",
                "error": str(e)
            })
        
        # Overall assessment and recommendations
        asset_found = any(t.get("asset_found", False) for t in results["tests"] if t["name"] == "find_asset_by_name function")
        
        # Check for manual scan results (if available)
        exact_matches = []
        approx_matches = []
        for test in results["tests"]:
            if test["name"] == "Manual scan" and test["status"] == "success":
                exact_matches = test.get("exact_matches", [])
                approx_matches = test.get("approx_matches", [])
                break
        
        # Add helpful links
        results["helpful_links"] = {
            "debug_page": "/labels/debug",
            "list_assets": "/labels/fetch-assets", 
            "direct_lookup": f"/labels/direct-lookup?name={asset_name}"
        }
        
        # If the name has a prefix (like W12-), suggest a search
        if '-' in asset_name:
            prefix = asset_name.split('-')[0]
            results["helpful_links"]["search_by_prefix"] = f"/labels/search-assets?q={prefix}"
        
        if asset_found:
            results["assessment"] = "Asset was found successfully with current logic"
            # If our function found it, we should have its ID
            for test in results["tests"]:
                if test["name"] == "find_asset_by_name function" and test.get("asset_found"):
                    if "asset_id" in test:
                        asset_id = test["asset_id"]
                        results["helpful_links"]["print_label"] = f"/labels/direct-print?id={asset_id}"
                        results["helpful_links"]["asset_info"] = f"/labels/get-asset-info?id={asset_id}"
                    break
        elif exact_matches:
            results["assessment"] = "Asset exists but isn't being found by the main function - manual scan found it"
            results["recommended_id"] = exact_matches[0]["id"]
            results["helpful_links"]["print_label"] = f"/labels/direct-print?id={exact_matches[0]['id']}"
            results["helpful_links"]["asset_info"] = f"/labels/get-asset-info?id={exact_matches[0]['id']}"
        elif approx_matches:
            results["assessment"] = "Asset wasn't found exactly, but similar assets exist"
            results["similar_assets"] = approx_matches
            # Add links for each similar asset
            results["similar_asset_links"] = {}
            for i, asset in enumerate(approx_matches):
                asset_id = asset.get("id")
                asset_name = asset.get("name", f"Asset {i+1}")
                if asset_id:
                    results["similar_asset_links"][asset_name] = {
                        "print": f"/labels/direct-print?id={asset_id}",
                        "info": f"/labels/get-asset-info?id={asset_id}"
                    }
        else:
            results["assessment"] = "Asset doesn't appear to exist in the system with this exact name"
            results["tips"] = [
                "Check the asset name in RT is exactly as entered",
                "Try using the direct lookup option (checkbox in the form)",
                "Use the list assets feature to see what assets exist",
                "Consider searching by asset ID instead"
            ]
            
        return custom_jsonify(results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return custom_jsonify({
            "error": f"Diagnostic test failed: {str(e)}",
            "error_type": type(e).__name__,
            "error_details": error_details,
            "partial_results": results
        })

@bp.route('/search-assets', methods=['GET'])
def search_assets_route():
    """
    Search for assets by partial name.
    
    Supports two query styles:
    1. Simple query: ?q=W12 (searches for assets with W12 in the name)
    2. Direct JSON format with POST to /labels/assets endpoint
    """
    search_term = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)
    
    if not search_term:
        return custom_jsonify({
            "error": "Please provide a search term with the 'q' parameter"
        })
    
    try:
        # First try using the direct JSON format that matches the curl command
        current_app.logger.info(f"Searching for assets with term '{search_term}' using JSON filter format")
        
        # Construct filter similar to the curl command example
        import requests
        import json
        
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        token = current_app.config.get('RT_TOKEN')
        
        url = f"{base_url}{api_endpoint}/assets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # Match the exact JSON structure from the curl command
        # Using the exact format: [{ "field": "Name", "operator": "LIKE", "value": "W12-" }]
        filter_data = [
            {
                "field": "Name",
                "operator": "LIKE",
                "value": f"{search_term}-"  # Add hyphen similar to W12-
            }
        ]
        
        # Log the exact curl command equivalent for debugging
        curl_cmd = f"curl -H 'Authorization: token {token}' -X POST -H \"Content-Type: application/json\" -d '{json.dumps(filter_data)}' {url}"
        current_app.logger.info(f"Equivalent curl command: {curl_cmd}")
        
        current_app.logger.info(f"Making POST request with filter: {json.dumps(filter_data)}")
        
        try:
            # Make the POST request with JSON body
            response = requests.post(url, headers=headers, json=filter_data)
            response.raise_for_status()
            
            # Process the response
            result = response.json()
            # Log the entire response structure for debugging
            current_app.logger.info(f"POST request returned response: {json.dumps(result)}")
            
            # Try to determine what kind of response we got
            if 'items' in result:
                current_app.logger.info(f"Response has 'items' field with {len(result.get('items', []))} items")
            elif 'assets' in result:
                current_app.logger.info(f"Response has 'assets' field with {len(result.get('assets', []))} assets")
            else:
                current_app.logger.info("Response does not have 'items' or 'assets' field")
            
            # Handle the response format from the direct JSON query
            # Extract items from result based on the actual structure returned
            items = []
            if 'items' in result:
                items = result.get('items', [])
            elif 'assets' in result:
                items = result.get('assets', [])
                
            current_app.logger.info(f"Found {len(items)} assets using JSON filter")
            
            # Log the first item to see its structure
            if items and len(items) > 0:
                current_app.logger.info(f"First item structure: {json.dumps(items[0])}")
            
            # Fetch full details for each asset found by ID
            results = []
            for item in items:
                try:
                    # Get the ID from the result item
                    asset_id = item.get("id")
                    if not asset_id:
                        current_app.logger.warning(f"Item has no ID, skipping: {item}")
                        continue
                        
                    # Fetch complete asset details
                    current_app.logger.debug(f"Fetching details for asset ID: {asset_id}")
                    asset_data = fetch_asset_data(asset_id, current_app.config)
                    
                    # Extract catalog information including name, if available
                    catalog_info = asset_data.get("Catalog", {})
                    catalog_id = None
                    catalog_name = None
                    
                    # Handle different catalog formats
                    if isinstance(catalog_info, dict):
                        catalog_id = catalog_info.get("id")
                        # Fetch catalog details to get its name
                        if catalog_id:
                            try:
                                catalog_data = rt_api_request("GET", f"/catalog/{catalog_id}", config=current_app.config)
                                catalog_name = catalog_data.get("Name")
                                current_app.logger.debug(f"Found catalog name: {catalog_name} for ID: {catalog_id}")
                            except Exception as catalog_error:
                                current_app.logger.warning(f"Error fetching catalog details: {catalog_error}")
                    elif isinstance(catalog_info, str) and catalog_info.isdigit():
                        catalog_id = catalog_info
                        # Try to fetch catalog name
                        try:
                            catalog_data = rt_api_request("GET", f"/catalog/{catalog_id}", config=current_app.config)
                            catalog_name = catalog_data.get("Name")
                            current_app.logger.debug(f"Found catalog name: {catalog_name} for ID: {catalog_id}")
                        except Exception as catalog_error:
                            current_app.logger.warning(f"Error fetching catalog details: {catalog_error}")
                    
                    results.append({
                        "id": asset_id,
                        "name": asset_data.get("Name", "Unknown"),
                        "status": asset_data.get("Status", "Unknown"),
                        "description": asset_data.get("Description", ""),
                        "catalog": {
                            "id": catalog_id,
                            "name": catalog_name,
                            "raw": catalog_info
                        }
                    })
                except Exception as detail_error:
                    current_app.logger.error(f"Error fetching details for asset {item.get('id')}: {detail_error}")
                    # Include basic info even if details fetch fails
                    results.append({
                        "id": item.get("id"),
                        "name": item.get("Name", "Unknown"),
                        "status": item.get("Status", "Unknown"),
                        "description": item.get("Description", ""),
                        "catalog": {
                            "id": None,
                            "name": None,
                            "raw": None,
                            "error": "Failed to fetch catalog details"
                        },
                        "error": f"Failed to fetch complete details: {str(detail_error)}"
                    })
            
            return custom_jsonify({
                "search_term": search_term,
                "total_results": len(results),
                "results": results,
                "query_type": "json_filter"
            })
            
        except Exception as json_error:
            current_app.logger.warning(f"JSON filter query failed: {json_error}, trying standard search")
        
        # If JSON approach fails, fall back to the original implementation
        # Try a direct query first
        query = f"Name LIKE '*{search_term}*' LIMIT {limit}"
        
        try:
            # First try LIKE query using GET method
            encoded_query = urllib.parse.quote(query)
            response = rt_api_request("GET", f"/assets?query={encoded_query}", current_app.config)
            assets = response.get("assets", [])
        except Exception as e:
            # If that fails, fetch all and filter manually
            current_app.logger.warning(f"LIKE query failed, falling back to manual filtering: {e}")
            all_query = f"id>0 LIMIT 1000"
            encoded_all_query = urllib.parse.quote(all_query)
            response = rt_api_request("GET", f"/assets?query={encoded_all_query}", current_app.config)
            all_assets = response.get("assets", [])
            
            # Filter manually
            assets = [
                asset for asset in all_assets
                if asset.get("Name") and search_term.lower() in asset.get("Name").lower()
            ][:limit]  # Apply limit after filtering
        
        # Simplify the assets for display
        results = []
        for asset in assets:
            asset_id = asset.get("id")
            if not asset_id:
                continue
                
            try:
                # For consistency with the JSON filter approach, also fetch complete details
                # including catalog information
                asset_data = fetch_asset_data(asset_id, current_app.config)
                
                # Extract catalog information including name, if available
                catalog_info = asset_data.get("Catalog", {})
                catalog_id = None
                catalog_name = None
                
                # Handle different catalog formats
                if isinstance(catalog_info, dict):
                    catalog_id = catalog_info.get("id")
                    # Fetch catalog details to get its name
                    if catalog_id:
                        try:
                            catalog_data = rt_api_request("GET", f"/catalog/{catalog_id}", config=current_app.config)
                            catalog_name = catalog_data.get("Name")
                        except Exception as catalog_error:
                            current_app.logger.warning(f"Error fetching catalog details: {catalog_error}")
                elif isinstance(catalog_info, str) and catalog_info.isdigit():
                    catalog_id = catalog_info
                    # Try to fetch catalog name
                    try:
                        catalog_data = rt_api_request("GET", f"/catalog/{catalog_id}", config=current_app.config)
                        catalog_name = catalog_data.get("Name")
                    except Exception as catalog_error:
                        current_app.logger.warning(f"Error fetching catalog details: {catalog_error}")
                
                results.append({
                    "id": asset_id,
                    "name": asset_data.get("Name", "Unknown"),
                    "status": asset_data.get("Status", "Unknown"),
                    "description": asset_data.get("Description", ""),
                    "catalog": {
                        "id": catalog_id,
                        "name": catalog_name,
                        "raw": catalog_info
                    }
                })
            except Exception as detail_error:
                current_app.logger.error(f"Error fetching details for asset {asset_id}: {detail_error}")
                # Include basic info even if details fetch fails
                results.append({
                    "id": asset_id,
                    "name": asset.get("Name", "Unknown"),
                    "status": asset.get("Status", "Unknown"),
                    "description": asset.get("Description", ""),
                    "catalog": {
                        "id": None,
                        "name": None,
                        "raw": None,
                        "error": "Failed to fetch catalog details"
                    },
                    "error": f"Failed to fetch complete details: {str(detail_error)}"
                })
        
        return custom_jsonify({
            "search_term": search_term,
            "total_results": len(results),
            "results": results,
            "query_type": "standard_search"
        })
    except Exception as e:
        import traceback
        return custom_jsonify({
            "error": f"Search failed: {str(e)}",
            "details": traceback.format_exc()
        })

@bp.route('/direct-lookup', methods=['GET'])
def direct_lookup_route():
    """
    A simple, direct lookup endpoint that bypasses the RT API wrapper.
    Searches for an asset by name using the most reliable approach.
    """
    asset_name = request.args.get('name')
    if not asset_name:
        return Response('{"error": "Missing name parameter"}', mimetype='application/json')
    
    try:
        import requests
        import json
        
        # Direct URL construction
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        
        # Direct headers construction
        token = current_app.config.get('RT_TOKEN')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # Use GET with query parameters (the original approach that works)
        url = f"{base_url}{api_endpoint}/assets"
        query = f"Name LIKE '{asset_name}'"  # Using LIKE instead of = for better matching
        
        current_app.logger.info(f"Searching for asset with name '{asset_name}' using GET query")
        
        # Make request using GET with query parameters
        query_url = f"{url}?query={urllib.parse.quote(query)}"
        current_app.logger.debug(f"Full URL: {query_url}")
        response = requests.get(query_url, headers=headers)
        response.raise_for_status()
        
        # Process response manually
        data = response.json()
        assets = data.get("assets", [])
        
        # Case-insensitive search
        matching_assets = []
        for asset in assets:
            name = asset.get("Name", "")
            if name and name.lower() == asset_name.lower():
                # Create a safe version of the asset
                safe_asset = {}
                for key, value in asset.items():
                    if key in ["id", "Name", "Status", "Description", "Queue", "Catalog"]:
                        safe_asset[key] = value
                    else:
                        # Convert other fields to strings to avoid serialization issues
                        safe_asset[key] = str(value)
                matching_assets.append(safe_asset)
        
        # If no exact match, try partial match
        if not matching_assets:
            partial_matches = []
            for asset in assets:
                name = asset.get("Name", "")
                if name and asset_name.lower() in name.lower():
                    # Create a safe version of the asset
                    safe_asset = {}
                    for key, value in asset.items():
                        if key in ["id", "Name", "Status", "Description", "Queue", "Catalog"]:
                            safe_asset[key] = value
                        else:
                            # Convert other fields to strings to avoid serialization issues
                            safe_asset[key] = str(value)
                    partial_matches.append(safe_asset)
        
        # Return a simple dictionary that we know can be serialized
        if matching_assets:
            # Add debug links for each asset
            for asset in matching_assets:
                asset_id = asset.get("id")
                asset["debug_links"] = {
                    "info": f"/labels/get-asset-info?id={asset_id}",
                    "print": f"/labels/direct-print?id={asset_id}",
                    "debug": f"/labels/debug-asset?name={asset.get('Name', '')}"
                }
            
            return Response(
                json.dumps({
                    "success": True,
                    "exact_match": True,
                    "message": f"Found {len(matching_assets)} exact matches",
                    "assets": matching_assets,
                    "helpful_links": {
                        "debug_page": "/labels/debug",
                        "list_assets": "/labels/fetch-assets"
                    }
                }, indent=2),
                mimetype='application/json'
            )
        elif partial_matches:
            # Add debug links for each asset
            for asset in partial_matches:
                asset_id = asset.get("id")
                asset["debug_links"] = {
                    "info": f"/labels/get-asset-info?id={asset_id}",
                    "print": f"/labels/direct-print?id={asset_id}"
                }
            
            return Response(
                json.dumps({
                    "success": True,
                    "exact_match": False,
                    "message": f"Found {len(partial_matches)} partial matches",
                    "assets": partial_matches[:5],  # Limit to 5 matches
                    "tips": [
                        "No exact match was found, but these assets have similar names",
                        "Consider using asset ID instead of name for more reliable lookups"
                    ],
                    "helpful_links": {
                        "debug_page": "/labels/debug",
                        "list_assets": "/labels/fetch-assets"
                    }
                }, indent=2),
                mimetype='application/json'
            )
        else:
            return Response(
                json.dumps({
                    "success": False,
                    "message": f"No assets found matching '{asset_name}'",
                    "sample_assets": [asset.get("Name") for asset in assets[:10] if asset.get("Name")],
                    "tips": [
                        "Check if the asset name is correct",
                        "Try searching with a partial name using /labels/search-assets?q=PARTIAL_NAME",
                        "View all assets using /labels/fetch-assets to find the correct name"
                    ],
                    "helpful_links": {
                        "debug_page": "/labels/debug",
                        "list_assets": "/labels/fetch-assets",
                        "search": f"/labels/search-assets?q={asset_name.split('-')[0] if '-' in asset_name else asset_name}"
                    }
                }, indent=2),
                mimetype='application/json'
            )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": error_trace.split("\n")
            }, indent=2),
            mimetype='application/json'
        )

@bp.route('/fetch-assets', methods=['GET'])
def fetch_assets_direct():
    """
    Directly fetch assets using a low-level approach that bypasses the RT API wrapper.
    This should work even when normal API calls are failing due to serialization issues.
    """
    try:
        import requests
        import json
        
        # Direct URL construction
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        url = f"{base_url}{api_endpoint}/assets?query=id>0%20LIMIT%2050"
        
        # Direct headers construction
        token = current_app.config.get('RT_TOKEN')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # Make request
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Process response manually
        data = response.json()
        
        # Process the assets to make them JSON-safe
        result_assets = []
        if "assets" in data:
            for asset in data["assets"]:
                safe_asset = {}
                for key, value in asset.items():
                    if key in ["id", "Name", "Status", "Description", "Queue", "Catalog"]:
                        safe_asset[key] = value
                    else:
                        # Convert other fields to strings to avoid serialization issues
                        safe_asset[key] = str(value)
                result_assets.append(safe_asset)
        
        # Return a simple dictionary that we know can be serialized
        return Response(
            json.dumps({
                "success": True,
                "count": len(result_assets),
                "assets": result_assets[:20]  # Limit to first 20 for display
            }, indent=2),
            mimetype='application/json'
        )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return Response(
            json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": error_trace.split("\n")
            }, indent=2),
            mimetype='application/json'
        )

@bp.route('/get-asset-info', methods=['GET'])
def get_asset_info():
    """
    Get detailed information about a specific asset by ID.
    """
    asset_id = request.args.get('id')
    if not asset_id:
        return custom_jsonify({"error": "Please provide an asset ID with the 'id' parameter"})
    
    try:
        # Fetch the asset data
        asset_data = fetch_asset_data(asset_id, current_app.config)
        
        # Create a safe version of the asset that can be serialized
        safe_asset = {
            "id": asset_data.get("id"),
            "name": asset_data.get("Name"),
            "status": asset_data.get("Status"),
            "description": asset_data.get("Description"),
            "catalog": asset_data.get("Catalog"),
            "created": str(asset_data.get("Created")),
            "last_updated": str(asset_data.get("LastUpdated")),
            "custom_fields": {}
        }
        
        # Extract custom fields
        if "CustomFields" in asset_data:
            for field in asset_data["CustomFields"]:
                field_name = field.get("name", "unknown")
                field_values = field.get("values", [])
                value = field_values[0] if field_values else None
                safe_asset["custom_fields"][field_name] = value
        
        # Add debug links
        debug_links = {}
        if safe_asset.get("name"):
            debug_links["lookup_by_name"] = f"/labels/direct-lookup?name={safe_asset['name']}"
            debug_links["debug_asset"] = f"/labels/debug-asset?name={safe_asset['name']}"
        debug_links["print_label"] = f"/labels/direct-print?id={asset_id}"
        
        return custom_jsonify({
            "asset": safe_asset,
            "debug_links": debug_links
        })
    except Exception as e:
        import traceback
        return custom_jsonify({
            "error": f"Failed to get asset info: {str(e)}",
            "details": traceback.format_exc()
        })

@bp.route('/list-assets', methods=['GET'])
def list_assets():
    """
    Simple route to list a sample of assets for debugging purposes.
    """
    limit = request.args.get('limit', 20, type=int)
    
    try:
        # Fetch a sample of assets
        query = f"id>0 LIMIT {limit}" 
        response = rt_api_request("GET", f"/assets?query={urllib.parse.quote(query)}", current_app.config)
        assets = response.get("assets", [])
        
        # Extract just the relevant fields
        simplified_assets = []
        for asset in assets:
            asset_id = asset.get("id")
            name = asset.get("Name")
            simplified_asset = {
                "id": asset_id,
                "name": name,
                "status": asset.get("Status"),
                "created": str(asset.get("Created"))  # Convert to string to avoid serialization issues
            }
            
            # Add debug links
            simplified_asset["links"] = {
                "info": f"/labels/get-asset-info?id={asset_id}",
                "print": f"/labels/direct-print?id={asset_id}"
            }
            if name:
                simplified_asset["links"]["lookup"] = f"/labels/direct-lookup?name={name}"
                
            simplified_assets.append(simplified_asset)
        
        return custom_jsonify({
            "total_assets": len(simplified_assets),
            "assets": simplified_assets,
            "tips": [
                "Click on any asset's 'info' link to see detailed information",
                "Click on 'print' to generate a label directly"
            ]
        })
    except Exception as e:
        import traceback
        return custom_jsonify({
            "error": f"Failed to list assets: {str(e)}",
            "details": traceback.format_exc()
        })

@bp.route('/assets', methods=['POST'])
def search_assets_json():
    """
    API endpoint to search for assets using direct JSON queries.
    
    This endpoint accepts POST requests with JSON payload containing filter conditions.
    It's compatible with the RT API format for querying assets.
    
    Example:
    ```
    curl -H 'Authorization: token YOUR_TOKEN' -X POST -H "Content-Type: application/json" 
    -d '[{ "field": "Name", "operator": "LIKE", "value": "W12-" }]' http://localhost:8080/labels/assets
    ```
    
    Returns:
        JSON response with the matching assets
    """
    try:
        # Get the JSON payload from the request
        filter_conditions = request.get_json()
        
        if not filter_conditions:
            return custom_jsonify({
                "error": "No filter conditions provided"
            }), 400
            
        current_app.logger.info(f"Received asset filter conditions: {filter_conditions}")
        
        # Direct API call to RT using the same filter format
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        token = current_app.config.get('RT_TOKEN')
        
        url = f"{base_url}{api_endpoint}/assets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # Make the request directly to RT with the filter JSON
        import requests
        current_app.logger.debug(f"Making POST request to RT API: {url}")
        current_app.logger.debug(f"Using filter conditions: {filter_conditions}")
        
        response = requests.post(url, headers=headers, json=filter_conditions)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        current_app.logger.debug(f"RT API returned {len(result.get('items', []))} items")
        
        # Return the result as-is (just sanitize it for JSON serialization)
        from request_tracker_utils.utils.rt_api import sanitize_json
        return custom_jsonify(sanitize_json(result))
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"RT API request error: {e}")
        return custom_jsonify({
            "error": f"Failed to query RT API: {str(e)}",
            "error_type": type(e).__name__
        }), 500
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error processing asset search: {e}")
        return custom_jsonify({
            "error": f"Failed to process asset search: {str(e)}",
            "error_type": type(e).__name__,
            "details": traceback.format_exc().split('\n')
        }), 500

@bp.route('/debug', methods=['GET'])
def debug_page():
    """
    Display a debug page with asset lookup tools.
    """
    return render_template("debug.html")

@bp.route('/direct-print', methods=['GET'])
def direct_print():
    """
    A simpler approach to printing labels that bypasses complex lookups.
    This route accepts an asset ID directly.
    """
    asset_id = request.args.get('id')
    if not asset_id:
        return jsonify({"error": "Please provide an asset ID with the 'id' parameter"}), 400
    
    try:
        # Directly fetch asset data by ID
        asset_data = fetch_asset_data(asset_id, current_app.config)
        
        # Extract custom fields
        custom_fields = asset_data.get("CustomFields", [])
        
        # Build the asset_label_data object
        asset_label_data = {
            "id": asset_id,
            "name": asset_data.get("Name", "Unknown Asset"),
            "description": asset_data.get("Description", "No description available."),
            "tag": asset_data.get("Name", "Unknown Tag"),
            "internal_name": get_custom_field_value(custom_fields, "Internal Name"),
            "model_number": get_custom_field_value(custom_fields, "Model"),
            "funding_source": get_custom_field_value(custom_fields, "Funding Source"),
            "serial_number": get_custom_field_value(custom_fields, "Serial Number"),
            "label_width": current_app.config.get("LABEL_WIDTH_MM", 100) - 4,
            "label_height": current_app.config.get("LABEL_HEIGHT_MM", 62) - 4
        }
        
        # Generate QR Code with the RT URL
        rt_asset_url = f"{current_app.config.get('RT_URL')}/Asset/Display.html?id={asset_id}"
        asset_label_data["qr_code"] = generate_qr_code(rt_asset_url)
        
        # Generate Barcode
        asset_label_data["barcode"] = generate_barcode(asset_label_data["name"])
        
        # Render the label using the template
        return render_template("label.html", **asset_label_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in direct print: {e}")
        return jsonify({
            "error": f"Failed to generate label: {str(e)}",
            "tips": [
                "Make sure the asset ID exists",
                "Try using the debug endpoints (/labels/fetch-assets, /labels/direct-lookup?name=XX) to explore available assets"
            ]
        }), 500

@bp.route('/update-all', methods=['POST'])
def update_all_labels():
    """
    Updates the "Label" custom field to "Label" for all assets in Request Tracker.
    
    This route will search for all assets and update their Label custom field.
    
    Returns:
        JSON response with success or error information
    """
    try:
        # Get all assets (you may want to add pagination for large datasets)
        assets = search_assets("", current_app.config)
        current_app.logger.info(f"Found {len(assets)} assets to update")
        
        # Track successes and failures
        updated_count = 0
        failed_assets = []
        
        # Update each asset's Label custom field
        for asset in assets:
            asset_id = asset.get("id")
            asset_name = asset.get("Name", f"Asset #{asset_id}")
            
            try:
                # Update the Label custom field to "Label"
                update_asset_custom_field(asset_id, "Label", "Label", current_app.config)
                updated_count += 1
                current_app.logger.debug(f"Updated Label field for asset {asset_name} (ID: {asset_id})")
            except Exception as asset_error:
                current_app.logger.error(f"Failed to update asset {asset_name} (ID: {asset_id}): {asset_error}")
                failed_assets.append({"id": asset_id, "name": asset_name})
        
        # Prepare the response
        result = {
            "total_assets": len(assets),
            "updated_assets": updated_count,
            "failed_assets": len(failed_assets),
            "failed_details": failed_assets
        }
        
        # Determine if it was a partial or complete success
        if failed_assets:
            return jsonify({"status": "partial_success", "result": result}), 207  # Multi-Status
        else:
            return jsonify({"status": "success", "result": result}), 200
            
    except Exception as e:
        current_app.logger.error(f"Error updating labels: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500