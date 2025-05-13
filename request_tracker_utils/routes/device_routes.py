from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, send_file
from ..utils.rt_api import find_asset_by_name, get_assets_by_owner, fetch_asset_data, fetch_user_data, rt_api_request, update_asset_custom_field
import logging
import urllib.parse
import requests
import json
import time
import traceback
import os
import csv
import datetime

bp = Blueprint('devices', __name__)
logger = logging.getLogger(__name__)

@bp.route('/check-in', strict_slashes=False)
def asset_checkin():
    """Display the device check-in form without a pre-filled asset name"""
    return render_template('device_checkin.html')

@bp.route('/check-in/<asset_name>')
def asset_details(asset_name):
    """Display asset details and check-in form"""
    return render_template('device_checkin.html', asset_name=asset_name)

@bp.route('/api/asset/<asset_name>')
def get_asset_info(asset_name):
    """API endpoint to get asset and related devices info"""
    try:
        logger.info("\n")
        logger.info("==========================================")
        logger.info(f"Device Lookup - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Request for: {asset_name}")
        logger.info("==========================================")
        
        # Make request directly to RT API using asset name
        base_url = current_app.config.get('RT_URL')
        api_endpoint = current_app.config.get('API_ENDPOINT')
        token = current_app.config.get('RT_TOKEN')
        
        url = f"{base_url}{api_endpoint}/assets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"token {token}"
        }
        
        # First try exact match using JSON filter format
        filter_data = [
            {
                "field": "Name",
                "operator": "=",
                "value": asset_name
            }
        ]
        
        logger.info(f"Making POST request with exact match filter: {json.dumps(filter_data)}")
        response = requests.post(url, headers=headers, json=filter_data)
        response.raise_for_status()
        
        # Process the response
        result = response.json()
        logger.info(f"POST exact match response: {json.dumps(result)}")
        
        # Look for assets in the response
        items = []
        if 'items' in result:
            items = result.get('items', [])
        elif 'assets' in result:
            items = result.get('assets', [])
            
        if items and len(items) > 0:
            logger.info(f"Found {len(items)} assets with exact match")
            matching_asset = items[0]  # Take the first match
        else:
            # If exact match fails, try LIKE match
            logger.info("No exact match found, trying LIKE operator")
            
            # Try with LIKE operator
            filter_data = [
                {
                    "field": "Name",
                    "operator": "LIKE",
                    "value": asset_name
                }
            ]
            
            logger.info(f"Making POST request with LIKE filter: {json.dumps(filter_data)}")
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
            
            if not items:
                logger.warning(f"No asset found with name: {asset_name}")
                return jsonify({
                    "error": f"No asset found with name: {asset_name}",
                    "tip": "Check the asset name and try again"
                }), 404
                
            matching_asset = items[0]  # Take the first match
            
        # Get the complete asset data
        asset_id = matching_asset.get('id')
        logger.info(f"Fetching complete data for asset ID: {asset_id}")
        asset_data = fetch_asset_data(asset_id)

        # Extract owner information and log it
        owner_data = asset_data.get('Owner', {})
        logger.info(f"\n=== Owner Information ===")
        logger.info(f"Raw owner data: {json.dumps(owner_data, indent=2)}")
        
        owner_info = {
            'id': None,
            'name': None,
            'raw': owner_data,
            'display_name': None,
            'numeric_id': None  # Add field for numeric ID
        }
        
        # Handle different Owner field formats and fetch user details
        if isinstance(owner_data, dict):
            owner_id = owner_data.get('id')
            logger.info(f"Owner ID from dict: {owner_id}")
            owner_info['id'] = owner_id
            try:
                # Fetch full user details
                logger.info(f"Fetching user details for ID: {owner_id}")
                user_data = fetch_user_data(owner_id)
                logger.info(f"User data retrieved: {json.dumps(user_data, indent=2)}")
                owner_info['name'] = owner_data.get('Name', owner_data.get('id'))
                owner_info['display_name'] = user_data.get('RealName', user_data.get('Name', owner_info['id']))
                
                # Extract numeric ID from hyperlinks
                hyperlinks = user_data.get('_hyperlinks', [])
                for link in hyperlinks:
                    if link.get('ref') == 'self' and link.get('type') == 'user':
                        owner_info['numeric_id'] = str(link.get('id'))
                        logger.info(f"Found numeric user ID: {owner_info['numeric_id']}")
                        break
                
            except Exception as e:
                logger.error(f"Error fetching user details: {e}")
                owner_info['name'] = owner_data.get('id')
                owner_info['display_name'] = owner_data.get('id')
        elif isinstance(owner_data, str):
            owner_info['id'] = owner_data
            try:
                # Fetch full user details
                logger.info(f"Fetching user details for ID: {owner_data}")
                user_data = fetch_user_data(owner_data)
                logger.info(f"User data retrieved: {json.dumps(user_data, indent=2)}")
                owner_info['name'] = owner_data
                owner_info['display_name'] = user_data.get('RealName', user_data.get('Name', owner_data))
                
                # Extract numeric ID from hyperlinks
                hyperlinks = user_data.get('_hyperlinks', [])
                for link in hyperlinks:
                    if link.get('ref') == 'self' and link.get('type') == 'user':
                        owner_info['numeric_id'] = str(link.get('id'))
                        logger.info(f"Found numeric user ID: {owner_info['numeric_id']}")
                        break
                
            except Exception as e:
                logger.error(f"Error fetching user details: {e}")
                owner_info['name'] = owner_data
                owner_info['display_name'] = owner_data

        logger.info(f"Final owner_info: {json.dumps(owner_info, indent=2)}")

        # Print owner information
        logger.info(f"\n=== Owner Information [{time.strftime('%H:%M:%S')}] ===")
        logger.info(f"Owner ID: {owner_info['id']}")
        logger.info(f"Owner Name: {owner_info['display_name']}")
        logger.info(f"Owner Numeric ID: {owner_info['numeric_id']}")

        # Get other devices for this owner if we have one and if the owner is not "Nobody"
        other_assets = []
        if owner_info['id'] == "Nobody" or owner_info['name'] == "Nobody":
            # If owner is Nobody, don't look up other assets
            logger.info(f"Owner is 'Nobody' - skipping lookup of other devices")
        elif owner_info['numeric_id']:  # Use numeric_id instead of id
            logger.info(f"\n=== Looking up other assets for owner {owner_info['numeric_id']} ===")
            try:
                other_assets = get_assets_by_owner(owner_info['numeric_id'], exclude_id=asset_id)
                logger.info(f"Found {len(other_assets)} other assets")
                
                # Log details about each asset found
                for asset in other_assets:
                    logger.info(f"Other asset found:")
                    logger.info(f"  ID: {asset.get('id')}")
                    logger.info(f"  Name: {asset.get('Name')}")
                    logger.info(f"  Status: {asset.get('Status')}")
                    logger.info(f"  Type: {next((cf['values'][0] for cf in asset.get('CustomFields', []) if cf['name'] == 'Type'), 'N/A')}")
                
            except Exception as e:
                logger.error(f"Error getting other assets: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
            # Ensure custom fields are included in other assets
            for other_asset in other_assets:
                if 'id' in other_asset and 'CustomFields' not in other_asset:
                    try:
                        logger.info(f"Fetching full details for other asset {other_asset['id']}")
                        full_asset_data = fetch_asset_data(other_asset['id'])
                        other_asset.update(full_asset_data)
                        logger.info(f"Successfully updated other asset {other_asset['id']} with full details")
                    except Exception as e:
                        logger.error(f"Error fetching details for other asset {other_asset['id']}: {e}")
        else:
            logger.warning("No owner ID available to lookup other assets")

        logger.info("----------------------------------------\n")
        
        # Include the full asset data with prominent owner info
        return jsonify({
            "asset": asset_data,
            "owner": owner_info,
            "other_assets": other_assets
        })

    except Exception as e:
        logger.error(f"Error getting asset info: {e}")
        return jsonify({
            "error": "Failed to get asset information",
            "details": str(e)
        }), 500

@bp.route('/api/update-asset', methods=['POST'])
def update_asset():
    """API endpoint to update asset owner and create linked tickets"""
    try:
        data = request.json
        asset_id = data.get('assetId')
        set_owner_to_nobody = data.get('setOwnerToNobody', False)
        create_ticket = data.get('createTicket', False)
        ticket_description = data.get('ticketDescription', '')
        broken_screen = data.get('brokenScreen', False)
        
        logger.info(f"Update asset request for asset ID: {asset_id}")
        logger.info(f"Set owner to Nobody: {set_owner_to_nobody}")
        logger.info(f"Create ticket: {create_ticket}")
        logger.info(f"Ticket description: {ticket_description}")
        logger.info(f"Broken screen: {broken_screen}")
        
        # Fetch current asset data to get details needed for ticket creation
        current_asset = fetch_asset_data(asset_id)
        if not current_asset:
            return jsonify({
                "error": f"Failed to fetch asset data for ID: {asset_id}"
            }), 404
            
        asset_name = current_asset.get('Name', '')
        
        # Build the final description text
        final_description = ticket_description
        
        # Add broken screen information if checked and not already in description
        if (broken_screen and "broken screen" not in final_description.lower()):
            if final_description:
                final_description += "\n\nBroken Screen"
            else:
                final_description = "Broken Screen"
        
        # Get owner info before changing it (for logging purposes)
        owner_info = {}
        owner_data = current_asset.get('Owner', {})
        if isinstance(owner_data, dict) and 'id' in owner_data:
            try:
                user_data = fetch_user_data(owner_data.get('id'))
                owner_info = {
                    'id': owner_data.get('id'),
                    'display_name': user_data.get('RealName', user_data.get('Name', owner_data.get('id')))
                }
            except Exception as e:
                logger.error(f"Error fetching owner info for logging: {e}")
                owner_info = {'id': owner_data.get('id'), 'display_name': owner_data.get('id')}
        elif isinstance(owner_data, str) and owner_data:
            try:
                user_data = fetch_user_data(owner_data)
                owner_info = {
                    'id': owner_data,
                    'display_name': user_data.get('RealName', user_data.get('Name', owner_data))
                }
            except Exception as e:
                logger.error(f"Error fetching owner info for logging: {e}")
                owner_info = {'id': owner_data, 'display_name': owner_data}
        else:
            owner_info = {'id': None, 'display_name': 'None'}
        
        # Update the asset owner to "Nobody" if requested
        if set_owner_to_nobody:
            try:
                logger.info(f"Setting owner to Nobody for asset {asset_id}")
                # Per RT API - "Nobody" is the username for empty/unassigned owners
                update_data = {
                    "Owner": "Nobody"
                }
                
                # Send PUT request to update asset
                response = rt_api_request("PUT", f"/asset/{asset_id}", data=update_data)
                logger.info(f"Owner update response: {json.dumps(response)}")
            except Exception as e:
                logger.error(f"Error updating asset owner: {e}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "error": f"Failed to update asset owner: {str(e)}"
                }), 500
        
        # Create linked ticket if requested
        ticket_id = None
        # Create a ticket if explicitly requested or if there's damage information
        should_create_ticket = create_ticket or broken_screen or (final_description and len(final_description.strip()) > 0)
        
        if should_create_ticket:
            try:
                logger.info(f"Creating linked ticket for asset {asset_id}")
                
                # Create a ticket in the Device Repair queue
                ticket_data = {
                    "Queue": "Device Repair",
                    "Subject": f"Device Check-in: {asset_name}",
                    "Content": final_description or "No description provided",
                    "Refers-To": f"asset:{asset_id}"  # Use Refers-To for link to asset instead of AssetId
                }
                
                # Use the specialized create_ticket function instead of rt_api_request directly
                from ..utils.rt_api import create_ticket
                logger.info(f"Creating ticket with data: {json.dumps(ticket_data)}")
                ticket_response = create_ticket(ticket_data)
                logger.info(f"Ticket creation response: {json.dumps(ticket_response)}")
                
                # Extract ticket ID from response
                if "id" in ticket_response:
                    ticket_id = ticket_response.get("id")
                    logger.info(f"Created ticket ID: {ticket_id}")
                else:
                    logger.error(f"Ticket creation failed - no ID in response: {ticket_response}")
                
            except Exception as e:
                logger.error(f"Error creating ticket: {e}")
                logger.error(traceback.format_exc())
                return jsonify({
                    "error": f"Failed to create ticket: {str(e)}",
                    "assetUpdated": set_owner_to_nobody  # Indicate if asset was updated
                }), 500
        
        # Log the check-in to CSV if the asset owner was updated
        if set_owner_to_nobody:
            try:
                # Get the current user from the session or default to "web-user"
                current_user = "web-user"  # This can be enhanced later with actual user authentication
                
                # Import and use the CSV logger with fallback location handling
                from ..utils.csv_logger import DeviceCheckInLogger
                
                # Try to use the default configured directory first
                try:
                    csv_logger = DeviceCheckInLogger()
                except (OSError, FileNotFoundError) as e:
                    logger.warning(f"Could not use configured log directory for check-in logging: {e}")
                    
                    # Use a directory in the Flask instance folder instead
                    from flask import current_app
                    instance_logs_dir = os.path.join(current_app.instance_path, 'logs')
                    os.makedirs(instance_logs_dir, exist_ok=True)
                    logger.info(f"Using alternative log directory for check-in logging: {instance_logs_dir}")
                    csv_logger = DeviceCheckInLogger(log_dir=instance_logs_dir)
                
                # Log the check-in
                log_result = csv_logger.log_checkin(
                    asset_data=current_asset,
                    owner_info=owner_info,
                    ticket_id=ticket_id,
                    description=final_description,
                    broken_screen=broken_screen,
                    user=current_user
                )
                if log_result:
                    logger.info(f"Device check-in logged to CSV for asset {asset_name}")
                else:
                    logger.error(f"Failed to log device check-in for asset {asset_name}")
            except Exception as e:
                # Log the error but don't fail the request
                logger.error(f"Error logging check-in to CSV: {e}")
                logger.error(traceback.format_exc())
        
        return jsonify({
            "success": True,
            "assetId": asset_id,
            "ownerUpdated": set_owner_to_nobody,
            "ticketCreated": ticket_id is not None,
            "ticketId": ticket_id
        })
        
    except Exception as e:
        logger.error(f"Error in update_asset: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Failed to process request: {str(e)}"
        }), 500

