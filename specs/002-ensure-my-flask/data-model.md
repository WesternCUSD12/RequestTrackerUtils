# Data Model: Flask Application Organizational Entities

## Overview

This document defines the conceptual "organizational entities" for the Flask application structure. Unlike traditional data models that describe database schemas, these entities represent the architectural components, their responsibilities, relationships, and standards.

**Note**: This feature does not introduce database schema changes. The "entities" here are organizational constructs for code structure and maintainability.

## Entity Definitions

### 1. Blueprint

A Flask Blueprint is a feature-area module that groups related routes, error handlers, and templates.

**Attributes**:

- **Name** (str): Blueprint identifier used in registration (e.g., `label_routes`, `device_routes`)
- **URL Prefix** (str): Base URL path for all routes in this blueprint (e.g., `/labels`, `/devices`)
- **Routes** (List[RouteHandler]): HTTP endpoints defined in this blueprint
- **Error Handlers** (Dict[int, Function]): HTTP status code → error handler function mapping
- **Template Directory** (Optional[str]): Blueprint-specific template subdirectory if applicable

**Responsibilities**:

- Define HTTP routes for a single feature area
- Handle HTTP request/response cycle
- Delegate business logic to Utility Modules
- Provide consistent error responses for blueprint routes
- Maintain isolation from other blueprints (no cross-blueprint imports)

**Relationships**:

- **Uses** multiple Utility Modules for business logic
- **Renders** Templates with context data
- **Registered by** Flask Application Factory (`create_app()`)

**Standards**:

- Must be registered in `create_app()` with explicit URL prefix
- Must not contain business logic (delegate to utils)
- Must not directly import other blueprints
- Route functions should be thin (max ~50 lines)
- Must define error handlers for 404, 500 at minimum

**Current Instances**:

1. `label_routes` - Label printing and batch generation
2. `tag_routes` - Asset tag sequence management
3. `device_routes` - Device check-in/check-out
4. `student_routes` - Student device tracking
5. `asset_routes` - Batch asset creation

---

### 2. Utility Module

A reusable Python module providing business logic, data access, or integration with external systems.

**Attributes**:

- **Module Name** (str): Python module identifier (e.g., `rt_api`, `pdf_generator`)
- **Exported Functions** (List[str]): Public API defined in `__all__`
- **External Dependencies** (List[str]): Third-party APIs or services integrated
- **State** (str): Stateless or Stateful (if maintains cache, connection pool, etc.)
- **Target Subpackage** (str): Intended grouping for reorganization (`integrations/`, `services/`, `infrastructure/`)
- **Dependency Rules** (str): May depend only on lower-level subpackages (no cyclic imports; e.g., `services` may use `integrations` and `infrastructure`, but not vice versa)

**Responsibilities**:

- Implement business logic independent of HTTP layer
- Provide reusable functions for multiple blueprints
- Handle external API integration (RT, Google Admin)
- Manage data persistence (database, file system, cache)
- Implement error handling for external calls (retry, timeout)
- Log operations at appropriate levels

**Relationships**:

- **Used by** Blueprints for business logic
- **May use** other Utility Modules (with acyclic dependency graph)
- **Uses** Configuration for settings and credentials
- **Reads/Writes** to Storage (database, file system)

**Standards**:

- Must define `__all__` for explicit public API
- Must not import from routes/ (no circular dependencies)
- Public functions must have comprehensive docstrings
- External API calls must have try/catch, retry logic, timeout
- Must use Python `logging` module (not print statements)
- Stateful modules must handle thread safety if applicable
- During reorganization, utilities will be grouped under subpackages: `integrations/` (external APIs), `services/` (domain orchestration), and `infrastructure/` (persistence helpers)

**Current Instances**:

1. `rt_api.py` - RT API client (stateful: cache, connection pool)
2. `db.py` - SQLite operations (stateless)
3. `google_admin.py` - Google Admin API client (stateless)
4. `pdf_generator.py` - PDF label generation (stateless)
5. `csv_logger.py` - CSV audit logging (stateless)
6. `student_check_tracker.py` - Student check-in tracking (stateful: database)
7. `name_generator.py` - Name generation (stateless)

---

### 3. Configuration

Environment-based application settings loaded from environment variables and .env files.

**Attributes**:

