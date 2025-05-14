import requests
import time
import threading
import json
import os
import random
import traceback
from flask import current_app
from functools import lru_cache
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from request_tracker_utils.config import WORKING_DIR  # Import the working directory from config

# Define explicitly which functions can be imported from this module
__all__ = [
    'PersistentAssetCache',
    'asset_cache',
    'create_retry_session',
    'sanitize_json',
    'rt_api_request',
    'fetch_asset_data', 
    'search_assets',
    'find_asset_by_name',
    'update_asset_custom_field',
    'update_user_custom_field',
    'get_assets_by_owner',
    'fetch_user_data',
    'create_ticket'
]

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class PersistentAssetCache:
    def __init__(self, max_size=1500, ttl=259200):  # Cache up to 1500 assets for 72 hours (259200 seconds)
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.RLock()
        
        # Use a platform-independent path in the user's home directory
        try:
            # Primary approach: Use the application's working directory if available
            from flask import current_app
            instance_path = current_app.instance_path
            cache_dir = Path(instance_path) / 'cache'
            logger.info(f"Using app instance directory for cache: {cache_dir}")
        except (ImportError, RuntimeError):
            # Fallback: Use the user's home directory
            cache_dir = Path.home() / '.rtutils' / 'cache'
            logger.info(f"Using home directory for cache: {cache_dir}")
        
        self.cache_file = cache_dir / 'asset_cache.json'
        
        # Ensure cache directory exists
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created or verified cache directory: {self.cache_file.parent}")
        except Exception as e:
            logger.warning(f"Failed to create cache directory at {self.cache_file.parent}: {e}")
            # Final fallback: Use a temporary directory
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / 'rtutils_cache'
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = temp_dir / 'asset_cache.json'
            logger.info(f"Using temporary directory for cache: {self.cache_file}")
        
        # Load existing cache from file
        self._load_cache()
        
        # Start background threads
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.save_thread = threading.Thread(target=self._periodic_save_loop, daemon=True)
        self.cleanup_thread.start()
        self.save_thread.start()

    def get(self, key):
        """Get an item from cache if it exists and is not expired"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() < entry['expires']:
                    logger.debug(f"Cache hit for key: {key}")
                    return entry['data']
                else:
                    # Remove expired entry
                    logger.debug(f"Removing expired entry for key: {key}")
                    del self.cache[key]
        return None

    def set(self, key, value):
        """Add an item to the cache with expiration"""
        with self.lock:
            # If cache is full, remove oldest entry
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.items(), key=lambda x: x[1]['expires'])[0]
                del self.cache[oldest_key]
            
            self.cache[key] = {
                'data': value,
                'expires': time.time() + self.ttl
            }
            logger.debug(f"Added/updated cache entry for key: {key}")
            self._save_cache()

    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self._save_cache()
            logger.info("Cache cleared")

    def _cleanup_loop(self):
        """Background thread to clean expired entries"""
        while True:
            time.sleep(300)  # Check every 5 minutes
            self._cleanup_expired()

    def _periodic_save_loop(self):
        """Background thread to periodically save cache to disk"""
        while True:
            time.sleep(600)  # Save every 10 minutes
            self._save_cache()

    def _cleanup_expired(self):
        """Remove all expired entries from cache"""
        now = time.time()
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry['expires'] < now]
            for key in expired_keys:
                del self.cache[key]
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")
                self._save_cache()

    def _save_cache(self):
        """Save cache to disk"""
        try:
            with self.lock:
                # Create a copy of the cache with serializable data
                cache_data = {
                    'last_updated': time.time(),
                    'entries': {
                        k: {
                            'data': v['data'],
                            'expires': v['expires']
                        } for k, v in self.cache.items()
                    }
                }
                
                # Save to file atomically using a temporary file
                temp_file = self.cache_file.with_suffix('.tmp')
                with open(temp_file, 'w') as f:
                    json.dump(cache_data, f)
                temp_file.replace(self.cache_file)
                logger.debug("Cache saved to disk")
        except Exception as e:
            logger.error(f"Error saving cache to disk: {e}")

    def _load_cache(self):
        """Load cache from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    now = time.time()
                    
                    # Only load non-expired entries
                    valid_entries = {
                        k: v for k, v in cache_data.get('entries', {}).items()
                        if v['expires'] > now
                    }
                    
                    with self.lock:
                        self.cache = valid_entries
                    
                    expired_count = len(cache_data.get('entries', {})) - len(valid_entries)
                    logger.info(f"Loaded {len(valid_entries)} valid entries from disk cache")
                    if expired_count > 0:
                        logger.info(f"Skipped {expired_count} expired entries")
        except Exception as e:
            logger.error(f"Error loading cache from disk: {e}")
            # Start with empty cache if load fails
            self.cache = {}

