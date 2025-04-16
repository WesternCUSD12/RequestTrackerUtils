from flask import Blueprint, request, jsonify, render_template, current_app
import json
import io
import base64
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter
from request_tracker_utils.utils.rt_api import fetch_asset_data, search_assets, update_asset_custom_field

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

@bp.route('/print')
def print_label():
    """
    Handles the request to print a label for a specific asset.

    This function retrieves the asset ID from the request arguments, fetches
    the corresponding asset data from the RT API, and renders a label using
    the "label.html" template.

    Returns:
        Response: A Flask response object containing the rendered label template
        or an error message with the appropriate HTTP status code.

    Raises:
        400 Bad Request: If the 'assetId' parameter is missing in the request.
        500 Internal Server Error: If there is an error fetching asset data
        from the RT API.
    """
    asset_id = request.args.get('assetId')
    current_app.logger.debug(f"Received assetId: {asset_id if asset_id else 'None'}")
    
    if not asset_id:
        current_app.logger.debug("Missing assetId parameter in the request")
        return jsonify({"error": "Missing assetId parameter"}), 400
        
    try:
        # Fetch asset data from RT API
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