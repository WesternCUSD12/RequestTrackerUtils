import requests
import time
import threading
from flask import current_app
from functools import lru_cache

# Simple in-memory cache for assets with expiration
class AssetCache:
    def __init__(self, max_size=500, ttl=3600):  # Cache up to 500 assets for 1 hour
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = threading.RLock()
        
        # Start a background thread to clean expired entries
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def get(self, key):
        """Get an item from cache if it exists and is not expired"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if time.time() < entry['expires']:
                    return entry['data']
                else:
                    # Remove expired entry
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
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
    
    def _cleanup_loop(self):
        """Background thread to clean expired entries"""
        while True:
            time.sleep(300)  # Check every 5 minutes
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove all expired entries from cache"""
        now = time.time()
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry['expires'] < now]
            for key in expired_keys:
                del self.cache[key]

# Initialize the asset cache
asset_cache = AssetCache()

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
    Make a request to the RT API.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, DELETE)
        endpoint (str): API endpoint path
        data (dict, optional): JSON data to send with the request
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: JSON response from API or None if request fails
        
    Raises:
        requests.exceptions.RequestException: If the request fails
    """
    # Use provided config or fall back to current_app.config
    cfg = config or current_app.config
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {cfg['RT_TOKEN']}",
    }
    url = f"{cfg['RT_URL']}{cfg['API_ENDPOINT']}{endpoint}"
    
    if config is None:  # Log request details if using current_app
        current_app.logger.debug(f"RT API Request: {method} {url}")
        if data:
            current_app.logger.debug(f"Request data: {data}")
    
    try:
        if method.upper() == "GET":
            # For GET requests, use params=None since the query is part of the URL
            response = requests.request(method, url, headers=headers)
        else:
            # For POST/PUT/DELETE requests, use json for JSON data
            response = requests.request(method, url, headers=headers, json=data)
            
        # Log response status
        if config is None:
            current_app.logger.debug(f"Response status: {response.status_code}")
            
        response.raise_for_status()
        
        # Sanitize the response to handle objects like datetime that can't be JSON serialized
        result = response.json()
        
        # Log summarized response (just count items if it's a list of assets)
        if config is None and "assets" in result:
            asset_count = len(result.get("assets", []))
            current_app.logger.debug(f"Response contains {asset_count} assets")
            
        return sanitize_json(result)
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"RT API request error: {e}")
        raise

def fetch_asset_data(asset_id, config=None, use_cache=True):
    """
    Fetch asset data from the RT API with caching.
    
    Args:
        asset_id (str): The ID of the asset to fetch
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        use_cache (bool, optional): Whether to use and update the cache, defaults to True
        
    Returns:
        dict: Asset data
        
    Raises:
        Exception: If there's an error fetching the asset data
    """
    if not asset_id:
        raise ValueError("Asset ID is missing or invalid")
    
    # Check if the asset is in cache
    if use_cache:
        cache_key = f"asset_{asset_id}"
        cached_data = asset_cache.get(cache_key)
        if cached_data:
            if config is None:
                current_app.logger.info(f"Cache hit for asset ID: {asset_id}")
            return cached_data
    
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
        
        # Update cache with the response if caching is enabled
        if use_cache:
            cache_key = f"asset_{asset_id}"
            asset_cache.set(cache_key, response)
            if config is None:
                current_app.logger.debug(f"Updated cache for asset ID: {asset_id}")
                
        return response
        
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error fetching asset data: {e}")
        raise Exception(f"Failed to fetch asset data from RT: {e}")
    except Exception as e:
        if config is None:
            current_app.logger.error(f"Error processing asset data for ID {asset_id}: {str(e)}")
        raise Exception(f"Error processing asset data: {str(e)}")

def search_assets(query, config=None, try_post_fallback=True, use_cache=True):
    """
    Search for assets in RT using a query with caching.
    
    Args:
        query (str): The search query
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        try_post_fallback (bool, optional): Whether to try POST method if GET fails, defaults to True
        use_cache (bool, optional): Whether to use and update the cache, defaults to True
        
    Returns:
        list: List of assets matching the query
        
    Raises:
        Exception: If there's an error searching for assets
        
    Notes:
        - Based on testing, the RT API supports GET requests with query parameters
        - It also supports POST requests with form-urlencoded content type
        - It does NOT support POST requests with JSON payloads
    """
    # URL encode the query to handle special characters properly
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    
    if config is None:
        current_app.logger.debug(f"Original query: {query}")
        current_app.logger.debug(f"Encoded query: {encoded_query}")
    
    # Check cache for this query
    if use_cache and query:
        # Use a hash of the query as the cache key
        import hashlib
        cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = asset_cache.get(cache_key)
        
        if cached_result:
            if config is None:
                current_app.logger.info(f"Cache hit for query: {query}")
            return cached_result
    
    try:
        # First try with GET method - this is the most reliable approach
        if config is None:
            current_app.logger.info(f"Searching assets from RT API: {query}")
            
        response = rt_api_request("GET", f"/assets?query={encoded_query}", config=config)
        
        if config is None:
            current_app.logger.debug(f"GET Response: {response}")
        
        # Get the assets from the response    
        assets = response.get("assets", [])
        
        # Update cache
        if use_cache and query:
            cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
            asset_cache.set(cache_key, assets)
            if config is None:
                current_app.logger.debug(f"Updated cache for query: {query}")
                
        return assets
        
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.warning(f"GET method failed for assets search: {e}")
            
        # If GET fails and fallback is enabled, try POST with form-urlencoded
        if try_post_fallback:
            try:
                if config is None:
                    current_app.logger.info("Trying POST with form-urlencoded as fallback")
                
                # Custom request to use form-urlencoded content type
                import requests
                
                cfg = config or current_app.config
                
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Authorization": f"token {cfg['RT_TOKEN']}",
                }
                
                url = f"{cfg['RT_URL']}{cfg['API_ENDPOINT']}/assets"
                form_data = {"query": query}
                
                if config is None:
                    current_app.logger.debug(f"POST URL: {url}")
                    current_app.logger.debug(f"POST Form Data: {form_data}")
                
                response = requests.post(url, headers=headers, data=form_data)
                response.raise_for_status()
                
                # Process the response
                result = response.json()
                
                if config is None:
                    current_app.logger.debug(f"POST Response: {result}")
                
                # Get the assets from the response
                assets = result.get("assets", [])
                
                # Update cache
                if use_cache and query:
                    import hashlib
                    cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
                    asset_cache.set(cache_key, assets)
                    if config is None:
                        current_app.logger.debug(f"Updated cache for query (POST): {query}")
                    
                return assets
                
            except requests.exceptions.RequestException as post_e:
                if config is None:
                    current_app.logger.error(f"POST fallback also failed: {post_e}")
                # Fall through to the exception below
        
        # If we get here, both methods failed or POST wasn't tried
        if config is None:
            current_app.logger.error(f"Error searching assets: {e}")
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