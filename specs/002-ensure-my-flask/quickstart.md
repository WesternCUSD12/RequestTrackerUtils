# Quickstart: Flask Application Organization & Maintainability

## Purpose

Follow this runbook to carry the documentation-first reorganization from research into implementation. Each phase delivers auditable artifacts (docs, contracts, tests) before touching production code, keeping RequestTrackerUtils maintainable and compliant with the constitution.

## Prerequisites

- Python 3.11 runtime available (via Nix shell, uv, or system interpreter)
- `direnv allow` or `devenv shell` executed in the repo root
- Access to RT and Google Admin sandbox credentials for validation
- Ability to push to feature branch `002-ensure-my-flask`
- Tooling installed: `ruff`, `isort`, `black`, `pytest`

## Phase 0 – Documentation Groundwork

1. **Create subsystem docs**
   - Copy the architecture template (`docs/_template_architecture.md`) into `docs/architecture/` for each subsystem: `assets`, `devices`, `labels`, `students`, `tags`, `integrations`, `infrastructure`.
   - Fill in sections: Purpose, Entry Points, Dependencies, Configuration, Logging & Error Handling, Testing Hooks, Future Work.
2. **Link from README**
   - Add an `Architecture` section summarizing the system and linking to each new document.
   - Highlight the documentation-first rule so contributors know to update docs before code.
3. **Capture current state evidence**
   - Run `tree -L 3 request_tracker_utils` and embed the snapshot in the architecture docs.
   - Export current blueprint registrations from `request_tracker_utils/__init__.py` and include them in the routes documentation.

**Exit Criteria**: All subsystem docs exist, README links are live, and evidence of current structure is captured in docs.

## Phase 1 – Design & Contract Outputs

1. **Utility package blueprint**
   - Map existing utilities into new subpackages:
     - `utils/integrations/`: RT, Google Admin, other external services.
     - `utils/services/`: orchestration helpers (student tracker, tag manager, label workflows).
     - `utils/infrastructure/`: db connections, csv logging, filesystem helpers.
   - Note any temporary shim modules required during migration.
2. **Document domain contracts**
   - Update `data-model.md` with entity tables (Blueprint, Utility Module, Architecture Document, Test Suite) and their relationships/state transitions.
3. **Publish API surface**
   - Author `/specs/002-ensure-my-flask/contracts/rt-utils-openapi.yaml` describing existing REST endpoints, payloads, and error envelopes to ensure backward compatibility.
4. **Refine this quickstart**
   - Keep instructions synchronized with architecture docs and research decisions.
5. **Plan pytest scaffolding**
   - Design directory layout for `tests/unit/`, define fixtures in `conftest.py`, and list priority test cases (RT API cache, name generator, csv logger, blueprint route smoke).

**Exit Criteria**: Design artifacts (plan, data model, contracts, quickstart) are updated and reviewed with maintainers.

## Phase 2 – Implementation Preparation

1. **Batch the migration**

   - Define logical change sets: (a) documentation updates, (b) blueprint prefix normalization, (c) utility package moves, (d) pytest scaffolding, (e) logging/error standardization.
   - For each batch capture expected file list, validation commands, and rollback steps.

   **Change Set A – Documentation Updates**

   - Files: `docs/architecture/*.md`, `README.md`, `docs/architecture/_inputs/*`, `docs/configuration/current_env_matrix.md`.
   - Validation: `mdformat` (if available), `markdown-link-check README.md`, manual proofread.
   - Rollback: Restore docs from `git checkout -- docs/architecture README.md docs/configuration/current_env_matrix.md`.

   **Change Set B – Blueprint Prefix Normalization**

   - Files: `request_tracker_utils/__init__.py`, `request_tracker_utils/routes/*.py`, new regression tests under `tests/integration/`.
   - Validation: `pytest tests/integration/test_blueprint_prefixes.py`, manual curl against key routes (`/labels`, `/devices`, `/students`).
   - Rollback: `git checkout` route modules and rerun smoke tests; keep legacy prefixes noted in `blueprint_registry.md` until fix applied.

   **Change Set C – Utility Package Moves**

   - Files: `request_tracker_utils/utils/*` reorganized into `integrations/`, `services/`, `infrastructure/`; update `__all__` exports and imports across routes/scripts.
   - Validation: `ruff check --select=I`, `import-linter`, `pytest tests/unit/utils`, targeted script run (`python scripts/inspect_asset.py --help`).
   - Rollback: Revert directory moves or reapply shim modules maintained under `utils/legacy/` (temporary) before reattempting.

   **Change Set D – Pytest Scaffolding**

   - Files: `tests/unit/conftest.py`, `tests/unit/utils/test_rt_api.py`, `tests/unit/utils/test_name_generator.py`, `docs/architecture/testing.md`.
   - Validation: `pytest tests/unit`, ensure zero live HTTP calls (inspect fixture usage).
   - Rollback: Remove new tests/fixtures, reinstall baseline smoke scripts, note gaps in backlog.

   **Change Set E – Logging & Error Standardization**

   - Files: `request_tracker_utils/utils/error_responses.py`, `request_tracker_utils/logging.py`, route modules for standardized responses, contracts under `specs/002-ensure-my-flask/contracts/`.
   - Validation: `pytest tests/integration/test_blueprint_prefixes.py::test_error_envelopes`, capture sample logs (`tail -n 50 instance/logs/app.log`) to confirm format.
   - Rollback: Revert shared helper modules, re-register previous logging handlers in `create_app()`.

