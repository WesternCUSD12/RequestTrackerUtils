import requests
from flask import current_app

def rt_api_request(method, endpoint, data=None):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {current_app.config['RT_TOKEN']}",
    }
    url = f"{current_app.config['RT_URL']}{current_app.config['API_ENDPOINT']}{endpoint}"

    try:
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"RT API request error: {e}")
        return None