from flask import Blueprint, jsonify, request, current_app, render_template
from datetime import datetime
import os
import re
from request_tracker_utils.utils.rt_api import update_asset_custom_field, fetch_asset_data, rt_api_request

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
        # Use absolute paths with the working directory
        working_dir = config.get("WORKING_DIR", "/var/lib/request-tracker-utils")
        # Ensure working directory exists
        os.makedirs(working_dir, exist_ok=True)
        self.sequence_file = os.path.join(working_dir, "asset_tag_sequence.txt")
        self.log_file = os.path.join(working_dir, "asset_tag_confirmations.log")
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
            
    def get_last_updated_time(self):
        """
        Get the last modification time of the sequence file.
        
        Returns:
            datetime: Last modification time or None if file doesn't exist
        """
        if os.path.exists(self.sequence_file):
            mod_time = os.path.getmtime(self.sequence_file)
            return datetime.fromtimestamp(mod_time)
        return None
        
    def get_log_entries(self, limit=10):
        """
        Get the most recent log entries.
        
        Args:
            limit (int): Maximum number of entries to retrieve
            
        Returns:
            list: List of dictionaries with log entry data
        """
        entries = []
        
        if not os.path.exists(self.log_file):
            return entries
            
        # Pattern to match log entry format: ISO timestamp - Asset Tag: X, Request Tracker ID: Y
        pattern = r"^(.*?) - Asset Tag: (.*?), Request Tracker ID: (.*?)$"
        
        try:
            with open(self.log_file, "r") as f:
                # Read all lines, reverse to get newest first, and limit
                lines = f.readlines()
                lines.reverse()
                lines = lines[:limit]
                
                for line in lines:
                    line = line.strip()
                    match = re.match(pattern, line)
                    if match:
                        timestamp_str, asset_tag, rt_id = match.groups()
                        try:
                            # Parse ISO timestamp
                            timestamp = datetime.fromisoformat(timestamp_str)
                            # Format for display
                            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                            
                            entries.append({
                                "timestamp": formatted_time,
                                "asset_tag": asset_tag,
                                "rt_id": rt_id
                            })
                        except ValueError:
                            # Skip entries with invalid timestamps
                            continue
                            
        except Exception as e:
            # Return partial results if there's an error
            return entries
            
        return entries


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

    # After confirming the asset tag, update the asset name in RT
    try:
        # Fetch the asset data to ensure it exists
        asset_data = fetch_asset_data(request_tracker_id, current_app.config)
        
        # Update the asset name to match the asset tag
        data = {
            "Name": asset_tag
        }
        
        # Make the API request to update the asset
        rt_api_request("PUT", f"/asset/{request_tracker_id}", data=data, config=current_app.config)
        
        current_app.logger.info(f"Updated asset {request_tracker_id} name to {asset_tag}")
    except Exception as e:
        # Log the error but don't fail the request
        current_app.logger.error(f"Failed to update asset name in RT: {e}")
        # Include warning in response
        return jsonify({
            "message": "Asset tag confirmation logged successfully.",
            "warning": f"Failed to update asset name in RT: {str(e)}"
        })
    
    return jsonify({"message": "Asset tag confirmation logged successfully. Asset name updated in RT."})


@bp.route('/update-asset-name', methods=['POST'])
def update_asset_name_route():
    """
    Updates an asset's name in Request Tracker.
    
    Example usage with curl:
        curl -X POST -H "Content-Type: application/json" -d '{"asset_id": "123", "asset_name": "W12-0001"}' http://localhost:8080/update-asset-name
    """
    data = request.get_json()
    
    # Validate the input
    asset_id = data.get("asset_id")
    asset_name = data.get("asset_name")
    
    if not asset_id or not asset_name:
        return jsonify({"error": "Both 'asset_id' and 'asset_name' are required."}), 400
    
    try:
        # Fetch the asset data to ensure it exists
        asset_data = fetch_asset_data(asset_id, current_app.config)
        
        # Update the asset name
        update_data = {
            "Name": asset_name
        }
        
        # Make the API request to update the asset
        response = rt_api_request("PUT", f"/asset/{asset_id}", data=update_data, config=current_app.config)
        
        current_app.logger.info(f"Updated asset {asset_id} name to {asset_name}")
        
        return jsonify({
            "message": f"Asset name updated successfully to '{asset_name}'",
            "old_name": asset_data.get("Name", "Unknown"),
            "new_name": asset_name,
            "asset_id": asset_id
        })
    except Exception as e:
        current_app.logger.error(f"Failed to update asset name in RT: {e}")
        return jsonify({"error": f"Failed to update asset name: {str(e)}"}), 500


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


