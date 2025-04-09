from flask import Flask
from app.routes import label_routes, tag_routes

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('app.config')

    # Register blueprints
    app.register_blueprint(label_routes.bp)
    app.register_blueprint(tag_routes.bp)

    return app