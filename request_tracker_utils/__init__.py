from flask import Flask, render_template, url_for, jsonify, request
from request_tracker_utils.routes import label_routes, tag_routes

def request_wants_json():
    """Check if the request prefers JSON response.
    
    Returns True if the request is from an API client that wants JSON,
    False if it's likely a browser request that wants HTML.
    """
    # Check Accept header for application/json
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return (best == 'application/json' and
            request.accept_mimetypes[best] > 
            request.accept_mimetypes['text/html'])

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('request_tracker_utils.config')

    # Register blueprints
    app.register_blueprint(label_routes.bp)
    app.register_blueprint(tag_routes.bp)

    # Add homepage route
    @app.route('/')
    def home():
        routes = []
        
        # Label routes
        routes.append({
            "endpoint": "/labels/print",
            "methods": ["GET"],
            "description": "Print a label for a specific asset",
            "usage": "GET /labels/print?assetId=<asset_id>"
        })
        
        routes.append({
            "endpoint": "/labels/batch",
            "methods": ["POST"],
            "description": "Generate labels for multiple assets based on a query",
            "usage": "POST /labels/batch with form data: query=<rt_query>"
        })
        
        routes.append({
            "endpoint": "/labels/update-all",
            "methods": ["POST"],
            "description": "Updates the 'Label' custom field to 'Label' for all assets",
            "usage": "POST /labels/update-all"
        })
        
        # Tag routes
        routes.append({
            "endpoint": "/next-asset-tag",
            "methods": ["GET"],
            "description": "Returns the next asset tag based on the current sequence",
            "usage": "GET /next-asset-tag"
        })
        
        routes.append({
            "endpoint": "/confirm-asset-tag",
            "methods": ["POST"],
            "description": "Confirms an asset tag and associates it with a Request Tracker ID",
            "usage": "POST /confirm-asset-tag with JSON body: {'asset_tag': 'W12-0001', 'request_tracker_id': 'RT12345'}"
        })
        
        routes.append({
            "endpoint": "/reset-asset-tag",
            "methods": ["POST"],
            "description": "Resets the asset tag sequence to a specified starting number",
            "usage": "POST /reset-asset-tag with JSON body: {'start_number': 100}"
        })
        
        # For API requests, return JSON
        if request_wants_json():
            return jsonify({
                "name": "Request Tracker Utils",
                "description": "Utilities for managing Request Tracker asset tags and labels",
                "available_routes": routes
            })
        
        # For browser requests, render HTML template
        return render_template('index.html', 
                              routes=routes)

    return app

def main():
    app = create_app()
    port = app.config.get('PORT', 8080)
    
    # Set logging level to DEBUG for more detailed logs
    import logging
    app.logger.setLevel(logging.DEBUG)
    
    # Log Flask and Werkzeug messages too
    logging.getLogger('werkzeug').setLevel(logging.DEBUG)
    logging.getLogger('flask').setLevel(logging.DEBUG)

    # Log configuration information
    rt_token = app.config.get('RT_TOKEN', 'Not Set')
    app.logger.info(f"RT_TOKEN: {rt_token}")
    app.logger.info(f"Starting server on port {port}")

    app.run(debug=True, host='0.0.0.0', port=port)