@bp.route('/webhook/asset-created', methods=['POST'])
def asset_created_webhook():
    """
    Webhook endpoint for Request Tracker to call when a new asset is created.
    
    This webhook automatically assigns the next available asset tag to the newly created asset.
    
    To configure RT to call this webhook:
    1. Create a Scrip in RT:
      - Condition: On Create
      - Stage: TransactionCreate
      - Action: User Defined
      - Template: User Defined
    2. In the Custom Condition code, add:
      ```
      return 1 if $self->TransactionObj->Type eq 'Create' && $self->TransactionObj->ObjectType eq 'RT::Asset';
      return 0;
      ```
    3. In the Custom Action code, add:
      ```
      my $asset_id = $self->TransactionObj->ObjectId;
      my $webhook_url = 'http://your-server.com/webhook/asset-created';
      
      my $ua = LWP::UserAgent->new;
      my $response = $ua->post(
        $webhook_url,
        Content_Type => 'application/json',
        Content => encode_json({
          asset_id => $asset_id,
          event => 'create',
          timestamp => time()
        })
      );
      
      return 1;
      ```
    """
    # Get JSON data from the webhook 
    webhook_data = request.get_json()
    
    # Basic validation
    if not webhook_data:
        return jsonify({"error": "No data provided"}), 400
    
    asset_id = webhook_data.get("asset_id")
    if not asset_id:
        return jsonify({"error": "Missing asset_id in webhook data"}), 400
    
    # Log the webhook call
    current_app.logger.info(f"Received asset created webhook for asset ID: {asset_id}")
    current_app.logger.debug(f"Webhook data: {webhook_data}")
    
    try:
        # Get the next available asset tag
        manager = AssetTagManager(current_app.config)
        next_tag = manager.get_next_tag()
        
        # Fetch the asset data to ensure it exists
        try:
            asset_data = fetch_asset_data(asset_id, current_app.config)
            current_app.logger.info(f"Asset exists with current name: {asset_data.get('Name', 'Unknown')}")
        except Exception as fetch_error:
            current_app.logger.error(f"Failed to fetch asset data: {fetch_error}")
            return jsonify({"error": f"Asset not found: {str(fetch_error)}"}), 404
        
        # Update the asset name to the next tag
        try:
            data = {
                "Name": next_tag
            }
            
            # Make the API request to update the asset
            rt_api_request("PUT", f"/asset/{asset_id}", data=data, config=current_app.config)
            
            current_app.logger.info(f"Updated asset {asset_id} name to {next_tag}")
            
            # Increment the sequence number
            manager.increment_sequence()
            
            # Log the asset tag assignment
            manager.log_confirmation(next_tag, asset_id)
            
            return jsonify({
                "message": f"Asset tag {next_tag} assigned to asset {asset_id}",
                "asset_id": asset_id,
                "asset_tag": next_tag,
                "previous_name": asset_data.get("Name", "Unknown")
            })
        except Exception as update_error:
            current_app.logger.error(f"Failed to update asset name: {update_error}")
            return jsonify({"error": f"Failed to update asset: {str(update_error)}"}), 500
    except Exception as e:
        current_app.logger.error(f"Error processing asset created webhook: {e}")
        return jsonify({"error": f"Failed to process webhook: {str(e)}"}), 500


@bp.route('/admin', methods=['GET'])
def asset_tag_admin():
    """
    Display the asset tag administration page.
    
    This page allows users to view the current asset tag sequence and update it.
    It also shows recent asset tag assignments.
    """
    manager = AssetTagManager(current_app.config)
    
    # Get current sequence info
    sequence = manager.get_current_sequence()
    next_tag = manager.get_next_tag()
    prefix = manager.prefix
    
    # Get last updated time
    last_updated = manager.get_last_updated_time()
    if last_updated:
        last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_updated = "Unknown"
    
    # Get recent log entries
    log_entries = manager.get_log_entries(limit=20)
    
    # RT URL for linking to assets
    rt_url = current_app.config.get('RT_URL', 'https://tickets.example.com')
    
    return render_template(
        'asset_tag_admin.html',
        sequence=sequence,
        next_tag=next_tag,
        prefix=prefix,
        last_updated=last_updated,
        log_entries=log_entries,
        rt_url=rt_url
    )