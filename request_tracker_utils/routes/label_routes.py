from flask import Blueprint, request, jsonify, render_template, current_app, Response
import json
import io
import base64
import urllib.parse
import qrcode
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
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")
    qr_buffer.close()
    return qr_base64

def generate_barcode(content):
    """
    Generate a barcode image and return as base64 string.
    
    Args:
        content (str): Content to encode in the barcode
        
    Returns:
        str: Base64 encoded barcode image
    """
    barcode = Code128(content, writer=ImageWriter())
    barcode_writer_options = {
        "module_width": 4,
        "module_height": 50,
        "write_text": False,
        "dpi": 600
    }
    barcode_buffer = io.BytesIO()
    barcode.write(barcode_buffer, options=barcode_writer_options)
    barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")
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
            
            # Use the direct lookup approach - fetch all assets and filter locally
            if direct_lookup:
                current_app.logger.info("Using direct lookup approach")
                # Get a limited list of assets (1000 should be enough for most instances)
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
                        current_app.logger.error(f"No asset found with name similar to: {asset_name}")
                        return jsonify({
                            "error": f"No asset found with name: {asset_name}",
                            "tip": "Try checking the asset name in RT or use an asset ID instead."
                        }), 404
            else:
                # Use the standard find_asset_by_name function
                asset = find_asset_by_name(asset_name, current_app.config)
                
                if not asset:
                    current_app.logger.error(f"No asset found with name: {asset_name}")
                    return jsonify({
                        "error": f"No asset found with name: {asset_name}",
                        "tip": "Try again with ?direct=true added to the URL or use an asset ID instead."
                    }), 404
                    
                # Get the asset ID from the found asset
                asset_id = asset.get('id')
                current_app.logger.info(f"Found asset ID: {asset_id} for name: {asset_name}")
        
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
        rt_asset_url = f"https://tickets.wc-12.com/Asset/Display.html?id={asset_id}"
        asset_label_data["qr_code"] = generate_qr_code(rt_asset_url)
        
        # Generate Barcode
        asset_label_data["barcode"] = generate_barcode(asset_label_data["name"])
        
        current_app.logger.debug(f"Asset label data: {json.dumps(asset_label_data, indent=4)}")

    except Exception as e:
        current_app.logger.error(f"Error processing asset data: {e}")
        return jsonify({"error": "Failed to process asset data"}), 500

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
                        # Standard lookup method
                        current_app.logger.info(f"Using standard lookup for asset: {asset_name}")
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
            rt_asset_url = f"{current_app.config.get('RT_URL')}/Asset/Display.html?id={asset_id}"
            label_data["qr_code"] = generate_qr_code(rt_asset_url)
            
            # Generate Barcode
            label_data["barcode"] = generate_barcode(label_data["name"])
            
            labels_data.append(label_data)
        
        # Render the batch labels template with all label data
        context = {'labels': labels_data}
        if warning_message:
            context['warning'] = warning_message
            
        return render_template('batch_labels.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error processing batch labels: {e}")
        return render_template('batch_labels_form.html', 
                              error=f"Failed to process batch labels: {str(e)}")

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
    """
    search_term = request.args.get('q', '')
    limit = request.args.get('limit', 20, type=int)
    
    if not search_term:
        return custom_jsonify({
            "error": "Please provide a search term with the 'q' parameter"
        })
    
    try:
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
            results.append({
                "id": asset.get("id"),
                "name": asset.get("Name"),
                "status": asset.get("Status"),
                "description": asset.get("Description")
            })
        
        return custom_jsonify({
            "search_term": search_term,
            "total_results": len(results),
            "results": results
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