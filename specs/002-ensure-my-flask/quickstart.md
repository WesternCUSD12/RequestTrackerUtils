# Quickstart: Flask Application Organization & Maintainability

## Overview

This quickstart guide provides step-by-step instructions for implementing Flask application organization improvements following a documentation-first approach. Each phase builds on the previous, ensuring comprehensive documentation before code changes.

**Key Principle**: Document current state → Define standards → Apply standards gradually

## Prerequisites

- Python 3.11+ installed
- Flask application running locally
- Git repository initialized
- Access to edit code and documentation

## Phase 0: Document Current Architecture

**Goal**: Create comprehensive documentation of existing Flask application structure.

### Step 0.1: Create Architecture Documentation

1. **Add Architecture Section to README**

Create a new section in `README.md`:

```markdown
## Architecture

RequestTrackerUtils is a Flask web application using Blueprint-based organization for asset management and label generation.

### Application Structure
```

request_tracker_utils/
├── **init**.py # Flask app factory (create_app)
├── config.py # Environment-based configuration
├── routes/ # Flask blueprints by feature area
├── utils/ # Reusable business logic modules
├── templates/ # Jinja2 HTML templates
└── static/ # Frontend assets (JS, CSS, images)

```

### Blueprints

| Blueprint | URL Prefix | Purpose |
|-----------|------------|---------|
| `label_routes` | `/labels` | Label printing and batch generation |
| `tag_routes` | `/tags` | Asset tag sequence management |
| `device_routes` | `/devices` | Device check-in/check-out workflows |
| `student_routes` | `/students` | Student device tracking |
| `asset_routes` | `/assets` | Batch asset creation |

### Utility Modules

| Module | Purpose | External Dependencies |
|--------|---------|----------------------|
| `rt_api.py` | RT (Request Tracker) API client | RT REST API |
| `google_admin.py` | Google Admin API integration | Google Directory API |
| `db.py` | SQLite database operations | None |
| `pdf_generator.py` | PDF label generation | None |
| `csv_logger.py` | CSV audit logging | None |
| `student_check_tracker.py` | Student check-in tracking | SQLite database |
| `name_generator.py` | Adjective-animal name generation | None |

### External Integrations

- **RT (Request Tracker)**: Asset management, ticket creation, custom fields
- **Google Admin SDK**: Chromebook data sync, student device information
- **SQLite**: Local storage for check-in logs, asset tag sequences
```

2. **Document Module Dependencies**

Create `docs/module_dependencies.md`:

```markdown
# Module Dependencies

## Dependency Graph
```

config.py (no dependencies)
↑
utils/db.py
utils/rt_api.py → config.py
utils/google_admin.py → config.py
utils/pdf_generator.py
utils/csv_logger.py
utils/student_check_tracker.py → utils/db.py
utils/name_generator.py
↑
routes/label_routes.py → utils/rt_api.py, utils/pdf_generator.py
routes/tag_routes.py → utils/rt_api.py
routes/device_routes.py → utils/rt_api.py, utils/csv_logger.py
routes/student_routes.py → utils/google_admin.py, utils/student_check_tracker.py
routes/asset_routes.py → utils/rt_api.py, utils/name_generator.py
↑
**init**.py (app factory) → all routes, config.py

```

## Current State Analysis

- ✅ Blueprint pattern established
- ✅ Utilities separated from routes
- ⚠️ Inconsistent URL prefix usage
- ⚠️ Mixed docstring coverage
- ⚠️ No explicit module exports (`__all__`)
```

**Validation**: Verify dependency graph by checking import statements in each module.

### Step 0.2: Create Configuration Documentation

Add Configuration section to README:

````markdown
## Configuration

All configuration uses environment variables loaded from `.env` file (for development) or system environment (for production).

### Required Variables

| Variable   | Type   | Purpose                     | Example             |
| ---------- | ------ | --------------------------- | ------------------- |
| `RT_TOKEN` | string | RT API authentication token | `your-rt-api-token` |

