from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import os

bp = Blueprint('tag_routes', __name__)

# File paths for storing the asset tag sequence and log
ASSET_TAG_FILE = "asset_tag_sequence.txt"
LOG_FILE = "asset_tag_confirmations.log"

@bp.route('/next-asset-tag', methods=['GET'])
def next_asset_tag_route():
    """
    Returns the next asset tag based on the current sequence stored in a file.
    """
    prefix = current_app.config.get("PREFIX", "W12-")

    # Read the current sequence number from the file
    if not os.path.exists(ASSET_TAG_FILE):
        # If the file doesn't exist, initialize it with 0
        with open(ASSET_TAG_FILE, "w") as f:
            f.write("0")

    with open(ASSET_TAG_FILE, "r") as f:
        current_number = int(f.read().strip())

    # Generate the next asset tag (without incrementing the sequence)
    next_tag = f"{prefix}{current_number:04d}"

    return jsonify({"next_asset_tag": next_tag})


@bp.route('/confirm-asset-tag', methods=['POST'])
def confirm_asset_tag_route():
    """
    Logs the confirmation of an asset tag and its associated Request Tracker ID.
    Increments the sequence number in the file.
    """

    """
    Example usage with curl:

        Confirm an asset tag with a Request Tracker ID:
        curl -X POST -H "Content-Type: application/json" -d '{"asset_tag": "W12-0001", "request_tracker_id": "RT12345"}' http://localhost:8080/confirm-asset-tag
    """

    data = request.get_json()

    # Validate the input
    asset_tag = data.get("asset_tag")
    request_tracker_id = data.get("request_tracker_id")

    if not asset_tag or not request_tracker_id:
        return jsonify({"error": "Both 'asset_tag' and 'request_tracker_id' are required."}), 400

    # Read the current sequence number from the file
    if not os.path.exists(ASSET_TAG_FILE):
        return jsonify({"error": "Asset tag sequence file not found."}), 500

    with open(ASSET_TAG_FILE, "r") as f:
        current_number = int(f.read().strip())

    # Verify that the confirmed asset tag matches the expected next tag
    prefix = current_app.config.get("PREFIX", "W12-")
    expected_tag = f"{prefix}{current_number:04d}"
    if asset_tag != expected_tag:
        return jsonify({"error": f"Invalid asset tag. Expected: {expected_tag}"}), 400

    # Increment the sequence number and update the file
    with open(ASSET_TAG_FILE, "w") as f:
        f.write(str(current_number + 1))

    # Log the asset tag and Request Tracker ID to a log file
    log_entry = f"{datetime.now().isoformat()} - Asset Tag: {asset_tag}, Request Tracker ID: {request_tracker_id}\n"

    try:
        with open(LOG_FILE, "a") as log_file:
            log_file.write(log_entry)
    except Exception as e:
        return jsonify({"error": f"Failed to write to log file: {str(e)}"}), 500

    return jsonify({"message": "Asset tag confirmation logged successfully."})


@bp.route('/reset-asset-tag', methods=['POST'])
def reset_asset_tag_route():
    """
    Resets the asset tag sequence to a specified starting number.

    Example usage with curl:

        Reset the asset tag sequence to start from 100:
        curl -X POST -H "Content-Type: application/json" -d '{"start_number": 100}' http://localhost:8080/reset-asset-tag
    """
    
    prefix = current_app.config.get("PREFIX", "W12-")
    data = request.get_json()
    new_start_number = data.get("start_number", 0)

    # Validate that the new_start_number is an integer
    if not isinstance(new_start_number, int) or new_start_number < 0:
        return jsonify({"error": "Invalid start_number. It must be a non-negative integer."}), 400

    # Write the new sequence number to the file
    try:
        with open(ASSET_TAG_FILE, "w") as f:
            f.write(str(new_start_number))
    except Exception as e:
        return jsonify({"error": f"Failed to reset asset tag sequence: {str(e)}"}), 500

    # Generate the new starting tag
    new_tag = f"{prefix}{new_start_number:04d}"

    return jsonify({"message": "Asset tag sequence reset successfully.", "new_start_tag": new_tag})