@bp.route('/checkin-logs')
def checkin_logs():
    """Display a list of available check-in log files"""
    try:
        # Import and use the CSV logger
        from ..utils.csv_logger import DeviceCheckInLogger
        from ..utils.db import get_db_connection
        
        # Create a temporary directory in the instance folder if the configured directory isn't working
        try:
            csv_logger = DeviceCheckInLogger()
        except (OSError, FileNotFoundError) as e:
            logger.warning(f"Could not use configured log directory: {e}")
            
            # Use a directory in the Flask instance folder instead
            from flask import current_app
            instance_logs_dir = os.path.join(current_app.instance_path, 'logs')
            os.makedirs(instance_logs_dir, exist_ok=True)
            logger.info(f"Using alternative log directory: {instance_logs_dir}")
            csv_logger = DeviceCheckInLogger(log_dir=instance_logs_dir)
        
        # Get the CSV file logs
        file_logs = csv_logger.get_available_logs()
        
        # Get unique dates from the database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT DISTINCT date FROM device_logs ORDER BY date DESC")
            db_dates = [row['date'] for row in cursor.fetchall()]
            
            # For dates that don't exist as CSV files but exist in database, add them to the logs list
            existing_dates = {log['filename'][9:-4] for log in file_logs}  # Extract dates from filenames
            
            for date_str in db_dates:
                if date_str not in existing_dates:
                    # This date exists in DB but not as a CSV file
                    try:
                        # Get device count for this date
                        cursor.execute("SELECT COUNT(*) as count FROM device_logs WHERE date = ?", (date_str,))
                        row_count = cursor.fetchone()['count']
                        
                        # Convert to datetime for formatting
                        log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                        # Format as a readable date
                        display_date = log_date.strftime('%A, %B %d, %Y')
                        
                        # Create a new log entry
                        filename = f"checkins_{date_str}.csv"
                        file_logs.append({
                            'filename': filename,
                            'path': None,  # No physical file exists
                            'date': display_date,
                            'size': 0,  # No file size since it's only in database
                            'modified': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'device_count': row_count,
                            'db_only': True  # Flag to indicate this is only in the database
                        })
                    except Exception as date_error:
                        logger.error(f"Error processing database date {date_str}: {date_error}")
        finally:
            conn.close()
            
        # Sort all logs by date (newest first)
        file_logs.sort(key=lambda x: x['filename'], reverse=True)
        
        return render_template('checkin_logs.html', logs=file_logs)
        
    except Exception as e:
        logger.error(f"Error displaying check-in logs: {e}")
        logger.error(traceback.format_exc())
        
        # Check if the error.html template exists before trying to render it
        template_exists = os.path.exists(os.path.join(
            current_app.root_path, 'templates', 'error.html'
        ))
        
        if template_exists:
            return render_template('error.html', error=f"Failed to load check-in logs: {str(e)}")
        else:
            # Fallback to a simple error message if the template doesn't exist
            return f"<h1>Error</h1><p>Failed to load check-in logs: {str(e)}</p>", 500