### Optional Variables

| Variable          | Type    | Default                                                          | Purpose                     |
| ----------------- | ------- | ---------------------------------------------------------------- | --------------------------- |
| `RT_URL`          | string  | `https://tickets.wc-12.com`                                      | RT instance URL             |
| `WORKING_DIR`     | path    | `~/.rtutils` (macOS) or `/var/lib/request-tracker-utils` (Linux) | Runtime data directory      |
| `PORT`            | integer | `8080`                                                           | HTTP server port            |
| `PREFIX`          | string  | `W12-`                                                           | Asset tag prefix            |
| `LABEL_WIDTH_MM`  | integer | `100`                                                            | Label width in millimeters  |
| `LABEL_HEIGHT_MM` | integer | `62`                                                             | Label height in millimeters |

### Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
````

2. Edit `.env` with your values:

   ```bash
   # RT Configuration
   RT_TOKEN=your-actual-rt-token-here
   RT_URL=https://your-rt-instance.com

   # Application Settings
   PORT=8080
   PREFIX=YOUR-PREFIX-
   ```

3. Never commit `.env` file (already in `.gitignore`)

### Security Notes

- `RT_TOKEN` is sensitive - never log or expose in error messages
- `.env` file is for local development only
- Production uses systemd EnvironmentFile or Nix secrets

````

### Step 0.3: Create .env.example

Create `.env.example` in repository root:

```bash
# RT (Request Tracker) Configuration
# Required: Authentication token for RT REST API
RT_TOKEN=your-rt-api-token-here

# Optional: RT instance URL (default: https://tickets.wc-12.com)
# RT_URL=https://your-rt-instance.com

# Optional: API endpoint path (default: /REST/2.0)
# API_ENDPOINT=/REST/2.0

# Google Admin Configuration
# Required for Chromebook sync features
GOOGLE_CREDENTIALS_FILE=path/to/google-credentials.json
GOOGLE_ADMIN_EMAIL=admin@yourdomain.com

# Application Settings
# Optional: Working directory for database, logs, cache (default: platform-specific)
# WORKING_DIR=/var/lib/request-tracker-utils

# Optional: HTTP server port (default: 8080)
# PORT=8080

# Optional: Asset tag prefix (default: W12-)
# PREFIX=W12-

# Label Configuration
# Optional: Label dimensions in millimeters (defaults: 100x62)
# LABEL_WIDTH_MM=100
# LABEL_HEIGHT_MM=62

# Optional: Label padding in millimeters (default: 4)
# PADDING=4

# Optional: RT catalog for new assets (default: General assets)
# RT_CATALOG=General assets

# Logging Configuration
# Optional: Log level (default: INFO)
# LOG_LEVEL=INFO
````

**Validation**: Verify all configuration variables in `config.py` are documented.

---

## Phase 1: Standardize Module Structure

**Goal**: Apply consistent module organization patterns without changing functionality.

### Step 1.1: Assign Blueprint URL Prefixes

Update `request_tracker_utils/__init__.py` in `create_app()`:

**Before**:

```python
app.register_blueprint(label_routes.bp)
app.register_blueprint(tag_routes.bp)
app.register_blueprint(device_routes.bp, url_prefix='/devices')
app.register_blueprint(student_routes.bp)
app.register_blueprint(asset_routes.bp)
```

**After**:

```python
# Register blueprints with explicit URL prefixes
app.register_blueprint(label_routes.bp, url_prefix='/labels')
app.register_blueprint(tag_routes.bp, url_prefix='/tags')
app.register_blueprint(device_routes.bp, url_prefix='/devices')
app.register_blueprint(student_routes.bp, url_prefix='/students')
app.register_blueprint(asset_routes.bp, url_prefix='/assets')
```

**Testing**: Update any tests or documentation that reference old URLs without prefixes.

### Step 1.2: Add **all** Exports to Utility Modules

For each module in `request_tracker_utils/utils/`:

1. **Identify public functions** (used by routes or other utils)
2. **Add `__all__` list** at top of module after imports

**Example** (`db.py`):

```python
"""Database connection and initialization utilities."""

