#!/usr/bin/env python3
import sys
import logging
import urllib.parse
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import rt_api_request, update_asset_custom_field, logger as rt_logger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set RT API logger to INFO level
rt_logger.setLevel(logging.INFO)

def save_progress(progress_data):
    """Save progress to a file"""
    progress_file = Path.home() / '.rtutils' / 'label_update_progress.json'
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f)
    # logger.info(f"Progress saved to {progress_file}")

def load_progress():
    """Load progress from file"""
    progress_file = Path.home() / '.rtutils' / 'label_update_progress.json'
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return None

def update_asset_with_timeout(asset_id, asset_name, config, timeout=45):
    """Attempt to update an asset with a timeout"""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Update timed out for asset {asset_id}")
    
    # Set timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    
    try:
        # Use the correct format for updating custom fields
        data = {
            "CustomFields": {"Label": "Print Label"}
        }
        rt_api_request("PUT", f"/asset/{asset_id}", data=data, config=config)
        signal.alarm(0)  # Disable alarm
        return True
    except TimeoutError as e:
        logger.error(str(e))
        return False
    except Exception as e:
        logger.error(f"Error updating asset {asset_id}: {str(e)}")
        return False
    finally:
        signal.alarm(0)  # Ensure alarm is disabled

def update_all_labels():
    """Update assets in RT that don't have Label custom field set to 'Print Label'"""
    # Create config dict from imported settings
    config = {
        'RT_URL': RT_URL,
        'API_ENDPOINT': API_ENDPOINT,
        'RT_TOKEN': RT_TOKEN
    }
    
    logger.info("Starting update of asset labels")
    
    # Get total count of assets that need updating
    query = "CF.Label IS NULL OR CF.Label != 'Print Label'"
    encoded_query = urllib.parse.quote(query)
    
    try:
        response = rt_api_request(
            "GET", 
            f"/assets?query={encoded_query}",
            config=config
        )
        total_assets = response.get('total', 0)
        logger.info(f"Found {total_assets} assets that need Label field updated")
        logger.info("===================================")
    except Exception as e:
        logger.error(f"Error getting total asset count: {e}")
        total_assets = 0

    # Load previous progress if it exists
    progress = load_progress()
    if progress:
        start_page = progress.get('next_page', 1)
        success_count = progress.get('success_count', 0)
        error_count = progress.get('error_count', 0)
        skipped_count = progress.get('skipped_count', 0)
        processed_ids = set(progress.get('processed_ids', []))
        logger.info(f"Resuming from page {start_page}")
        logger.info(f"Progress: {success_count + error_count + skipped_count}/{total_assets} assets processed")
        logger.info(f"    Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
        logger.info("===================================")
    else:
        start_page = 1
        success_count = 0
        error_count = 0
        skipped_count = 0
        processed_ids = set()
    
    try:
        page = start_page
        
        while True:
            logger.info(f"Fetching page {page} of assets from RT...")
            
            # Use AssetSQL query to find assets where Label is not 'Print Label' or is not set
            query = "CF.Label IS NULL OR CF.Label != 'Print Label'"
            encoded_query = urllib.parse.quote(query)
            
            # Make GET request with AssetSQL query
            try:
                response = rt_api_request(
                    "GET", 
                    f"/assets?query={encoded_query}&page={page}",
                    config=config
                )
            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                raise
                
            # Extract items from response
            items = []
            if 'items' in response:
                items = response['items']
            elif 'assets' in response:
                items = response['assets']
                
            if not items:
                logger.info("No more assets found that need updating, ending pagination")
                break
                
            logger.info(f"Processing {len(items)} assets from page {page}")
            
            # Process each asset in this page
            for item in items:
                try:
                    asset_id = item.get("id")
                    
                    # Skip if we've already processed this asset
                    if asset_id in processed_ids:
                        logger.debug(f"Skipping already processed asset")
                        continue
                        
                    asset_name = item.get("Name", "Unknown")
                    
                    # Double check the current Label value
                    custom_fields = item.get("CustomFields", {})
                    current_label = custom_fields.get("Label", "")
                    
                    if current_label == "Print Label":
                        logger.debug(f"Skipping asset {asset_id} ({asset_name}) - Label already set correctly")
                        skipped_count += 1
                    else:
                        # logger.info(f"Processing asset {asset_id} ({asset_name})")
                        if update_asset_with_timeout(asset_id, asset_name, config):
                            success_count += 1
                        else:
                            error_count += 1
                        
                    # Add to processed set
                    processed_ids.add(asset_id)
                    
                    # Save progress after each asset
                    save_progress({
                        'next_page': page,
                        'success_count': success_count,
                        'error_count': error_count,
                        'skipped_count': skipped_count,
                        'processed_ids': list(processed_ids)
                    })
                    
                    # Brief progress update every 10 assets
                    total_processed = success_count + error_count + skipped_count
                    if total_processed % 10 == 0:
                        percent = (total_processed / total_assets * 100) if total_assets > 0 else 0
                        logger.info(f"Progress: {total_processed}/{total_assets} ({percent:.1f}%)")
                    
                    time.sleep(.05)
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to update asset ID {item.get('id', 'Unknown')}: {e}")
            
            logger.info(f"Completed page {page}")
            total_processed = success_count + error_count + skipped_count
            percent = (total_processed / total_assets * 100) if total_assets > 0 else 0
            logger.info(f"Progress: {total_processed}/{total_assets} ({percent:.1f}%)")
            logger.info(f"Status - Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
            logger.info("===================================")
            
            # Check pagination info
            total_pages = response.get('pages', 1)
            if page >= total_pages:
                logger.info(f"Reached last page ({page} of {total_pages})")
                break
                
            page += 1
            
            # Pause between pages
            logger.info("Pausing for 1 second before next page...")
            time.sleep(1)
        
        # Log final results
        logger.info("Update complete!")
        logger.info(f"Successfully updated: {success_count}")
        logger.info(f"Skipped (already set): {skipped_count}")
        logger.info(f"Failed updates: {error_count}")
        
        # Clear progress file on successful completion
        progress_file = Path.home() / '.rtutils' / 'label_update_progress.json'
        if progress_file.exists():
            progress_file.unlink()
            logger.info("Cleared progress file")
        
    except Exception as e:
        logger.error(f"Error updating assets: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_all_labels()