from flask import Blueprint, request, jsonify, render_template, current_app
import requests
import json
import qrcode
import io
import base64
from barcode import Code128
from barcode.writer import ImageWriter

bp = Blueprint('label_routes', __name__)

@bp.route('/print_label')
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

    Flask Configurations:
        RT_URL (str): Base URL for the RT API.
        API_ENDPOINT (str): Endpoint for accessing asset data.
        RT_TOKEN (str): Authentication token for the RT API.

    Logs:
        Logs an error message if the request to the RT API fails.

    Templates:
        label.html: Template used to render the label with the asset data.
    """
    asset_id = request.args.get('assetId')
    current_app.logger.debug(f"Received assetId: {asset_id if asset_id else 'None'}")
    if not asset_id:
        current_app.logger.debug("Missing assetId parameter in the request")
        return jsonify({"error": "Missing assetId parameter"}), 400

    
    # Construct the RT API URL
    rt_url = f"{current_app.config['RT_URL']}{current_app.config['API_ENDPOINT']}/asset/{asset_id}"
    # current_app.logger.debug(f"Constructed RT API URL: {rt_url}")

    # Set up headers for authentication
    headers = {
        "Authorization": f"token {current_app.config['RT_TOKEN']}",
        "Content-Type": "application/json"
    }
    # current_app.logger.debug(f"Request headers: {headers}")

    # Make the API request
    try:
        response = requests.get(rt_url, headers=headers)
        response.raise_for_status()  # Raise an error for HTTP codes 4xx/5xx
        asset_data = response.json()  # Parse the JSON response
        
        pretty_asset_data = json.dumps(asset_data, indent=4)
        # current_app.logger.debug(f"Received asset data: {pretty_asset_data}")

        # Build the asset_label_data object
        asset_label_data = {
            "name": asset_data.get("Name", "Unknown Asset"),
            "description": asset_data.get("Description", "No description available."),
            "tag": asset_data.get("Name", "Unknown Tag"),
            "internal_name": next(
            (field.get("values", [None])[0] for field in asset_data.get("CustomFields", [])
             if field.get("name") == "Internal Name" and field.get("values")), "N/A"
            ),
            "model_number": next(
            (field.get("values", [None])[0] for field in asset_data.get("CustomFields", [])
             if field.get("name") == "Model" and field.get("values")), "N/A"
            ),
            "funding_source": next(
            (field.get("values", [None])[0] for field in asset_data.get("CustomFields", [])
             if field.get("name") == "Funding Source" and field.get("values")), "N/A"
            ),
            "serial_number": next(
            (field.get("values", [None])[0] for field in asset_data.get("CustomFields", [])
             if field.get("name") == "Serial Number" and field.get("values")), "N/A"
            ),
            "label_width": current_app.config.get("LABEL_WIDTH_MM", 100) - 4,  # Default to 100mm
            "label_height": current_app.config.get("LABEL_HEIGHT_MM", 62) - 4  # Default to 62mm
        }


        # Generate QR Code with the RT URL
        rt_asset_url = f"https://tickets.wc-12.com/Asset/Display.html?id={asset_id}"
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(rt_asset_url)  # Add the RT URL to the QR code
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white")

        # Convert QR Code to Base64
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")
        qr_buffer.close()

        # Generate Barcode
        barcode = Code128(asset_label_data["name"], writer=ImageWriter())
        barcode_writer_options = {
            "module_width": 4,  # Adjust the width of each bar (default is 0.2)
            "module_height": 50,  # Adjust the height of the barcode (default is 15)
            "write_text": False,  # Disable text under the barcode
            "dpi": 600  # Increase the resolution of the barcode
        }
        barcode_buffer = io.BytesIO()
        barcode.write(barcode_buffer, options=barcode_writer_options)
        barcode_base64 = base64.b64encode(barcode_buffer.getvalue()).decode("utf-8")
        barcode_buffer.close()

        current_app.logger.debug(f"Asset label data: {json.dumps(asset_label_data, indent=4)}")


        # Add QR Code and Barcode to asset_label_data
        asset_label_data["qr_code"] = qr_base64
        asset_label_data["barcode"] = barcode_base64

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching asset data: {e}")
        return jsonify({"error": "Failed to fetch asset data from RT"}), 500

    # Render the label using the template
    current_app.logger.debug("Rendering the label template with asset label data")
    return render_template("label.html", **asset_label_data)