import sqlite3
import logging
from flask import current_app

# Public API - these functions are intended for import
__all__ = [
    'get_db_connection',
    'init_db',
    'close_db_connection'
]

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get SQLite database connection."""
    # Implementation
    pass

def init_db():
    """Initialize database schema."""
    # Implementation
    pass

def close_db_connection(conn):
    """Close database connection safely."""
    # Implementation
    pass

def _create_tables(conn):
    """Internal: Create database tables."""
    # This is private (not in __all__)
    pass
```

**Validation**: Run `python -c "from request_tracker_utils.utils.db import *; print(dir())"` to verify exports.

### Step 1.3: Organize Imports (PEP 8)

For each Python file:

1. **Order imports**: stdlib → third-party → local
2. **Group with blank lines** between categories
3. **Sort alphabetically** within each group

**Example**:

**Before**:

```python
from request_tracker_utils.config import WORKING_DIR
from flask import Blueprint, request, jsonify
import os
import logging
from request_tracker_utils.utils.rt_api import fetch_asset_data
import json
```

**After**:

```python
# Standard library
import json
import logging
import os

# Third-party
from flask import Blueprint, jsonify, request

# Local
from request_tracker_utils.config import WORKING_DIR
from request_tracker_utils.utils.rt_api import fetch_asset_data
```

**Tool**: Use `isort` for automatic sorting:

```bash
isort request_tracker_utils/
```

---

## Phase 2: Add Comprehensive Documentation

**Goal**: Add Google-style docstrings to all public functions.

### Step 2.1: Add Module Docstrings

For each module without a module-level docstring:

```python
"""
One-line summary of module purpose.

Extended description of what this module provides and its main use cases.

Typical usage example:
    from module_name import primary_function

    result = primary_function(param="value")
```

**Example** (`rt_api.py`):

```python
"""
RT (Request Tracker) API client with caching and retry logic.

This module provides a comprehensive interface to the RT REST API for
asset management operations. Features include:
- Persistent asset caching to minimize API calls
- Automatic retry with exponential backoff
- Thread-safe cache operations
- Connection pooling for performance

Typical usage:
    from request_tracker_utils.utils.rt_api import fetch_asset_data

    asset = fetch_asset_data("W12-0123")
    print(asset['Name'])
"""
```

### Step 2.2: Add Function Docstrings

For each public function (in `__all__`), add Google-style docstring:

**Template**:

```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    One-line summary in imperative mood.

    Extended description (optional for simple functions).

    Args:
        param1: Description of first parameter.
        param2: Description of second parameter. Defaults to X.

    Returns:
        Description of return value. For dicts/lists, describe structure.

    Raises:
        ExceptionType: When this exception is raised and why.

    Example:
        >>> result = function_name("value", param2=42)
        >>> print(result)
        'output'
    """
    # Implementation
    pass
```

**Refer to**: `specs/002-ensure-my-flask/contracts/docstring_standard.md` for detailed examples.

**Progress Tracking**:

```bash
# Check coverage
pydocstyle --count request_tracker_utils/

# Target: 90% coverage (SC-003)
```

### Step 2.3: Add Inline Comments for Complex Logic

For business-critical or non-obvious code:

**Example**:

```python
def calculate_next_asset_tag():
    """Generate next asset tag in sequence."""
    # Lock file prevents race condition between concurrent requests
    with open(sequence_file, 'r+') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        # Read current sequence number
        current = int(f.read().strip())

        # Increment and format with leading zeros (4 digits)
        next_num = current + 1
        tag = f"{PREFIX}{next_num:04d}"

        # Write back to file for next request
        f.seek(0)
        f.write(str(next_num))
        f.truncate()

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    return tag
```

---

## Phase 3: Standardize Error Handling & Logging

**Goal**: Implement consistent error handling and logging patterns.

### Step 3.1: Configure Application Logging

Update `request_tracker_utils/__init__.py`:

```python
def create_app():
    """Create and configure Flask application instance."""
    import os
    from request_tracker_utils.config import WORKING_DIR

    os.makedirs(WORKING_DIR, exist_ok=True)
    app = Flask(__name__, instance_path=WORKING_DIR)

    # Load configuration
    app.config.from_object('request_tracker_utils.config')

    # Configure logging
    configure_logging(app)

    # ... rest of initialization

def configure_logging(app):
    """
    Configure application-wide logging with consistent format.

    Sets up console and rotating file handlers with structured
    log format: timestamp - module - level - message

    Args:
        app: Flask application instance.
    """
    import logging
    from logging.handlers import RotatingFileHandler
    import os

    # Determine log level from config
    log_level = app.config.get('LOG_LEVEL', 'INFO')

    # Create formatter with consistent format (SC-009)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level))

    # File handler with rotation (10MB max, 10 backups)
    log_dir = os.path.join(app.instance_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # File gets all levels

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce werkzeug (Flask HTTP) logging verbosity
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    app.logger.info("Logging configured successfully")
```

### Step 3.2: Add Blueprint Error Handlers

For each blueprint in `request_tracker_utils/routes/`:

```python
# At end of blueprint file (e.g., label_routes.py)

@bp.errorhandler(404)
def not_found_error(error):
    """
    Handle 404 Not Found errors for this blueprint.

    Returns JSON response for API requests, HTML for browser requests.
    """
    logger.warning(f"404 error in {bp.name}: {request.url}")

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Resource not found"}), 404

    return render_template('404.html', blueprint=bp.name), 404

@bp.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server Error for this blueprint.

    Logs full exception details and returns generic error message to user.
    """
    logger.exception(f"500 error in {bp.name}")

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"error": "Internal server error"}), 500

    return render_template('500.html'), 500