- **Variable Name** (str): Environment variable key (e.g., `RT_TOKEN`, `WORKING_DIR`)
- **Type** (str): Data type (str, int, bool, path)
- **Default Value** (Optional[Any]): Fallback value if not set in environment
- **Required** (bool): Whether application can start without this value
- **Sensitive** (bool): Whether value contains secrets/credentials
- **Source** (str): Where to set (`.env` file, system environment, deployment secrets)

**Responsibilities**:

- Centralize all environment-specific settings
- Provide sensible defaults for non-critical settings
- Validate configuration values at startup
- Fail fast with clear error messages for missing required values
- Never log or expose sensitive values

**Relationships**:

- **Loaded by** `config.py` module at import time
- **Used by** Blueprints and Utility Modules for behavior configuration
- **Set by** deployment environment (.env file, systemd unit, Nix module)

**Standards**:

- All configuration must be in `config.py` module
- Must use `python-dotenv` for `.env` file support
- Sensitive values must never have real defaults (use placeholder or fail)
- Must provide type conversion (int(), bool(), Path())
- Must document in README and `.env.example`
- Must support platform-specific paths (macOS vs Linux)

**Current Instances**:

- `RT_TOKEN` (str, required, sensitive) - RT API authentication token
- `RT_URL` (str, optional, non-sensitive) - RT instance base URL
- `WORKING_DIR` (path, optional, non-sensitive) - Runtime data directory
- `PREFIX` (str, optional, non-sensitive) - Asset tag prefix
- `PORT` (int, optional, non-sensitive) - HTTP server port
- `LABEL_WIDTH_MM` (int, optional, non-sensitive) - Label dimensions

---

### 4. Route Handler

A Python function that processes HTTP requests and returns HTTP responses within a Blueprint.

**Attributes**:

- **Function Name** (str): Python function identifier (e.g., `print_label`, `batch_labels`)
- **HTTP Methods** (List[str]): Allowed methods (GET, POST, etc.)
- **URL Pattern** (str): Route pattern relative to blueprint prefix (e.g., `/print`, `/batch`)
- **Request Parameters** (Dict[str, Type]): Expected query params, form data, JSON body
- **Response Format** (str): HTML, JSON, PDF, etc.

**Responsibilities**:

- Validate HTTP request parameters
- Delegate business logic to Utility Modules
- Prepare response data (JSON, HTML context, file download)
- Handle errors gracefully with user-friendly messages
- Return appropriate HTTP status codes
- Log request/response for audit trail

**Relationships**:

- **Defined in** Blueprint module
- **Calls** Utility Module functions for business logic
- **Renders** Template with context data (for HTML responses)
- **Returns** HTTP response (Flask Response, jsonify, render_template)

**Standards**:

- Must have descriptive function name (verb + noun, e.g., `create_asset`, `list_students`)
- Must validate all input parameters before processing
- Must not contain business logic (max ~20 lines of logic)
- Must have docstring describing purpose, parameters, responses
- Must use try/catch for exception handling
- Must return proper HTTP status codes (200/201/400/404/500)
- Must use `jsonify()` for JSON responses
- Must use `render_template()` for HTML responses

---

### 5. Template

A Jinja2 HTML template file that renders dynamic content for browser display.

**Attributes**:

- **Template Name** (str): Filename (e.g., `label_form.html`, `device_checkin.html`)
- **Base Template** (Optional[str]): Parent template if using inheritance (usually `base.html`)
- **Required Context** (Dict[str, Type]): Variables that must be passed from route handler
- **Blocks Overridden** (List[str]): Jinja2 blocks redefined from base template

**Responsibilities**:

- Render HTML with dynamic data from route handler
- Extend base template for consistent layout
- Include appropriate CSS/JavaScript for interactivity
- Display user-friendly error messages
- Maintain accessibility standards

**Relationships**:

- **Rendered by** Route Handler with context data
- **Extends** base.html (or other parent template)
- **Includes** Static Assets (CSS, JavaScript, images)

**Standards**:

- Must extend `base.html` for consistent layout
- Must use Bootstrap CSS classes (current standard)
- Must use Jinja2 template inheritance ({% extends %}, {% block %})
- Naming convention: `{feature}_{purpose}.html`
- Must include inline documentation for complex logic or required context variables

**Current Instances**:

- `base.html` - Base layout with navigation, Bootstrap CSS
- `index.html` - Homepage with route directory
- `label_form.html`, `batch_labels.html` - Label printing templates
- `device_checkin.html`, `device_checkout.html` - Device management templates
- `student_devices.html`, `student_checkin.html` - Student tracking templates
- `asset_create.html` - Asset batch creation form

