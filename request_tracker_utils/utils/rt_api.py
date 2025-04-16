import requests
from flask import current_app

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

def fetch_asset_data(asset_id, config=None):
    """
    Fetch asset data from the RT API.
    
    Args:
        asset_id (str): The ID of the asset to fetch
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        dict: Asset data
        
    Raises:
        Exception: If there's an error fetching the asset data
    """
    try:
        return rt_api_request("GET", f"/asset/{asset_id}", config=config)
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error fetching asset data: {e}")
        raise Exception(f"Failed to fetch asset data from RT: {e}")

def search_assets(query, config=None, try_post_fallback=True):
    """
    Search for assets in RT using a query.
    
    Args:
        query (str): The search query
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        try_post_fallback (bool, optional): Whether to try POST method if GET fails, defaults to True
        
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
    
    try:
        # First try with GET method - this is the most reliable approach
        response = rt_api_request("GET", f"/assets?query={encoded_query}", config=config)
        
        if config is None:
            current_app.logger.debug(f"GET Response: {response}")
            
        return response.get("assets", [])
        
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
                    
                return result.get("assets", [])
                
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