```

### Step 3.3: Standardize Route Error Handling

Update route handlers to follow error handling contract:

**Template**:

```python
@bp.route('/endpoint', methods=['POST'])
def route_handler():
    """Route description with docstring."""
    try:
        # 1. Validate input early
        param = request.form.get('param')
        if not param:
            logger.warning(f"Missing required parameter in {request.endpoint}")
            return jsonify({"error": "Parameter 'param' is required"}), 400

        # 2. Delegate to utility function
        result = utility_function(param)

        # 3. Log success
        logger.info(f"Operation successful: param={param}, result_count={len(result)}")

        # 4. Return success response
        return jsonify({"success": True, "data": result}), 200

    except ValueError as e:
        # Input validation error
        logger.warning(f"Validation error: {e}", exc_info=False)
        return jsonify({"error": str(e)}), 400

    except requests.HTTPError as e:
        # External API error
        logger.error(f"External API error: status={e.response.status_code}, url={e.request.url}")
        return jsonify({"error": "External service error"}), 502

    except requests.Timeout:
        logger.error(f"Request timeout: endpoint={request.endpoint}")
        return jsonify({"error": "Request timed out"}), 504

    except Exception as e:
        # Unexpected error - full stack trace
        logger.exception(f"Unexpected error in {request.endpoint}")
        return jsonify({"error": "Internal server error"}), 500
```

**Refer to**: `specs/002-ensure-my-flask/contracts/error_handling_contract.md`

---

## Phase 4: Validation & Testing

**Goal**: Verify all success criteria are met.

### Step 4.1: Verify Success Criteria

Run validation checks:

```bash
# SC-003: 90% docstring coverage
pydocstyle --count request_tracker_utils/

# SC-004: Zero circular dependencies
# Install: pip install import-linter
lint-imports

# SC-009: Consistent logging format
# Manual review of log output during testing

# SC-005: All config via environment variables
# Verify config.py uses only os.getenv()

