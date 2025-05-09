from flask import Flask, render_template, url_for, jsonify, request
from request_tracker_utils.routes import label_routes, tag_routes, device_routes, student_routes

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
    app.register_blueprint(device_routes.bp, url_prefix='/devices')
    app.register_blueprint(student_routes.bp, url_prefix='/students')

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
        
        routes.append({
            "endpoint": "/labels/assets",
            "methods": ["POST"],
            "description": "Search for assets using direct JSON queries in RT API format",
            "usage": "POST /labels/assets with JSON body: [{\"field\": \"Name\", \"operator\": \"LIKE\", \"value\": \"W12-\"}]"
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
        
        routes.append({
            "endpoint": "/update-asset-name",
            "methods": ["POST"],
            "description": "Updates an asset's name in Request Tracker",
            "usage": "POST /update-asset-name with JSON body: {'asset_id': '123', 'asset_name': 'W12-0001'}"
        })
        
        routes.append({
            "endpoint": "/webhook/asset-created",
            "methods": ["POST"],
            "description": "Webhook endpoint for RT to call when a new asset is created",
            "usage": "POST /webhook/asset-created with JSON body: {'asset_id': '123', 'event': 'create'}"
        })
        
        # Add documentation for RT webhook configuration
        webhook_docs = {
            "title": "RT Webhook Configuration",
            "description": "To automatically assign asset tags when assets are created in Request Tracker, configure a webhook Scrip:",
            "steps": [
                "1. Go to Admin > Global > Scrips > Create",
                "2. Set these Scrip properties:",
                "   - Description: Auto Asset Tag Assignment",
                "   - Condition: On Create",
                "   - Stage: TransactionCreate",
                "   - Action: User Defined",
                "   - Template: User Defined",
                "3. In the Custom Condition code, add:",
                "```perl",
                "return 1 if $self->TransactionObj->Type eq 'Create' && $self->TransactionObj->ObjectType eq 'RT::Asset';",
                "return 0;",
                "```",
                "4. In the Custom Action code, add:",
                "```perl",
                "use LWP::UserAgent;",
                "use JSON;",
                "use HTTP::Request;",
                "",
                "my $asset_id = $self->TransactionObj->ObjectId;",
                "my $webhook_url = 'http://your-server-address/webhook/asset-created';",
                "",
                "# Get the asset object to modify it later",
                "my $asset = RT::Asset->new($RT::SystemUser);",
                "$asset->Load($asset_id);",
                "",
                "# Use eval for error handling",
                "eval {",
                "  # Create a user agent for making HTTP requests",
                "  my $ua = LWP::UserAgent->new(timeout => 10);",
                "  ",
                "  # Send POST request to the webhook with the asset ID",
                "  my $response = $ua->post(",
                "    $webhook_url,",
                "    'Content-Type' => 'application/json',",
                "    'Content' => encode_json({",
                "      asset_id => $asset_id,",
                "      event => 'create',",
                "      timestamp => time()",
                "    })",
                "  );",
                "  ",
                "  # Check if the request was successful",
                "  if ($response->is_success) {",
                "    # Parse the JSON response",
                "    my $result = decode_json($response->decoded_content);",
                "    ",
                "    # If the webhook assigned a tag, update the asset name in RT",
                "    if ($result->{asset_tag}) {",
                "      my $new_tag = $result->{asset_tag};",
                "      ",
                "      # Update the asset's name",
                "      $RT::Logger->info(\"Updating asset #$asset_id name to '$new_tag'\");",
                "      $asset->SetName($new_tag);",
                "      ",
                "      # Log the result",
                "      $RT::Logger->info(\"Asset #$asset_id name updated to: \" . $asset->Name);",
                "    } else {",
                "      $RT::Logger->warning(\"No asset tag received from webhook for asset #$asset_id\");",
                "    }",
                "  } else {",
                "    # Log the error if the webhook request failed",
                "    $RT::Logger->error(\"Webhook request failed: \" . $response->status_line);",
                "    $RT::Logger->error(\"Response content: \" . $response->decoded_content);",
                "  }",
                "};",
                "if ($@) {",
                "  # Catch any exceptions and log them",
                "  $RT::Logger->error(\"Error in asset creation webhook: $@\");",
                "}",
                "",
                "# Return success regardless of webhook result to avoid affecting RT",
                "return 1;",
                "```",
                "5. Apply to: Assets",
                "6. Set appropriate Queue/Catalog restrictions if needed",
                "7. Save the Scrip"
            ]
        }
        
        # For API requests, return JSON
        if request_wants_json():
            return jsonify({
                "name": "Request Tracker Utils",
                "description": "Utilities for managing Request Tracker asset tags and labels",
                "available_routes": routes,
                "webhook_configuration": webhook_docs
            })
        
        # For browser requests, render HTML template
        return render_template('index.html', 
                              routes=routes,
                              webhook_docs=webhook_docs)

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
