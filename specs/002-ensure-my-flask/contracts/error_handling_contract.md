# Error Handling & Logging Envelope Contract

## Purpose

Define standardized error and logging response formats for all Flask routes and utility modules. Ensures consistent, actionable, and secure error feedback for clients and maintainers.

## Error Envelope (JSON)

All API endpoints and utility functions must return errors in the following envelope:

```json
{
  "success": false,
  "error": {
    "type": "<ErrorType>",
    "message": "<User-friendly message>",
    "details": "<Optional: developer details, redacted if sensitive>",
    "code": <HTTP status code>,
    "retry": <true|false>,
    "timestamp": "<ISO8601 UTC>"
  }
}
```

- `type`: Short error class (e.g., ValidationError, ExternalAPIError, InternalError)
- `message`: Human-readable, actionable message (never expose stack traces)
- `details`: Optional; only for internal logs or debugging, must redact secrets
- `code`: HTTP status code (e.g., 400, 404, 500)
- `retry`: Indicates if client should retry (true for transient errors)
- `timestamp`: UTC ISO8601 string

## Success Envelope (JSON)

All successful API responses must include:

```json
{
  "success": true,
  "data": <payload>,
  "timestamp": "<ISO8601 UTC>"
}
```

- `data`: Main response payload (dict, list, etc.)
- `timestamp`: UTC ISO8601 string

## Logging Envelope

All logs must use structured format:

```
<timestamp> <level> <module> <message> [context]
```

- `timestamp`: UTC ISO8601
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `module`: Python module name
- `message`: Main log message
- `context`: Optional key-value pairs (e.g., asset_id=123, user=admin)

## Implementation Notes

- Never log or return secrets, tokens, or sensitive data
- Always redact internal error details in client responses
- Use Python `logging` module for all logs
- Utility modules must raise exceptions with envelope-compatible attributes
- Route handlers must catch exceptions and return standardized envelopes
- All error responses must set correct HTTP status code
- Envelope format must be documented in subsystem guides and README

## Example

### Error Response

```json
{
  "success": false,
  "error": {
    "type": "ExternalAPIError",
    "message": "Failed to fetch asset data from RT API.",
    "details": "RT API returned 502 Bad Gateway.",
    "code": 502,
    "retry": true,
    "timestamp": "2025-10-13T18:00:00Z"
  }
}
```

### Success Response

```json
{
  "success": true,
  "data": {
    "asset_id": "W12-1001",
    "owner": "student123"
  },
  "timestamp": "2025-10-13T18:00:01Z"
}
```

### Log Entry

```
2025-10-13T18:00:00Z ERROR rt_api Failed to fetch asset data from RT API. asset_id=W12-1001 code=502
```