# SC-001: Module discovery time (manual test with new developer)
# SC-002: Code change isolation (measure via git diff analysis)
# SC-006: Deployment time (measure during next deployment)
# SC-007: Mockable dependencies (verify in test suite)
# SC-008: Code review feedback (track over next sprint)
```

### Step 4.2: Test Application

Run comprehensive tests:

```bash
# Start development server
python run.py

# Test all routes
curl http://localhost:8080/
curl http://localhost:8080/labels/
curl http://localhost:8080/devices/check-in

# Check logs for consistent format
tail -f instance/logs/app.log

# Verify .env configuration
rm .env  # Test with defaults
cp .env.example .env
# Edit with real values
python run.py
```

### Step 4.3: Update Development Guide

Create `docs/development_guide.md`:

```markdown
# Development Guide

## Adding a New Blueprint

1. Create blueprint file: `request_tracker_utils/routes/new_feature_routes.py`
2. Define blueprint with clear name: `bp = Blueprint('new_feature', __name__)`
3. Implement route handlers following error handling contract
4. Add docstrings to all route functions
5. Register in `__init__.py`: `app.register_blueprint(new_feature_routes.bp, url_prefix='/new-feature')`
6. Add error handlers (404, 500) at end of blueprint file

## Adding a New Utility Module

1. Create module file: `request_tracker_utils/utils/new_utility.py`
2. Add module docstring describing purpose
3. Define `__all__` list with public functions
4. Implement functions with Google-style docstrings
5. Use `logger = logging.getLogger(__name__)`
6. Add error handling for external calls (retry, timeout)

## Testing Patterns

See `specs/002-ensure-my-flask/contracts/` for:

- Docstring standards
- Error handling patterns
- Logging guidelines
```

---

## Phase 5: Continuous Improvement

**Goal**: Maintain standards as codebase evolves.

### Step 5.1: Add Pre-Commit Checks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile, black]

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]

  - repo: https://github.com/pycqa/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: [--convention=google]
```

Install:

```bash
pip install pre-commit
pre-commit install
```

### Step 5.2: Document Standards in CLAUDE.md

Update `.github/copilot-instructions.md` or `CLAUDE.md`:

```markdown
## Code Organization Standards

- **Blueprints**: All routes must be in blueprints with explicit URL prefixes
- **Utilities**: Business logic in `utils/` with `__all__` exports
- **Imports**: PEP 8 order (stdlib → third-party → local)
- **Docstrings**: Google-style for all public functions (90% coverage target)
- **Error Handling**: Consistent try/catch with proper HTTP status codes
- **Logging**: Structured format with key=value context

See `specs/002-ensure-my-flask/contracts/` for detailed contracts.
```

### Step 5.3: Review Process Checklist

Add to pull request template:

```markdown
## Code Quality Checklist

- [ ] All new functions have Google-style docstrings
- [ ] Imports follow PEP 8 order (stdlib → third-party → local)
- [ ] Error handling follows error_handling_contract.md
- [ ] Logging uses structured format with context
- [ ] No circular dependencies introduced
- [ ] Blueprint error handlers present (404, 500)
- [ ] Configuration uses environment variables (no hardcoded values)
- [ ] Tests added for new functionality
```

---

## Summary

This quickstart implements Flask organization improvements in 5 phases:

1. **Phase 0**: Document current architecture, configuration, dependencies
2. **Phase 1**: Standardize module structure (URL prefixes, `__all__`, imports)
3. **Phase 2**: Add comprehensive documentation (docstrings, inline comments)
4. **Phase 3**: Standardize error handling and logging patterns
5. **Phase 4**: Validate success criteria and test thoroughly
6. **Phase 5**: Establish continuous improvement practices

**Key Success Metrics**:

- SC-001: 10-minute module discovery time
- SC-003: 90% docstring coverage
- SC-004: Zero circular dependencies
- SC-009: Consistent logging format

**Next Steps**: Proceed to task generation with `/speckit.tasks` command.

---

**Quickstart Version**: 1.0
**Last Updated**: 2025-01-XX
**Status**: Ready for Implementation