# Initialize the cache
asset_cache = PersistentAssetCache()

def create_retry_session(retries=5, backoff_factor=1.0, status_forcelist=(500, 502, 503, 504)):
    """Create a requests Session with retry configuration
    
    Args:
        retries (int): Number of retries before giving up
        backoff_factor (float): Factor to apply between attempts. Wait will be:
            {backoff factor} * (2 ** ({number of total retries} - 1))
        status_forcelist (tuple): Status codes that trigger a retry
    """
    session = requests.Session()
    
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE', 'HEAD']),
        respect_retry_after_header=True,
        # Add jitter to prevent thundering herd
        backoff_jitter=random.uniform(0, 0.1)
    )
    
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def sanitize_json(obj):
    """
    Sanitize objects that can't be directly serialized to JSON
    
    Args:
        obj: The object to sanitize
        
    Returns:
        A JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json(item) for item in obj]
    # Convert datetime objects to strings
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    # Convert timedelta objects to seconds
    elif hasattr(obj, 'total_seconds'):
        return f"{obj.total_seconds()} seconds"
    return obj

def rt_api_request(method, endpoint, data=None, config=None):
    """
    Make a request to the RT API with retry logic.
    
    Args:
        method (str): HTTP method (GET, POST, etc.)
        endpoint (str): API endpoint path
        data (dict, optional): Data to send with the request
        config (dict, optional): Configuration dictionary
        
    Returns:
        dict: JSON response from the API
        
    Raises:
        requests.exceptions.RequestException: If the request fails after all retries
    """
    if config is None:
        config = current_app.config
    
    base_url = config.get('RT_URL')
    api_endpoint = config.get('API_ENDPOINT')
    token = config.get('RT_TOKEN')
    
    url = f"{base_url}{api_endpoint}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",  # Explicitly request JSON response
        "Authorization": f"token {token}"
    }
    
    try:
        # Create a session with retry logic
        session = create_retry_session()
        
        # Add timeout to prevent hanging
        response = session.request(
            method, 
            url, 
            headers=headers, 
            json=data, 
            verify=True,
            timeout=(30, 90)  # (connect timeout, read timeout)
        )
        
        # Log retry attempts and response details
        if response.history:
            logger.info(f"Request succeeded after {len(response.history)} retries")
            
        # Check content type of response
        content_type = response.headers.get('content-type', '')
        if 'application/json' not in content_type.lower():
            logger.error(f"Unexpected content type: {content_type}")
            logger.error(f"Response content: {response.text[:500]}...")  # Log first 500 chars
            raise requests.exceptions.RequestException(
                f"API returned non-JSON response (content-type: {content_type})"
            )
            
        if response.status_code >= 400:
            logger.error(f"Error response from RT API: Status {response.status_code}")
            logger.error(f"URL: {url}")
            logger.error(f"Method: {method}")
            if data:
                logger.error(f"Request data: {json.dumps(data)}")
            logger.error(f"Response headers: {dict(response.headers)}")
            try:
                logger.error(f"Response content: {response.text}")
            except:
                logger.error("Could not decode response content")
        
        response.raise_for_status()
        
        # Ensure we can parse the response as JSON
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {e}")
            logger.error(f"Response content: {response.text[:500]}...")
            raise requests.exceptions.RequestException(
                f"Failed to parse API response as JSON: {str(e)}"
            )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"RT API request failed: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            logger.error(f"Error response content: {e.response.text}")
            logger.error(f"Error response headers: {dict(e.response.headers) if e.response else 'No headers'}")
        raise

def fetch_asset_data(asset_id, config=None, use_cache=False):
    """
    Fetch asset data from the RT API (caching disabled).
    
    Args:
        asset_id (str): The ID of the asset to fetch
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        use_cache (bool, optional): Whether to use and update the cache, defaults to False
        
    Returns:
        dict: Asset data
        
    Raises:
        Exception: If there's an error fetching the asset data
    """
    if not asset_id:
        raise ValueError("Asset ID is missing or invalid")
    
    try:
        # Log the API request details
        if config is None:
            current_app.logger.info(f"Fetching asset data for ID: {asset_id} from RT API")
            
        response = rt_api_request("GET", f"/asset/{asset_id}", config=config)
        
        # Validate response has expected fields
        if not response:
            raise ValueError(f"Empty response from RT API for asset ID: {asset_id}")
            
        # Check if the response has a Name field
        if "Name" not in response:
            # Log response for debugging
            if config is None:
                current_app.logger.warning(f"Response for asset ID {asset_id} is missing Name field: {response}")
                
        return response
        
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error fetching asset data: {e}")
        raise Exception(f"Failed to fetch asset data from RT: {e}")
    except Exception as e:
        if config is None:
            current_app.logger.error(f"Error processing asset data for ID {asset_id}: {str(e)}")
        raise Exception(f"Error processing asset data: {str(e)}")

def search_assets(query, config=None, try_post_fallback=True, use_cache=False):
    """
    Search for assets in RT using a query with pagination support (caching disabled).
    """
    logger.info(f"Starting asset search with query: {query}")
    start_time = time.time()
    
    all_assets = []
    page = 1
    
    try:
        # Convert query to JSON search format
        if isinstance(query, list):
            search_condition = query
            logger.info(f"Using provided search conditions: {json.dumps(search_condition)}")
        elif query == "id>0":
            search_condition = [{
                "field": "id",
                "operator": ">=",
                "value": 0
            }]
            logger.info("Using id>0 search condition to fetch all assets")
        elif "=" in query:
            field, value = query.split("=", 1)
            field = field.strip()
            value = value.strip("' ")
            search_condition = [{
                "field": field,
                "operator": "=",
                "value": value
            }]
            logger.info(f"Using equals search condition: {field}={value}")
        elif "LIKE" in query.upper():
            field, value = query.upper().split("LIKE", 1)
            field = field.strip()
            value = value.strip("' ")
            search_condition = [{
                "field": field,
                "operator": "LIKE",
                "value": value
            }]
            logger.info(f"Using LIKE search condition: {field} LIKE {value}")
        else:
            search_condition = [{
                "field": "Name",
                "operator": "LIKE",
                "value": query
            }]
            logger.info(f"Using default Name LIKE search condition with value: {query}")

        logger.info("Beginning paginated asset fetch...")
        
        while True:
            logger.info(f"Fetching page {page}...")
            fetch_start = time.time()
            
            # Make POST request with JSON search conditions
            try:
                response = rt_api_request(
                    "POST", 
                    f"/assets?page={page}",
                    data=search_condition,
                    config=config
                )
                fetch_duration = time.time() - fetch_start
                logger.info(f"Page {page} fetch completed in {fetch_duration:.1f} seconds")
            except Exception as e:
                logger.error(f"Error fetching page {page}: {str(e)}")
                raise
            
            # Extract items from response
            items = []
            if 'items' in response:
                items = response['items']
                logger.info(f"Found {len(items)} items in 'items' field")
            elif 'assets' in response:
                items = response['assets']
                logger.info(f"Found {len(items)} items in 'assets' field")
            else:
                logger.warning(f"No items found in response for page {page}")
            
            if not items:
                logger.info(f"No more items found on page {page}, ending pagination")
                break
            
            # Process items in the current page
            logger.info(f"Processing {len(items)} items from page {page}")
            processed = 0
            
            for item in items:
                asset_id = item.get('id')
                if asset_id:
                    try:
                        # Fetch full asset details if we only got IDs
                        if len(item.keys()) <= 3:  # Only has id, type, _url
                            logger.debug(f"Fetching full details for asset {asset_id}")
                            asset_detail = rt_api_request("GET", f"/asset/{asset_id}", config=config)
                            all_assets.append(asset_detail)
                        else:
                            all_assets.append(item)
                        processed += 1
                        if processed % 10 == 0:
                            logger.info(f"Processed {processed}/{len(items)} items from page {page}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for asset {asset_id}: {e}")
            
            logger.info(f"Completed processing page {page} ({processed} items)")
            
            # Check pagination info
            total_pages = response.get('pages', 1)
            if page >= total_pages:
                logger.info(f"Reached last page ({page} of {total_pages})")
                break
            
            page += 1
            if page % 10 == 0:  # Log progress every 10 pages
                duration = time.time() - start_time
                logger.info(f"Processed {len(all_assets)} assets so far in {duration:.1f} seconds...")
        
        total_duration = time.time() - start_time
        logger.info(f"Found {len(all_assets)} total assets in {total_duration:.1f} seconds")
        
        return all_assets
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Failed to search assets after {duration:.1f} seconds: {e}")
        import traceback
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        raise Exception(f"Failed to search assets in RT: {e}")

def find_asset_by_name(asset_name, config=None):
    """
    Find an asset by its name in RT.
    
    Args:
        asset_name (str): The name of the asset to find
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: The first asset with the matching name, or None if no match is found
        
    Raises:
        Exception: If there's an error searching for the asset
    """
    try:
        # Log the search attempt
        if config is None:
            from flask import current_app
            current_app.logger.info(f"Searching for asset with name: {asset_name}")
        
        # Try a more direct approach: First get all assets and filter locally
        # This bypasses search query encoding issues entirely
        if config is None:
            from flask import current_app
            current_app.logger.info("Getting all assets and filtering locally")
        
        # Use a simple query to get a broader range of assets
        # Get the prefix part of the asset name (e.g., "W12-" from "W12-1246")
        prefix = None
        import re
        prefix_match = re.match(r'^([A-Za-z0-9\-]+\-)', asset_name)
        if prefix_match:
            prefix = prefix_match.group(1)
            
        if prefix:
            # Use the prefix with wildcard to get relevant assets
            query = f"Name LIKE '{prefix}*'"
            if config is None:
                from flask import current_app
                current_app.logger.info(f"Using prefix query: {query}")
        else:
            # Fallback to a very simple query 
            query = "id>0"
            if config is None:
                from flask import current_app
                current_app.logger.info("Using fallback query to get all assets")
            
        # Get assets matching the query
        assets = search_assets(query, config)
        
        if config is None:
            from flask import current_app
            current_app.logger.info(f"Retrieved {len(assets)} assets for filtering")
        
        # Directly filter the assets by name - case insensitive comparison
        matching_assets = [
            asset for asset in assets 
            if asset.get("Name") and asset.get("Name").lower() == asset_name.lower()
        ]
        
        if matching_assets:
            if config is None:
                from flask import current_app
                current_app.logger.info(f"Found {len(matching_assets)} exact matches after filtering")
                current_app.logger.info(f"First match ID: {matching_assets[0].get('id')}")
            return matching_assets[0]
            
        # If no exact match, try a fuzzy match (contains)
        if not matching_assets:
            if config is None:
                from flask import current_app
                current_app.logger.info("No exact matches, trying fuzzy matching")
                
            fuzzy_matches = [
                asset for asset in assets 
                if asset.get("Name") and asset_name.lower() in asset.get("Name").lower()
            ]
            
            if fuzzy_matches:
                if config is None:
                    from flask import current_app
                    current_app.logger.info(f"Found {len(fuzzy_matches)} fuzzy matches")
                    current_app.logger.info(f"First fuzzy match: {fuzzy_matches[0].get('Name')} (ID: {fuzzy_matches[0].get('id')})")
                return fuzzy_matches[0]
                
        # As a last resort, try the specific search queries (from original function)
        if config is None:
            from flask import current_app
            current_app.logger.info("Trying specific search queries as fallback")
            
        query_methods = [
            f"Name='{asset_name}'",
            f"Name LIKE '{asset_name}'", 
            f"{asset_name}"
        ]
        
        for query in query_methods:
            if config is None:
                from flask import current_app
                current_app.logger.info(f"Trying fallback query: {query}")
                
            query_assets = search_assets(query, config)
            
            if query_assets:
                if config is None:
                    from flask import current_app
                    current_app.logger.info(f"Fallback found {len(query_assets)} assets")
                    current_app.logger.info(f"First result: {query_assets[0].get('Name')} (ID: {query_assets[0].get('id')})")
                return query_assets[0]
                
        # If we get here, no assets were found
        if config is None:
            from flask import current_app
            current_app.logger.info("No assets found with any method")
        return None
        
    except Exception as e:
        if config is None:  # Only log if using current_app
            from flask import current_app
            current_app.logger.error(f"Error finding asset by name: {e}")
        raise Exception(f"Failed to find asset by name in RT: {e}")

def update_asset_custom_field(asset_id, field_name, field_value, config=None):
    """
    Update a custom field value for an asset in RT.
    
    Args:
        asset_id (str): The ID of the asset to update
        field_name (str): The name of the custom field to update
        field_value (str): The new value for the custom field
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: The response from the API
        
    Raises:
        Exception: If there's an error updating the asset custom field
    """
    data = {
        "CustomFields": [
            {
                "name": field_name,
                "values": [field_value]
            }
        ]
    }
    
    try:
        return rt_api_request("PUT", f"/asset/{asset_id}", data=data, config=config)
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error updating asset {asset_id} custom field: {e}")
        raise Exception(f"Failed to update asset custom field in RT: {e}")

def update_user_custom_field(user_id, field_name, field_value, config=None):
    """
    Update a custom field value for a user in RT.
    
    Args:
        user_id (str): The numeric ID or username of the user to update
        field_name (str): The name of the custom field to update
        field_value (str): The new value for the custom field
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: The response from the API
        
    Raises:
        Exception: If there's an error updating the user custom field
    """
    data = {
        "CustomFields": [
            {
                "name": field_name,
                "values": [field_value]
            }
        ]
    }
    
    try:
        return rt_api_request("PUT", f"/user/{user_id}", data=data, config=config)
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error updating user {user_id} custom field: {e}")
        raise Exception(f"Failed to update user custom field in RT: {e}")

def get_assets_by_owner(owner, exclude_id=None, config=None):
    """
    Fetch all assets owned by a specific owner, optionally excluding one asset by ID.
    
    Args:
        owner (str): The owner's identifier to search for (numeric ID)
        exclude_id (str, optional): Asset ID to exclude from results
        config (dict, optional): Config dictionary for RT API settings
        
    Returns:
        list: List of assets owned by this owner
    """
    if config is None:
        from flask import current_app
        config = current_app.config
        
    try:
        # Log input parameters
        logger.info(f"\n=== get_assets_by_owner ===")
        logger.info(f"Looking up assets for owner: {owner}")
        logger.info(f"Excluding asset ID: {exclude_id}")
        
        # Construct the URL for the assets endpoint
        base_url = config.get('RT_URL')
        api_endpoint = config.get('API_ENDPOINT')
        url = f"{base_url}{api_endpoint}/assets"
        
        # Use exact format from successful curl command
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"token {config.get('RT_TOKEN')}"
        }
        
        # Format query exactly as in the curl command
        query = f"Owner = '{owner}'"
        data = {"query": query}
        
        logger.info(f"Using query: {query}")
        logger.info(f"Request URL: {url}")
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request data: {data}")
        
        # Make the POST request with form-urlencoded data
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        logger.info(f"Raw API Response: {json.dumps(result, indent=2)}")
        
        # Get the list of asset IDs from items array
        items = result.get('items', [])
        logger.info(f"Found {len(items)} items for owner {owner}")
        for item in items:
            logger.info(f"Item: {json.dumps(item, indent=2)}")
        
        # Fetch full details for each asset
        assets = []
        for item in items:
            asset_id = item.get('id')
            if asset_id and asset_id != exclude_id:
                try:
                    logger.info(f"Fetching details for asset ID: {asset_id}")
                    asset_data = fetch_asset_data(asset_id, config)
                    assets.append(asset_data)
                    logger.info(f"Successfully fetched details for asset {asset_id}")
                except Exception as e:
                    logger.error(f"Error fetching details for asset {asset_id}: {e}")
                    
        logger.info(f"Final assets list contains {len(assets)} assets:")
        for asset in assets:
            logger.info(f"- Asset ID: {asset.get('id')}, Name: {asset.get('Name')}")
        
        logger.info("=== End get_assets_by_owner ===\n")
        return assets
        
    except Exception as e:
        logger.error(f"Error in get_assets_by_owner: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def fetch_user_data(user_id, config=None):
    """
    Fetch user data from RT API.
    
    Args:
        user_id (str): The ID (username) of the user to fetch
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: User data including Name, EmailAddress, etc.
        
    Raises:
        Exception: If there's an error fetching the user data
    """
    if not user_id:
        raise ValueError("User ID is missing or invalid")
    
    try:
        if config is None:
            from flask import current_app
            config = current_app.config
            current_app.logger.info(f"Fetching user data for ID: {user_id}")
            
        response = rt_api_request("GET", f"/user/{user_id}", config=config)
        
        # Validate response
        if not response:
            raise ValueError(f"Empty response from RT API for user ID: {user_id}")
            
        return response
        
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error fetching user data: {e}")
        raise Exception(f"Failed to fetch user data from RT: {e}")
    except Exception as e:
        if config is None:
            current_app.logger.error(f"Error processing user data for ID {user_id}: {str(e)}")
        raise Exception(f"Error processing user data: {str(e)}")

def create_ticket(subject, body, queue=None, requestor=None, status=None, owner=None, config=None):
    """
    Create a new ticket in Request Tracker.
    
    Args:
        subject (str): The subject of the ticket
        body (str): The content/description of the ticket
        queue (str, optional): The queue to create the ticket in (defaults to config value or 'General')
        requestor (str, optional): The email address of the requestor
        status (str, optional): The initial status of the ticket (e.g., 'new', 'open')
        owner (str, optional): The owner of the ticket
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: The newly created ticket data including its ID
        
    Raises:
        Exception: If there's an error creating the ticket
    """
    try:
        if config is None:
            from flask import current_app
            config = current_app.config
            logger.info(f"Creating new ticket: {subject}")
        
        # Use the default queue from configuration or fallback to 'General'
        if queue is None:
            queue = config.get('RT_DEFAULT_QUEUE', 'General')
            
        # Prepare ticket data
        ticket_data = {
            "Subject": subject,
            "Queue": queue,
            "Content": body
        }
        
        # Add optional fields if provided
        if requestor:
            ticket_data["Requestor"] = requestor
            
        if status:
            ticket_data["Status"] = status
            
        if owner:
            ticket_data["Owner"] = owner
            
        # Make the API request to create the ticket
        response = rt_api_request("POST", "/ticket", data=ticket_data, config=config)
        
        if not response or 'id' not in response:
            error_msg = f"Failed to create ticket: Invalid response from RT API"
            logger.error(error_msg)
            logger.error(f"Response: {response}")
            raise Exception(error_msg)
            
        logger.info(f"Successfully created ticket #{response.get('id')}")
        return response
        
    except Exception as e:
        error_msg = f"Failed to create ticket: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise Exception(error_msg)