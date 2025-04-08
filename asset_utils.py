from flask import Flask, request, jsonify, make_response, g, current_app
import requests
import json
import base64
from io import BytesIO
import sqlite3
from flask.cli import with_appcontext
import click
from datetime import datetime

def create_app(config_name=None):  #  config_name is a common pattern
    app = Flask(__name__)
    # ... load configuration ...

    # ... other app setup (e.g., blueprints, extensions) ...

    init_app(app)  # Initialize the database setup

    return app


# Configuration
RT_URL = "https://tickets.wc-12.com"  # Replace with your RT URL
API_ENDPOINT = "/REST/2.0"
RT_TOKEN = "1-7857-e7f98423b3b0e6e1da56f78722cc7ffe"  # Replace with your RT authentication token
LABEL_WIDTH_INCHES = 3.9
LABEL_HEIGHT_INCHES = 2.125

DATABASE = 'assets.db' # Name of the SQLite database file

PREFIX = 'W12-'
PADDING = 4

# --- Database Connection Handling (Standard Flask Pattern) ---

def get_db():
    """Connects to the specific database."""
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(
                DATABASE,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            # Return rows that behave like dicts
            g.db.row_factory = sqlite3.Row
            current_app.logger.debug("Database connection established.")
        except sqlite3.Error as e:
            current_app.logger.error(f"Database connection error: {e}")
            raise # Re-raise the exception to signal failure
    return g.db

def close_db(e=None):
    """Closes the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        current_app.logger.debug("Database connection closed.")

# --- Database Initialization ---

def init_db():
    """Initializes the database schema."""
    db = get_db()
    try:
        with current_app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf8'))
        current_app.logger.info("Database schema initialized.")
    except sqlite3.Error as e:
        current_app.logger.error(f"Error initializing database schema: {e}")
    except FileNotFoundError:
         current_app.logger.error("schema.sql not found. Cannot initialize database.")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    # Make sure close_db is called when the app context tears down
    app.teardown_appcontext(close_db)
    # Add the new command to the flask script
    app.cli.add_command(init_db_command)
    # You might also want to ensure the DB exists on first request or app start
    with app.app_context():
         # Example: Ensure DB file exists or basic check
         try:
             get_db() # Try connecting
         except Exception as e:
             app.logger.error(f"Failed initial database connection check: {e}")


def rt_api_request(method, endpoint, data=None):
    """
    Helper function to make requests to the RT API using a token.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {RT_TOKEN}",  # Use the token in the Authorization header
    }
    url = f"{RT_URL}{API_ENDPOINT}{endpoint}"

    try:
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during RT API request: {e}")
        return None

