# Error Handling Contract

## Overview

All Flask routes and utility functions must follow consistent error handling patterns to ensure reliability, debuggability, and user-friendly error messages.

## Principles

1. **Fail Fast**: Validate inputs early and raise descriptive exceptions
2. **Catch Specifically**: Catch specific exception types, not bare `except:`
3. **Log Contextually**: Include relevant context (asset ID, user, operation) in error logs
4. **User-Friendly Messages**: Never expose stack traces or internal details to users
5. **Proper Status Codes**: Return appropriate HTTP status codes for different error types

## Route Handler Error Handling Pattern

### Standard Pattern

```python
@bp.route('/endpoint', methods=['POST'])
def route_handler():
    """Route description."""
    try:
        # 1. Validate input
        param = request.form.get('param')
        if not param:
            logger.warning("Missing required parameter: param")
            return jsonify({"error": "Parameter 'param' is required"}), 400

        # 2. Delegate to utility function
        result = utility_function(param)

        # 3. Return success response
        return jsonify({"success": True, "data": result}), 200

    except ValueError as e:
        # Business logic validation error (user input issue)
        logger.warning(f"Validation error: {e}", exc_info=False)
        return jsonify({"error": str(e)}), 400

    except requests.HTTPError as e:
        # External API error
        logger.error(f"External API error: {e}", exc_info=True)
        if e.response.status_code == 404:
            return jsonify({"error": "Resource not found"}), 404
        else:
            return jsonify({"error": "External service error"}), 502

    except requests.Timeout:
        # Timeout error
        logger.error(f"Request timed out for param: {param}")
        return jsonify({"error": "Request timed out, please try again"}), 504

    except Exception as e:
        # Unexpected error - log full stack trace
        logger.exception(f"Unexpected error in route_handler for param: {param}")
        return jsonify({"error": "Internal server error"}), 500
```

### HTTP Status Code Guidelines

- **200 OK**: Successful GET/PUT/DELETE operation
- **201 Created**: Successful POST creating new resource
- **400 Bad Request**: Invalid input, validation error, missing required parameter
- **404 Not Found**: Resource doesn't exist (asset not found, user not found)
- **500 Internal Server Error**: Unexpected server-side error
- **502 Bad Gateway**: External service (RT API, Google API) returned error
- **504 Gateway Timeout**: External service timed out

## Utility Function Error Handling Pattern

### Pattern for External API Calls

```python
def call_external_api(resource_id: str) -> dict:
    """
    Call external API to fetch resource.

    Args:
        resource_id: The resource identifier.

    Returns:
        Resource data dictionary.

    Raises:
        ValueError: If resource_id is empty or invalid.
        requests.HTTPError: If API returns error (4xx, 5xx).
        requests.Timeout: If request exceeds timeout.
        ConnectionError: If API is unreachable.
    """
    # Validate input
    if not resource_id or not resource_id.strip():
        raise ValueError("resource_id cannot be empty")

    url = f"{BASE_URL}/resource/{resource_id}"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            timeout=30  # Always set timeout
        )
        response.raise_for_status()

        logger.info(f"Successfully fetched resource: {resource_id}")
        return response.json()

    except requests.Timeout:
        logger.error(f"Timeout fetching resource: {resource_id} from {url}")
        raise

    except requests.HTTPError as e:
        logger.error(f"HTTP error fetching resource {resource_id}: {e.response.status_code}")
        raise

    except requests.ConnectionError as e:
        logger.error(f"Connection error fetching resource {resource_id}: {e}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error fetching resource {resource_id}")
        raise
```

### Pattern with Retry Logic

For RT API and Google Admin API calls, use retry with exponential backoff:

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_retry_session(retries=3, backoff_factor=0.5):
    """Create requests Session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
```

## Blueprint Error Handlers

Register error handlers for each blueprint:

```python
@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors within this blueprint."""
    logger.warning(f"404 error in blueprint {bp.name}: {request.url}")

    if request.accept_mimetypes.accept_json:
        return jsonify({"error": "Resource not found"}), 404
    return render_template('404.html'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors within this blueprint."""
    logger.exception(f"500 error in blueprint {bp.name}")

    if request.accept_mimetypes.accept_json:
        return jsonify({"error": "Internal server error"}), 500
    return render_template('500.html'), 500
```

## Logging Best Practices

### Log Levels

- **DEBUG**: Function entry/exit, variable values, detailed flow
- **INFO**: Successful operations, important state changes
- **WARNING**: Recoverable issues, deprecated features, validation failures
- **ERROR**: Failed operations, external API errors
- **CRITICAL**: System-wide failures, irrecoverable errors

### Log Context

Always include relevant context:

```python
# ✅ Good: Context-rich logging
logger.info(f"Asset created: id={asset_id}, owner={owner}, catalog={catalog}")
logger.error(f"Failed to fetch asset: id={asset_id}, error={str(e)}")

# ❌ Bad: Vague logging
logger.info("Asset created")
logger.error("Error occurred")
```

### Exception Logging

```python
# Use logger.exception() for unexpected errors (includes stack trace)
try:
    result = risky_operation()
except Exception as e:
    logger.exception("Unexpected error in risky_operation")
    raise

# Use logger.error() for expected errors (no stack trace)
try:
    asset = fetch_asset_data(asset_id)
except requests.HTTPError as e:
    logger.error(f"Asset not found: {asset_id}, status={e.response.status_code}")
    raise
```

## Validation

### Success Criteria

- **FR-007**: Error handling follows consistent patterns across all blueprints
- **FR-008**: API endpoints return proper HTTP status codes with JSON error details
- **SC-009**: All log messages follow consistent format

### Testing

```python
def test_error_handling(client):
    """Test proper error handling and status codes."""
    # Test 400 Bad Request for missing parameter
    response = client.post('/endpoint')
    assert response.status_code == 400
    assert 'error' in response.json

    # Test 404 Not Found
    response = client.get('/assets/nonexistent')
    assert response.status_code == 404

    # Test 500 Internal Server Error (with mocked exception)
    with patch('module.utility_function', side_effect=Exception("Test error")):
        response = client.post('/endpoint', data={'param': 'value'})
        assert response.status_code == 500
```

---

**Contract Version**: 1.0
**Last Updated**: 2025-01-XX
