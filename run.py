from request_tracker_utils import create_app

request_tracker_utils = create_app()

if __name__ == "__main__":
    request_tracker_utils.run(debug=True, host='0.0.0.0', port=8080)