2. **Risk register & mitigations**
   - Document risks (broken imports, missing env vars, stale docs) in `plan.md`, along with mitigations (shim modules, automated search, doc review checklist).
3. **Validation matrix**

   - Enumerate checks per batch:

     | Batch | Automated Checks                                                                                                | Manual Checks                                                     |
     | ----- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
     | A     | `ruff check docs/`, `markdown-link-check README.md`                                                             | Confirm README links resolve, preview subsystem docs in browser   |
     | B     | `pytest tests/integration/test_blueprint_prefixes.py`                                                           | Hit `/labels`, `/devices`, `/students` with curl or browser       |
     | C     | `ruff check --select=I`, `import-linter`, `pytest tests/unit`                                                   | Execute representative script (`python scripts/inspect_asset.py`) |
     | D     | `pytest tests/unit`, `pytest tests/integration -k "not external"`                                               | Review fixture docs for completeness                              |
     | E     | `pytest tests/integration/test_blueprint_prefixes.py::test_error_envelopes`, `pydocstyle request_tracker_utils` | Tail logs to confirm structured format                            |

   - Always close out with `nixos-rebuild test --flake .#request-tracker-utils` (or `switch` in staging) once code reorganization touches deployment modules.

4. **NixOS deployment alignment**
   - Review `flake.nix`, `flake.lock`, and `devenv.nix` for references to moved modules. Update package inputs/outputs and the `request-tracker-utils.nixosModule` service definition if file paths change.
   - Document rebuild steps for operators: run `sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils` on the host after merging changes, and note any new environment variables in the Nix module options.
5. **Communication prep**
   - Draft release notes for IT/ops highlighting new docs/tests.
   - Schedule walkthrough with maintainers covering documentation locations and pytest flow.

**Exit Criteria**: Implementation path is sequenced, risks logged, and stakeholders briefed.

## Validation Checklist

- [ ] Subsystem docs committed and linked from README
- [ ] Plan, data model, contracts, and quickstart reflect latest decisions
- [ ] Pytest scaffolding plan approved
- [ ] Risk register populated with mitigations
- [ ] Validation matrix ready for implementation phase
- [ ] NixOS deployment steps documented and smoke-tested via `sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils`

## Reference Commands (fish shell)

```fish
cd /Users/jmartin/rtutils
if test -f devenv.lock
     devenv shell
else
     direnv allow
end

ruff check request_tracker_utils
isort request_tracker_utils
pytest tests/unit  # once scaffolded
./test_rt_api.fish  # smoke check
```

## Helpful Resources

- Constitution: `.specify/memory/constitution.md`
- Feature spec: `specs/002-ensure-my-flask/spec.md`
- Research log: `specs/002-ensure-my-flask/research.md`
- API contracts: `specs/002-ensure-my-flask/contracts/`
- Architecture docs: `docs/architecture/`

Keep this quickstart current whenever standards evolve; it is the onboarding path for contributors executing this maintainability initiative.

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