---

### 6. Static Asset

Frontend files (JavaScript, CSS, images) served directly to the browser.

**Attributes**:

- **File Path** (str): Relative path from `static/` directory (e.g., `js/asset_batch.js`)
- **Type** (str): JavaScript, CSS, or Image
- **Purpose** (str): What functionality or styling this asset provides

**Responsibilities**:

- Provide client-side interactivity (JavaScript)
- Provide custom styling beyond Bootstrap (CSS)
- Provide images, icons, logos

**Relationships**:

- **Referenced by** Templates via `url_for('static', filename='...')`
- **Loaded by** browser on page render

**Standards**:

- Must be organized by type: `js/`, `css/`, `images/`
- JavaScript files must be named by feature (e.g., `asset_batch.js`)
- CSS files must use descriptive names (e.g., `device_checkin.css`)
- Must minimize browser-side logic (prefer server-side rendering)
- Must use modern ES6+ JavaScript (const/let, arrow functions, async/await)

**Current Instances**:

- `static/js/asset_batch.js` - Asset batch creation form state management

---

### 7. Architecture Document

A markdown artifact describing responsibilities, dependencies, configuration, and troubleshooting guidance for a subsystem.

**Attributes**:

- **Subsystem Name** (str): Matching blueprint or utility area (e.g., `tags`, `devices`, `integrations`)
- **Purpose** (str): Summary of what the subsystem delivers
- **Inputs/Outputs** (List[str]): Key data consumed and produced
- **Dependencies** (List[str]): Utility modules, external services, configuration variables
- **Operational Notes** (List[str]): Logging, monitoring, failure handling tips
- **Ownership** (str): Team or role accountable for updates

**Responsibilities**:

- Provide canonical documentation for subsystem architecture and workflows
- Identify boundary contracts (public APIs, templates, scripts)
- Enumerate configuration requirements and secret handling expectations
- Surface known risks and future improvements

**Relationships**:

- **Linked from** README architecture section
- **Updated with** code refactors to maintain documentation-first approach
- **References** related utility modules, blueprints, and tests

**Standards**:

- Stored under `docs/architecture/`
- Must follow shared template (Purpose → Responsibilities → Dependencies → Configuration → Testing → Future Work)
- Reviewed whenever subsystem code changes land
- Must cross-reference relevant API contracts and test coverage
- Must link deployment expectations, including how the NixOS service module consumes the subsystem (if applicable)

**Current/Planned Instances**:

- `docs/architecture/assets.md`
- `docs/architecture/devices.md`
- `docs/architecture/labels.md`
- `docs/architecture/students.md`
- `docs/architecture/tags.md`
- `docs/architecture/integrations.md`

---

### 8. Test Suite Module

A pytest package encapsulating automated tests for utilities, routes, and integrations.

**Attributes**:

- **Name** (str): Package path (e.g., `tests/unit/utils/test_rt_api.py`)
- **Scope** (str): Unit, integration, or smoke
- **Fixtures** (List[str]): Reusable setup helpers (e.g., fake RT client, temporary SQLite DB)
- **Dependencies** (List[str]): Mock libraries, sample data files

**Responsibilities**:

- Validate public contracts of utilities and route handlers
- Catch regressions introduced during reorganization
- Document expected side effects and error handling

**Relationships**:

- **Targets** Utility Modules and Blueprints via app/test clients
- **Uses** configuration fixtures to isolate environments
- **Augments** shell-based smoke scripts for end-to-end validation

**Standards**:

- Organized under `tests/` with `unit/`, `integration/`, and `smoke/` layers
- Uses pytest style with fixtures defined in `conftest.py`
- Must run without external network calls (use mocks)
- Must be referenced in quickstart documentation

**Current/Planned Instances**:

- `tests/unit/utils/test_rt_api.py` (planned)
- `tests/unit/utils/test_name_generator.py` (planned)
- `tests/integration/test_integration.py` (existing; to be relocated)
- `tests/smoke/test_rt_api.fish` (existing shell script linked in docs)

## Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Flask Application                           │
│                     (create_app factory)                         │
└────────────┬────────────────────────────────────────────────────┘
             │ registers
             ▼
┌─────────────────────────┐
│      Configuration      │◄─────────────────────────────────────┐
│      (config.py)        │  reads                                │
└────────────┬────────────┘                                       │
             │ uses                                                │
             ▼                                                     │
