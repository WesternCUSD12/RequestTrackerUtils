#!/usr/bin/env python3
"""
Script to list all custom fields in RT.
"""
import sys
import logging
import os
from pathlib import Path

# Ensure RT utils are on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RT config first  
from request_tracker_utils.config import RT_URL, API_ENDPOINT, RT_TOKEN
from request_tracker_utils.utils.rt_api import rt_api_request

# Create Flask app context for RT utils
from flask import Flask
app = Flask(__name__)
app.config.update({
    'RT_URL': os.environ.get('RT_URL') or RT_URL,
    'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
    'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
})
ctx = app.app_context()
ctx.push()

def list_custom_fields():
    """List all custom fields in RT."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # RT API configuration
    config = {
        'RT_URL': os.environ.get('RT_URL') or RT_URL,
        'API_ENDPOINT': os.environ.get('API_ENDPOINT') or API_ENDPOINT,
        'RT_TOKEN': os.environ.get('RT_TOKEN') or RT_TOKEN
    }
    
    try:
        print("Fetching all custom fields from RT...")
        response = rt_api_request('GET', '/customfields', config=config)
        
        if response and 'items' in response:
            fields = response['items']
            print(f"\nFound {len(fields)} custom fields:")
            
            for field in fields:
                field_id = field.get('id', 'N/A')
                field_name = field.get('Name', 'N/A')
                field_type = field.get('Type', 'N/A')
                description = field.get('Description', 'N/A')
                
                print(f"\nField ID: {field_id}")
                print(f"  Name: {field_name}")
                print(f"  Type: {field_type}")
                print(f"  Description: {description}")
                
                # Check if it's battery related
                if 'battery' in field_name.lower() or 'health' in field_name.lower():
                    print(f"  *** BATTERY FIELD FOUND ***")
                    
                    # Get more details about this field
                    try:
                        detail_response = rt_api_request('GET', f'/customfield/{field_id}', config=config)
                        if detail_response:
                            values = detail_response.get('Values', [])
                            if values:
                                print(f"  Allowed Values:")
                                for value in values:
                                    print(f"    - {value}")
                    except Exception as e:
                        print(f"  Error getting field details: {e}")
        else:
            print("No custom fields found or error in response")
            print(f"Response: {response}")
            
    except Exception as e:
        logging.error(f"Error fetching custom fields: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    list_custom_fields()
