from flask import Flask
from request_tracker_utils.routes import label_routes, tag_routes

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('request_tracker_utils.config')

    # Register blueprints
    app.register_blueprint(label_routes.bp)
    app.register_blueprint(tag_routes.bp)

    return app

def main():
    app = create_app()
    port = app.config.get('PORT', 8080)
    app.logger.setLevel("INFO")


    rt_token = app.config.get('RT_TOKEN', 'Not Set')
    app.logger.info(f"RT_TOKEN: {rt_token}")

    app.run(debug=True, host='0.0.0.0', port=port)
