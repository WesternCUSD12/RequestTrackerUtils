from request_tracker_utils import create_app

# Create the Flask app instance
app = create_app()

if __name__ == "__main__":
    # Run the Flask app
    app.run(host="127.0.0.1", port=5000)
