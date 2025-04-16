from flask import Blueprint, jsonify, request, current_app
from datetime import datetime
import os

bp = Blueprint('tag_routes', __name__)

class AssetTagManager:
    """
    Manages asset tag sequence and logging operations.
    """
    def __init__(self, config):
        """
        Initialize the AssetTagManager with configuration.
        
        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.sequence_file = "asset_tag_sequence.txt"
        self.log_file = "asset_tag_confirmations.log"
        self.prefix = config.get("PREFIX", "W12-")
    
    def get_current_sequence(self):
        """
        Read the current sequence number from the file.
        
        Returns:
            int: Current sequence number
        """
        if not os.path.exists(self.sequence_file):
            # If the file doesn't exist, initialize it with 0
            with open(self.sequence_file, "w") as f:
                f.write("0")
        
        with open(self.sequence_file, "r") as f:
            return int(f.read().strip())
    
    def set_sequence(self, number):
        """
        Set the sequence number in the file.
        
        Args:
            number (int): The sequence number to set
            
        Raises:
            IOError: If unable to write to the file
        """
        with open(self.sequence_file, "w") as f:
            f.write(str(number))
    
    def get_next_tag(self):
        """
        Get the next asset tag without incrementing the sequence.
        
        Returns:
            str: The next asset tag in the sequence
        """
        current_number = self.get_current_sequence()
        return f"{self.prefix}{current_number:04d}"
    
    def increment_sequence(self):
        """
        Increment the sequence number by 1.
        
        Returns:
            int: The new sequence number
        """
        current_number = self.get_current_sequence()
        new_number = current_number + 1
        self.set_sequence(new_number)
        return new_number
    
    def log_confirmation(self, asset_tag, request_tracker_id):
        """
        Log the confirmation of an asset tag.
        
        Args:
            asset_tag (str): The asset tag
            request_tracker_id (str): The RT ID
            
        Raises:
            IOError: If unable to write to the log file
        """
        log_entry = f"{datetime.now().isoformat()} - Asset Tag: {asset_tag}, Request Tracker ID: {request_tracker_id}\n"
        with open(self.log_file, "a") as log_file:
            log_file.write(log_entry)


@bp.route('/next-asset-tag', methods=['GET'])
def next_asset_tag_route():
    """
    Returns the next asset tag based on the current sequence.
    """
    manager = AssetTagManager(current_app.config)
    next_tag = manager.get_next_tag()
    return jsonify({"next_asset_tag": next_tag})


@bp.route('/confirm-asset-tag', methods=['POST'])
def confirm_asset_tag_route():
    """
    Logs the confirmation of an asset tag and its associated Request Tracker ID.
    Increments the sequence number in the file.
    
    Example usage with curl:
        curl -X POST -H "Content-Type: application/json" -d '{"asset_tag": "W12-0001", "request_tracker_id": "RT12345"}' http://localhost:8080/confirm-asset-tag
    """
    data = request.get_json()

    # Validate the input
    asset_tag = data.get("asset_tag")
    request_tracker_id = data.get("request_tracker_id")

    if not asset_tag or not request_tracker_id:
        return jsonify({"error": "Both 'asset_tag' and 'request_tracker_id' are required."}), 400

    manager = AssetTagManager(current_app.config)
    
    # Verify that the confirmed asset tag matches the expected next tag
    expected_tag = manager.get_next_tag()
    if asset_tag != expected_tag:
        return jsonify({"error": f"Invalid asset tag. Expected: {expected_tag}"}), 400

    try:
        # Increment the sequence number
        manager.increment_sequence()
        
        # Log the asset tag confirmation
        manager.log_confirmation(asset_tag, request_tracker_id)
    except IOError as e:
        return jsonify({"error": f"Failed to process asset tag confirmation: {str(e)}"}), 500

    return jsonify({"message": "Asset tag confirmation logged successfully."})


@bp.route('/reset-asset-tag', methods=['POST'])
def reset_asset_tag_route():
    """
    Resets the asset tag sequence to a specified starting number.

    Example usage with curl:
        curl -X POST -H "Content-Type: application/json" -d '{"start_number": 100}' http://localhost:8080/reset-asset-tag
    """
    data = request.get_json()
    new_start_number = data.get("start_number", 0)

    # Validate that the new_start_number is an integer
    if not isinstance(new_start_number, int) or new_start_number < 0:
        return jsonify({"error": "Invalid start_number. It must be a non-negative integer."}), 400

    manager = AssetTagManager(current_app.config)
    
    try:
        # Set the new sequence number
        manager.set_sequence(new_start_number)
        
        # Generate the new starting tag
        new_tag = manager.get_next_tag()
    except IOError as e:
        return jsonify({"error": f"Failed to reset asset tag sequence: {str(e)}"}), 500

    return jsonify({"message": "Asset tag sequence reset successfully.", "new_start_tag": new_tag})