def create_pdf_label(asset_data):
    """
    Generates a PDF label from asset data.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib.pagesizes import letter
        from reportlab.graphics.barcode import code128
        from reportlab.lib.utils import ImageReader
        import qrcode
        from PIL import Image

        # Use a BytesIO buffer to store the PDF in memory
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(LABEL_WIDTH_INCHES * inch, LABEL_HEIGHT_INCHES * inch))

        # Generate QR code
        asset_url = f"{asset_data.get("url")}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=4)
        qr.add_data(asset_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill='black', back_color='white')
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_image_reader = ImageReader(qr_buffer)
        qr_img_width, qr_img_height = qr_image_reader.getSize()
        qr_img_width *= 1
        qr_img_height *= 1
        qr_x = LABEL_WIDTH_INCHES * inch - qr_img_width - 0.2 * inch
        qr_y = LABEL_HEIGHT_INCHES * inch - qr_img_height - 0.2 * inch
        c.drawImage(qr_image_reader, qr_x, qr_y, width=qr_img_width, height=qr_img_height)

        # Set font and size
        c.setFont("Helvetica-Bold", 12)
        header_text = "Western CUSD 12"
        header_width = c.stringWidth(header_text, "Helvetica-Bold", 12)
        c.drawString((LABEL_WIDTH_INCHES * inch - header_width) / 2, LABEL_HEIGHT_INCHES * inch - 0.2 * inch, header_text)

        # Set font and size for the rest of the text
        c.setFont("Helvetica", 10)
        y = LABEL_HEIGHT_INCHES * inch - 0.5 * inch  # Start below the header, leave a small margin

        # Helper function to add text, handles potential missing fields
        def add_text(label, value, y_offset):
            if value:  # check if the value exists
                c.setFont("Helvetica-Bold", 10)
                c.drawString(0.2 * inch, y_offset, f"{label}:")
                c.setFont("Helvetica", 10)
                c.drawString(0.7 * inch, y_offset, value)
                return y_offset - 0.2 * inch # Move y_offset
            return y_offset

        y = add_text("Tag", asset_data.get("Name", "N/A"), y)
        y = add_text("SN", asset_data.get("Serial Number", "N/A"), y)
        y = add_text("Model", asset_data.get("Model", "N/A"), y)
        y = add_text("Name", asset_data.get("Internal Name", "N/A"), y)

        # Generate barcode
        barcode_value = asset_data.get("Name", "N/A")
        barcode = code128.Code128(barcode_value, barHeight=0.25 * inch, barWidth=0.015 * inch)
        barcode_width = barcode.width
        # barcode_x = qr_x + qr_img_width - barcode_width
        barcode_x = LABEL_WIDTH_INCHES * inch - barcode_width - 0.1 * inch
        barcode.drawOn(c, barcode_x, 0.2 * inch)

        c.save()  # Save the PDF to the buffer

        pdf_data = buffer.getvalue()
        buffer.close()
        return base64.b64encode(pdf_data).decode('utf-8')  # Return as base64 string

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@app.route('/print_label')
def print_label():
    """
    Endpoint to retrieve asset information from RT and generate a label.
    """
    asset_id = request.args.get('assetId')
    if not asset_id:
        return jsonify({"error": "Missing assetId parameter"}), 400

    asset_endpoint = f"/asset/{asset_id}"
    asset_data = rt_api_request("GET", asset_endpoint)

    if asset_data is None:
        return jsonify({"error": "Failed to retrieve asset data from RT"}), 500

    # Print the received asset data for debugging
    print("Received asset data:", json.dumps(asset_data, indent=2))

    # Extract the required information, including custom fields.  Handle missing custom fields.
    extracted_data = {
        "Name": asset_data.get("Name"),
        "Serial Number": next((cf["values"][0] for cf in asset_data.get("CustomFields", []) if cf["name"] == "Serial Number" and cf["values"]), None),
        "Manufacturer": next((cf["values"][0] for cf in asset_data.get("CustomFields", []) if cf["name"] == "Manufacturer" and cf["values"]), None),
        "Model": next((cf["values"][0] for cf in asset_data.get("CustomFields", []) if cf["name"] == "Model" and cf["values"]), None),
        "Internal Name": next((cf["values"][0] for cf in asset_data.get("CustomFields", []) if cf["name"] == "Internal Name" and cf["values"]), None),
        "ID": asset_data.get("id"),
        "url": f"{RT_URL}/Asset/Display.html?id={asset_data.get("id")}",
    }

    # Print the extracted data for debugging
    print("Extracted data:", json.dumps(extracted_data, indent=2))

    pdf_base64 = create_pdf_label(extracted_data)

    if pdf_base64:
        pdf_data = base64.b64decode(pdf_base64)
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=asset_label.pdf' # Or 'attachment' for download
        return response
    else:
        return jsonify({"error": "Failed to generate PDF label"}), 500

@app.route('/next-asset-tag', methods=['GET'])
def next_asset_tag_route():
    """
    Provides the next available asset tag using the SQLite database.
    Finds the max tag_number, increments, inserts the new tag, and returns it.
    """
    current_app.logger.info("Request received for /next-asset-tag")
    db = get_db()
    cursor = db.cursor()
    next_number = 0
    full_asset_tag = None

    try:
        # --- Start Transaction ---
        cursor.execute("BEGIN")
        current_app.logger.debug("Transaction started for next tag.")

        # Find the maximum existing tag number
        cursor.execute("SELECT MAX(tag_number) FROM asset_tags")
        result = cursor.fetchone()
        max_number = result[0] if result and result[0] is not None else 0
        current_app.logger.info(f"Max existing tag number found: {max_number}")

        next_number = max_number + 1

        # Format the tag
        tag_number_part = f"{next_number:0{PADDING}d}"
        full_asset_tag = f"{PREFIX}{tag_number_part}"
        current_app.logger.info(f"Calculated next tag: {full_asset_tag} (Number: {next_number})")

        # Insert the new tag record
        # generated_at will use the default CURRENT_TIMESTAMP
        cursor.execute(
            "INSERT INTO asset_tags (tag_number, full_tag) VALUES (?, ?)",
            (next_number, full_asset_tag)
        )
        current_app.logger.info(f"Inserted new tag record for {full_asset_tag}")

        # --- Commit Transaction ---
        db.commit()
        current_app.logger.debug("Transaction committed for next tag.")

        return jsonify({"asset_tag": full_asset_tag})

    except sqlite3.IntegrityError as e:
        db.rollback() # Rollback on error
        current_app.logger.error(f"Database integrity error (likely duplicate tag attempt?) for tag number {next_number}: {e}")
        return jsonify({"error": "Failed to generate unique asset tag due to conflict"}), 500
    except sqlite3.Error as e:
        db.rollback() # Rollback on error
        current_app.logger.error(f"Database error generating next asset tag: {e}")
        return jsonify({"error": "Database error generating asset tag"}), 500
    except Exception as e:
        # Catch other potential errors (e.g., formatting)
        db.rollback() # Rollback on error
        current_app.logger.error(f"Unexpected error generating next asset tag: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/confirm-asset-tag', methods=['POST'])
def confirm_asset_tag_route():
    """
    Confirms usage of an asset tag and stores the RT Asset ID in the database.
    Expects JSON: {"asset_tag": "W12-####", "rt_asset_id": 123}
    """
    current_app.logger.info("Request received for /confirm-asset-tag")
    if not request.is_json:
        current_app.logger.warning("Confirmation request is not JSON.")
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    asset_tag = data.get('asset_tag')
    rt_asset_id = data.get('rt_asset_id')

    if not asset_tag or rt_asset_id is None: # Check rt_asset_id could be 0
        current_app.logger.warning(f"Missing 'asset_tag' or 'rt_asset_id' in confirmation: {data}")
        return jsonify({"error": "Missing required fields: asset_tag, rt_asset_id"}), 400

    # Optional: Basic validation of rt_asset_id format if needed
    try:
        rt_asset_id = int(rt_asset_id)
    except ValueError:
         current_app.logger.warning(f"Invalid non-integer 'rt_asset_id' received: {rt_asset_id}")
         return jsonify({"error": "Invalid rt_asset_id format"}), 400

    db = get_db()
    cursor = db.cursor()

    try:
        # --- Start Transaction ---
        cursor.execute("BEGIN")
        current_app.logger.debug(f"Transaction started for confirming tag {asset_tag}.")

        # Update the record, setting rt_asset_id and confirmed_at timestamp
        # Only update if it hasn't been confirmed already (rt_asset_id IS NULL)
        timestamp_now = datetime.now() # Get consistent timestamp
        cursor.execute(
            """UPDATE asset_tags
               SET rt_asset_id = ?, confirmed_at = ?
               WHERE full_tag = ? AND rt_asset_id IS NULL""",
            (rt_asset_id, timestamp_now, asset_tag)
        )

        rows_affected = cursor.rowcount
        current_app.logger.debug(f"Rows affected by confirmation update for tag {asset_tag}: {rows_affected}")

        if rows_affected == 1:
            # --- Commit Transaction ---
            db.commit()
            current_app.logger.info(f"Successfully confirmed tag '{asset_tag}' linked to RT Asset ID '{rt_asset_id}'.")
            return jsonify({"status": "acknowledged", "tag": asset_tag, "rt_id": rt_asset_id}), 200
        elif rows_affected == 0:
            # Tag not found OR it was already confirmed
            db.rollback() # No changes were made, but good practice
            current_app.logger.warning(f"Confirmation failed: Tag '{asset_tag}' not found or already confirmed.")
            # Check if the tag exists at all to give a better error
            cursor.execute("SELECT rt_asset_id FROM asset_tags WHERE full_tag = ?", (asset_tag,))
            existing_record = cursor.fetchone()
            if existing_record and existing_record['rt_asset_id'] is not None:
                 return jsonify({"error": f"Tag {asset_tag} already confirmed for RT ID {existing_record['rt_asset_id']}"}), 409 # Conflict
            else:
                 return jsonify({"error": f"Tag {asset_tag} not found"}), 404 # Not Found
        else:
             # Should not happen with unique full_tag, but handle defensively
             db.rollback()
             current_app.logger.error(f"Unexpected number of rows ({rows_affected}) affected by confirmation update for tag {asset_tag}.")
             return jsonify({"error": "Unexpected database state during confirmation"}), 500

    except sqlite3.Error as e:
        db.rollback() # Rollback on error
        current_app.logger.error(f"Database error confirming asset tag {asset_tag}: {e}")
        return jsonify({"error": "Database error confirming asset tag"}), 500
    except Exception as e:
        db.rollback() # Rollback on error
        current_app.logger.error(f"Unexpected error confirming asset tag {asset_tag}: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