@bp.route('/download-checkin-log/<filename>')
def download_checkin_log(filename):
    """Download a specific check-in log file"""
    try:
        # Validate filename (only allow checkins_*.csv pattern)
        if not filename.startswith('checkins_') or not filename.endswith('.csv'):
            return jsonify({
                "error": "Invalid log filename"
            }), 400
            
        # Extract the date from the filename (checkins_YYYY-MM-DD.csv)
        date_str = filename[9:-4]  # Remove "checkins_" prefix and ".csv" suffix
        
        # Option 1: Try to get the file directly (legacy support)
        possible_paths = []
        
        # Path in the configured working directory
        working_dir = current_app.config.get('WORKING_DIR', '/var/lib/request-tracker-utils')
        possible_paths.append(os.path.join(working_dir, 'logs', filename))
        
        # Path in the Flask instance folder (which we might be using as fallback)
        instance_logs_dir = os.path.join(current_app.instance_path, 'logs')
        possible_paths.append(os.path.join(instance_logs_dir, filename))
        
        # Check the nested logs folder that was found in the workspace structure
        nested_logs_dir = os.path.join(current_app.instance_path, 'logs', 'logs')
        possible_paths.append(os.path.join(nested_logs_dir, filename))
        
        # Find the first existing file path
        log_file_path = None
        for path in possible_paths:
            if os.path.exists(path) and os.path.isfile(path):
                log_file_path = path
                logger.info(f"Found log file at: {log_file_path}")
                break
        
        # Option 2: If file doesn't exist or we're using newer database logs, export from the database
        from ..utils.csv_logger import DeviceCheckInLogger
        csv_logger = DeviceCheckInLogger()
        
        if log_file_path:
            # If the file exists, use that directly
            return send_file(
                log_file_path, 
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )
        else:
            # Generate CSV content from database
            csv_data = csv_logger.export_logs_to_csv(date_str=date_str)
            
            if not csv_data:
                return jsonify({
                    "error": f"No log data found for date: {date_str}"
                }), 404
                
            # Create an in-memory file
            from io import BytesIO
            buffer = BytesIO()
            buffer.write(csv_data.encode('utf-8'))
            buffer.seek(0)
            
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )
        
    except Exception as e:
        logger.error(f"Error downloading check-in log: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Failed to download log file: {str(e)}"
        }), 500