┌─────────────────────────┐                                       │
│       Blueprint         │                                       │
│   (label_routes, etc)   │                                       │
└────────────┬────────────┘                                       │
             │                                                     │
             ├─────────────► Route Handler                        │
             │               (function)                            │
             │               │                                     │
             │               │ delegates                           │
             │               ▼                                     │
             │      ┌─────────────────────┐                       │
             │      │  Utility Module     │                       │
             │      │  (rt_api, db, etc)  │───────────────────────┘
             │      └─────────────────────┘  uses config
             │               │
             │               │ uses
             │               ▼
             │      ┌─────────────────────┐
             │      │  External Systems   │
             │      │  (RT API, Google)   │
             │      └─────────────────────┘
             │
             │ renders
             ▼
┌─────────────────────────┐
│       Template          │
│   (Jinja2 HTML)         │
└────────────┬────────────┘
             │ references
             ▼
┌─────────────────────────┐
│    Static Asset         │
│  (JS, CSS, Images)      │
└─────────────────────────┘
```

**Key Dependency Rules**:

1. **Blueprints** → Utility Modules (allowed, encouraged)
2. **Blueprints** → Configuration (allowed)
3. **Blueprints** ↔ Blueprints (not allowed - no cross-blueprint imports)
4. **Utility Modules** → Utility Modules (allowed if acyclic)
5. **Utility Modules** → Configuration (allowed)
6. **Utility Modules** → Blueprints (not allowed - circular dependency)
7. **Route Handlers** → Templates (allowed via render_template)
8. **Templates** → Static Assets (allowed via url_for)

---

## Validation Rules

### Acyclic Dependency Graph

All modules must form a Directed Acyclic Graph (DAG) with no circular dependencies.

**Enforcement**:

- Use static analysis tools (`import-linter`, custom script)
- Success Criterion SC-004: Zero circular dependencies

**Violation Examples**:

- ❌ `label_routes.py` imports from `device_routes.py`
- ❌ `rt_api.py` imports from `label_routes.py`
- ❌ `google_admin.py` imports `student_check_tracker.py` which imports `google_admin.py`

**Resolution Pattern**:

- Extract shared logic to a new utility module
- Use dependency injection (pass functions/objects as parameters)
- Use Flask signals for loose coupling between blueprints

### Interface Contracts

Each Utility Module must define its public API via `__all__` export list.

**Example** (`rt_api.py`):

```python
__all__ = [
    'fetch_asset_data',
    'search_assets',
    'find_asset_by_name',
    'update_asset_custom_field',
    'create_ticket'
]
```

**Benefits**:

- Clear public API vs internal implementation details
- Prevents accidental use of internal functions
- Enables static analysis of module usage

### Documentation Contracts

All public functions must have docstrings following Google style:

**Required Sections**:

- One-line summary
- Extended description (optional, for complex functions)
- **Args**: Parameter names, types, descriptions
- **Returns**: Return type and description
- **Raises**: Exception types and when raised
- **Example**: Usage example for non-obvious functions

**Enforcement**:

- Use `pydocstyle` for docstring validation
- Success Criterion SC-003: 90% docstring coverage

---

## Implementation Notes

### Current State vs Target State

**Current State**:

- ✅ Blueprint pattern established with 5 blueprints
- ✅ Utility modules separated from routes
- ⚠️ Inconsistent URL prefix usage
- ⚠️ Import patterns not standardized
- ⚠️ No explicit `__all__` in most modules
- ⚠️ Mixed docstring coverage
- ⚠️ No explicit documentation of architectural entities

**Target State**:

- ✅ All blueprints have explicit URL prefixes
- ✅ All imports follow PEP 8 ordering
- ✅ All utility modules define `__all__`
- ✅ 90%+ functions have Google-style docstrings
- ✅ Architecture documented in README with entity descriptions
- ✅ Zero circular dependencies (validated by static analysis)
- ✅ Configuration documented in .env.example

### Migration Path

This is a **documentation-first** feature:

1. Document current architecture (research.md)
2. Define organizational entities (this document)
3. Create interface contracts (contracts/ directory)
4. Generate implementation guide (quickstart.md)
5. Apply standards gradually via tasks

No breaking changes to functionality - only organizational improvements.

---

**Data Model Version**: 1.0
**Last Updated**: 2025-01-XX
**Status**: Ready for Contract Definition (Phase 1)
