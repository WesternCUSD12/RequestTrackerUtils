from flask import Flask
from app.database import init_app
from app.routes import label_routes, tag_routes

def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object('app.config')

    # Initialize database
    init_app(app)

    # Register blueprints
    app.register_blueprint(label_routes.bp)
    app.register_blueprint(tag_routes.bp)

    return app