@bp.route('/preview-checkin-log/<filename>')
def preview_checkin_log(filename):
    """Preview a specific check-in log file in the browser"""
    try:
        # Validate filename (only allow checkins_*.csv pattern)
        if not filename.startswith('checkins_') or not filename.endswith('.csv'):
            return jsonify({
                "error": "Invalid log filename"
            }), 400
            
        # Extract the date from the filename (checkins_YYYY-MM-DD.csv)
        date_str = filename[9:-4]  # Remove "checkins_" prefix and ".csv" suffix
        
        # Parse date for display (format: checkins_YYYY-MM-DD.csv)
        try:
            # Convert to datetime for formatting
            log_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
            # Format as a readable date
            display_date = log_date.strftime('%A, %B %d, %Y')  # e.g., "Thursday, May 9, 2025"
        except ValueError:
            display_date = date_str
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)  # Show 50 rows per page by default
        
        # Option 1: Try to get logs from the database first
        from ..utils.csv_logger import DeviceCheckInLogger
        csv_logger = DeviceCheckInLogger()
        db_logs = csv_logger.get_logs_by_date(date_str)
        
        if db_logs:
            # We have logs in the database, use those
            logger.info(f"Found {len(db_logs)} log entries in the database for date {date_str}")
            
            # Calculate pagination
            total_rows = len(db_logs)
            total_pages = max(1, (total_rows + per_page - 1) // per_page)
            
            # Clamp current page to valid range
            page = max(1, min(page, total_pages))
            
            # Get the data for the current page
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total_rows)
            page_logs = db_logs[start_idx:end_idx]
            
            # Convert logs to a format compatible with the template
            headers = [
                'Timestamp', 'Date', 'Time', 'Asset ID', 'Asset Tag', 
                'Device Type', 'Serial Number', 'Previous Owner', 'Ticket ID',
                'Has Ticket', 'Ticket Description', 'Broken Screen', 'Checked By'
            ]
            
            # Format rows as lists (like CSV reader output)
            rows = []
            for log in page_logs:
                row = [
                    log.get('timestamp', ''),
                    log.get('date', ''),
                    log.get('time', ''),
                    log.get('asset_id', ''),
                    log.get('asset_tag', ''),
                    log.get('device_type', ''),
                    log.get('serial_number', ''),
                    log.get('previous_owner', ''),
                    log.get('ticket_id', ''),
                    log.get('has_ticket', ''),
                    log.get('ticket_description', ''),
                    log.get('broken_screen', ''),
                    log.get('checked_by', ''),
                ]
                rows.append(row)
            
            # Calculate pagination values for display
            start_row = (page - 1) * per_page + 1
            end_row = min(page * per_page, total_rows)
            
            # Render the template with data from the database
            logger.info(f"Rendering preview from database logs, page {page} of {total_pages}")
            return render_template(
                'csv_preview.html', 
                filename=filename,
                display_date=display_date,
                headers=headers, 
                rows=rows,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                total_rows=total_rows,
                start_row=start_row,
                end_row=end_row,
                from_database=True
            )
        
        # Option 2: If not in database, try to get the file directly
        possible_paths = []
        
        # Path in the configured working directory
        working_dir = current_app.config.get('WORKING_DIR', '/var/lib/request-tracker-utils')
        possible_paths.append(os.path.join(working_dir, 'logs', filename))
        
        # Path in the Flask instance folder (which we might be using as fallback)
        instance_logs_dir = os.path.join(current_app.instance_path, 'logs')
        possible_paths.append(os.path.join(instance_logs_dir, filename))
        
        # Check the nested logs folder that was found in the workspace structure
        nested_logs_dir = os.path.join(current_app.instance_path, 'logs', 'logs')
        possible_paths.append(os.path.join(nested_logs_dir, filename))
        
        # Find the first existing file path
        log_file_path = None
        for path in possible_paths:
            if os.path.exists(path) and os.path.isfile(path):
                log_file_path = path
                logger.info(f"Found log file at: {log_file_path}")
                break
        
        if not log_file_path:
            logger.error(f"Log file not found in filesystem and no database entries. Searched in: {possible_paths}")
            return jsonify({
                "error": f"No log data found for date: {date_str}"
            }), 404
        
        # Read the CSV file content - with pagination support
        csv_data = []
        headers = []
        
        with open(log_file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)  # Get the header row
            
            # Store all rows (potentially inefficient for very large files)
            all_rows = list(reader)
            
            # Calculate pagination
            total_rows = len(all_rows)
            total_pages = max(1, (total_rows + per_page - 1) // per_page)
            
            # Clamp current page to valid range
            page = max(1, min(page, total_pages))
            
            # Get the rows for the current page
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total_rows)
            
            csv_data = all_rows[start_idx:end_idx]
        
        # Calculate pagination values for display
        start_row = (page - 1) * per_page + 1
        end_row = min(page * per_page, total_rows)
        
        # Return the preview template with the CSV data
        logger.info(f"Rendering preview from CSV file, page {page} of {total_pages}")
        return render_template(
            'csv_preview.html', 
            filename=filename,
            display_date=display_date,
            headers=headers, 
            rows=csv_data,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            total_rows=total_rows,
            start_row=start_row,
            end_row=end_row,
            from_database=False
        )
            
    except Exception as e:
        logger.error(f"Error previewing check-in log: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Failed to preview log file: {str(e)}"
        }), 500