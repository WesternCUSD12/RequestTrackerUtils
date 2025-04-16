import requests
from flask import current_app

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
    
    try:
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
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

def search_assets(query, config=None):
    """
    Search for assets in RT using a query.
    
    Args:
        query (str): The search query
        config (dict, optional): Configuration dictionary, defaults to current_app.config
        
    Returns:
        list: List of assets matching the query
        
    Raises:
        Exception: If there's an error searching for assets
    """
    try:
        response = rt_api_request("GET", f"/assets?query={query}", config=config)
        return response.get("assets", [])
    except requests.exceptions.RequestException as e:
        if config is None:  # Only log if using current_app
            current_app.logger.error(f"Error searching assets: {e}")
        raise Exception(f"Failed to search assets in RT: {e}")

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