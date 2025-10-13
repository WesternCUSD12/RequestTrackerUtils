# Logging Contract

## Standard Format

All log messages must follow this format:

```
%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

**Example output**:

```
2025-01-10 14:23:45 - request_tracker_utils.utils.rt_api - INFO - Asset fetched: id=W12-0123, cached=True
2025-01-10 14:23:46 - request_tracker_utils.routes.label_routes - ERROR - Failed to generate label: asset_id=W12-0456, error=Asset not found
```

## Logger Setup

### In Utility Modules

```python
import logging

logger = logging.getLogger(__name__)  # Use __name__ for automatic module name
```

### In Application Factory

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def configure_logging(app):
    """Configure application-wide logging."""
    # Set log level from config
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    app.logger.setLevel(getattr(logging, log_level))

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)

    # File handler with rotation
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    # Set level for werkzeug logger (Flask's HTTP logger)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
```

## Log Level Guidelines

### DEBUG

**When**: Detailed diagnostic information for development
**Examples**:

```python
logger.debug(f"Entering function: fetch_asset_data(asset_id={asset_id})")
logger.debug(f"Cache lookup result: hit={cache_hit}, entry_age={age_seconds}s")
logger.debug(f"HTTP request: method=GET url={url} headers={headers}")
```

### INFO

**When**: General informational messages about normal operations
**Examples**:

```python
logger.info(f"Asset fetched successfully: id={asset_id}, owner={owner}")
logger.info(f"Label generated: asset_id={asset_id}, format=PDF")
logger.info(f"Database connection established: path={db_path}")
```

### WARNING

**When**: Unexpected but recoverable situations
**Examples**:

```python
logger.warning(f"Asset cache miss for frequently accessed item: id={asset_id}")
logger.warning(f"RT API rate limit approaching: remaining={remaining_calls}")
logger.warning(f"Missing optional configuration: LABEL_TEMPLATE_PATH using default")
```

### ERROR

**When**: Errors that prevent specific operations from completing
**Examples**:

```python
logger.error(f"Failed to fetch asset: id={asset_id}, status_code={response.status_code}")
logger.error(f"Database query failed: query={query}, error={str(e)}")
logger.error(f"External API timeout: url={url}, timeout={timeout}s")
```

### CRITICAL

**When**: Severe errors affecting application availability
**Examples**:

```python
logger.critical(f"Database connection lost: path={db_path}")
logger.critical(f"RT API authentication failed: all requests will fail")
logger.critical(f"Configuration error: required RT_TOKEN not set")
```

## Structured Logging Pattern

Always include key-value context:

```python
# ✅ Good: Structured with key=value pairs
logger.info(f"Device checked in: asset_id={asset_id}, student={student_name}, location={location}")
logger.error(f"API call failed: endpoint={endpoint}, status={status}, retries={retry_count}")

# ❌ Bad: Unstructured messages
logger.info(f"Checked in {asset_id}")
logger.error("API call failed")
```

## Success Criteria

**SC-009**: All log messages follow consistent format (timestamp, level, module, message)

---

**Contract Version**: 1.0
