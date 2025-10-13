# Docstring Standard Contract

## Overview

All public functions, classes, and modules in the Flask application must use **Google-style docstrings** for consistency and documentation generation compatibility.

## Google Style Docstring Format

### Function Docstring Template

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    One-line summary of function purpose (imperative mood).

    Extended description providing more context about what the function
    does, when to use it, and any important behavioral notes. This section
    is optional for simple functions where the one-line summary is sufficient.

    Args:
        param1: Description of first parameter. Include type info if not
            in type hint. Can span multiple lines if needed, with
            continuation indented.
        param2: Description of second parameter.

    Returns:
        Description of return value. Include type info if not in type hint.
        For complex return types (dicts, tuples), describe structure:
            - key1: Description of key1 value
            - key2: Description of key2 value

    Raises:
        ExceptionType1: When this exception is raised and why.
        ExceptionType2: When this other exception is raised.

    Example:
        >>> result = function_name("value1", 42)
        >>> print(result)
        'expected output'

    Note:
        Additional notes, warnings, or important information about
        side effects, thread safety, or performance characteristics.
    """
    # Implementation
    pass
```

### Class Docstring Template

```python
class ClassName:
    """
    One-line summary of class purpose.

    Extended description of the class, its responsibilities, and
    when to use it. Include information about state management,
    thread safety, or lifecycle if relevant.

    Attributes:
        attribute1: Description of public attribute.
        attribute2: Description of another public attribute.

    Example:
        >>> obj = ClassName(param="value")
        >>> obj.method()
        'result'
    """

    def __init__(self, param: str):
        """
        Initialize ClassName instance.

        Args:
            param: Description of initialization parameter.
        """
        self.attribute1 = param
        self.attribute2 = None

    def method(self) -> str:
        """One-line summary of method purpose."""
        return self.attribute1
```

### Module Docstring Template

```python
"""
One-line summary of module purpose.

Extended description of what this module provides, its main use cases,
and how it fits into the larger application architecture.

This module provides utilities for [specific purpose] including:
- Feature 1
- Feature 2
- Feature 3

Typical usage example:
    from module_name import primary_function

    result = primary_function(param="value")
    print(result)
"""

import os
import logging
# ... rest of module
```

## Real-World Examples

### Example 1: RT API Function

```python
def fetch_asset_data(asset_id: str, use_cache: bool = True) -> dict:
    """
    Fetch asset data from RT API with optional caching.

    Retrieves complete asset information including custom fields,
    owner details, and catalog information. Uses persistent cache
    to minimize API calls for frequently accessed assets.

    Args:
        asset_id: The RT asset ID or asset name to fetch. Can be numeric
            ID (e.g., "123") or asset name (e.g., "W12-0045").
        use_cache: Whether to use cached data if available. Defaults to True.
            Set to False to force fresh data from RT API.

    Returns:
        Dictionary containing asset data with keys:
            - id: Asset ID (str)
            - Name: Asset name (str)
            - Owner: Owner username (str)
            - CustomFields: Dict of custom field name → value
            - Catalog: Asset catalog name (str)

    Raises:
        ValueError: If asset_id is empty or None.
        requests.HTTPError: If RT API returns 4xx or 5xx error.
        requests.Timeout: If RT API request times out (>30s).
        ConnectionError: If RT API is unreachable.

    Example:
        >>> asset = fetch_asset_data("W12-0123")
        >>> print(asset['Name'])
        'W12-0123'
        >>> print(asset['Owner'])
        'jsmith'

        >>> # Force fresh data from API
        >>> asset = fetch_asset_data("W12-0123", use_cache=False)

    Note:
        Cached data has 72-hour TTL. Cache is shared across all requests
        but thread-safe via RLock. For bulk operations, consider using
        search_assets() instead of multiple fetch_asset_data() calls.
    """
    # Implementation
    pass
```

### Example 2: Flask Route Handler

```python
@bp.route('/print', methods=['GET'])
def print_label():
    """
    Display asset label printing form or generate label PDF.

    Handles both form display (no query params) and label generation
    (with assetId query parameter). Generated labels include QR code,
    barcode, and asset details.

    Returns:
        For form display: Rendered HTML template.
        For label generation: PDF file as attachment or JSON error.

    Query Parameters:
        assetId (optional): Asset ID or name to generate label for.

    Example:
        GET /labels/print                    # Display form
        GET /labels/print?assetId=W12-0123   # Generate PDF

    Note:
        PDF generation uses reportlab with A4 size. QR code encodes
        RT asset URL. Barcode uses Code128 format with checksum.
    """
    asset_id = request.args.get('assetId')

    if not asset_id:
        # Display form
        return render_template('label_form.html')

    try:
        # Generate label PDF
        asset_data = fetch_asset_data(asset_id)
        pdf_bytes = generate_label_pdf(asset_data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{asset_id}-label.pdf'
        )
    except ValueError as e:
        logger.error(f"Invalid asset ID: {asset_id}, error: {e}")
        return jsonify({"error": "Invalid asset ID"}), 400
    except requests.HTTPError as e:
        logger.error(f"RT API error for asset {asset_id}: {e}")
        return jsonify({"error": "Asset not found"}), 404
    except Exception as e:
        logger.exception(f"Unexpected error generating label for {asset_id}")
        return jsonify({"error": "Internal server error"}), 500
```

### Example 3: Utility Class

```python
class PersistentAssetCache:
    """
    Thread-safe persistent cache for RT asset data.

    Maintains in-memory LRU cache with file-backed persistence across
    application restarts. Automatically expires stale entries and saves
    to disk periodically.

    This cache reduces RT API load by storing frequently accessed asset
    data for 72 hours. Cache is shared across all Flask request workers
    via file-based synchronization.

    Attributes:
        max_size: Maximum number of assets to cache (default: 1500).
        ttl: Time-to-live for cached entries in seconds (default: 259200).
        cache_file: Path to JSON cache file.

    Example:
        >>> cache = PersistentAssetCache(max_size=1000, ttl=86400)
        >>> cache.set("W12-0123", asset_data)
        >>> cached = cache.get("W12-0123")
        >>> if cached:
        ...     print("Cache hit!")

    Note:
        Thread-safe via RLock. Background threads handle cleanup and
        periodic saves. Cache file uses JSON format for portability.
        Automatically handles cache corruption by rebuilding from scratch.
    """

    def __init__(self, max_size: int = 1500, ttl: int = 259200):
        """
        Initialize persistent asset cache.

        Args:
            max_size: Maximum number of assets to cache. When exceeded,
                least recently used items are evicted.
            ttl: Time-to-live in seconds. Entries older than this are
                considered stale and removed during cleanup.
        """
        # Implementation
        pass

    def get(self, asset_id: str) -> Optional[dict]:
        """
        Retrieve cached asset data if available and not stale.

        Args:
            asset_id: The asset ID to look up.

        Returns:
            Cached asset data dict if found and fresh, None otherwise.
        """
        # Implementation
        pass

    def set(self, asset_id: str, asset_data: dict) -> None:
        """
        Store asset data in cache with current timestamp.

        Args:
            asset_id: The asset ID to cache.
            asset_data: Asset data dictionary to store.
        """
        # Implementation
        pass
```

## Section Guidelines

### One-Line Summary

- **Imperative mood**: "Fetch asset data" not "Fetches asset data"
- **Concise**: Ideally under 80 characters
- **Specific**: Describe what, not how
- **No period** at the end (convention)

### Extended Description

- **When to include**: For functions with non-obvious behavior, side effects, or important context
- **What to cover**: Algorithm overview, use cases, important behavioral notes, relationships to other functions
- **When to skip**: For simple getters/setters or self-explanatory functions

### Args Section

- **Format**: `param_name: Description starting with capital letter.`
- **Type info**: Include if not in type hints, especially for complex types (dicts, callbacks)
- **Default values**: Mention defaults and their meaning (e.g., "Defaults to True")
- **Valid values**: Document constraints (e.g., "Must be positive integer")
- **Multi-line**: Indent continuation lines with 4 spaces

### Returns Section

- **Format**: `Description of return value.`
- **Structure**: For dicts/tuples, use bullet list with key/index descriptions
- **None returns**: Explicitly state when function returns None
- **Multiple return types**: Document when and why different types returned

### Raises Section

- **Format**: `ExceptionType: When this exception is raised.`
- **Be specific**: Document actual exception types, not base Exception
- **Conditions**: Explain what triggers each exception
- **Order**: List most common/important exceptions first

### Example Section

- **When to include**: For non-trivial functions, especially public APIs
- **Format**: Doctest-compatible (`>>>` prompt) when possible
- **Multiple examples**: Show common use cases and edge cases
- **Output**: Show expected results with `print()` or value display

### Note Section

- **When to include**: Important warnings, performance notes, thread safety, side effects
- **Format**: Can use bullet lists for multiple notes
- **Tone**: Clear and direct, not overly formal

## Validation

### Tools

```bash
# Check docstring style compliance
pydocstyle request_tracker_utils/

# Check specific file
pydocstyle request_tracker_utils/utils/rt_api.py

# Generate coverage report
pydocstyle --count request_tracker_utils/ | grep "checked"
```

### Success Criteria

- **SC-003**: 90% of functions include docstrings with complete parameter and return value documentation
- All public functions (exported in `__all__`) must have comprehensive docstrings
- Private functions (prefixed with `_`) should have docstrings if complex
- All classes must have class-level docstrings
- All modules must have module-level docstrings

## Common Pitfalls

### ❌ Avoid: Missing type information

```python
def fetch_asset_data(asset_id, use_cache=True):
    """Fetch asset data."""
    pass
```

### ✅ Correct: Include types and descriptions

```python
def fetch_asset_data(asset_id: str, use_cache: bool = True) -> dict:
    """
    Fetch asset data from RT API with optional caching.

    Args:
        asset_id: The RT asset ID or asset name.
        use_cache: Whether to use cached data. Defaults to True.

    Returns:
        Dictionary containing asset data with keys id, Name, Owner.
    """
    pass
```

### ❌ Avoid: Vague descriptions

```python
def process_data(data):
    """
    Process the data.

    Args:
        data: The data to process.

    Returns:
        The processed data.
    """
    pass
```

### ✅ Correct: Specific, actionable descriptions

```python
def validate_asset_fields(asset_data: dict) -> dict:
    """
    Validate and normalize required asset fields.

    Checks for presence of required fields (Name, Owner, Catalog),
    validates field formats, and applies default values where needed.

    Args:
        asset_data: Raw asset data dict from RT API response.

    Returns:
        Validated asset data dict with normalized fields:
            - Name: Uppercase asset name
            - Owner: Lowercase username
            - Catalog: Catalog name or "General assets" default

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    pass
```

### ❌ Avoid: Missing raises documentation

```python
def fetch_asset_data(asset_id: str) -> dict:
    """Fetch asset data from RT API."""
    if not asset_id:
        raise ValueError("Asset ID required")
    response = requests.get(url)
    response.raise_for_status()  # Can raise HTTPError
    return response.json()
```

### ✅ Correct: Document all exceptions

```python
def fetch_asset_data(asset_id: str) -> dict:
    """
    Fetch asset data from RT API.

    Args:
        asset_id: The RT asset ID to fetch.

    Returns:
        Dictionary containing asset data.

    Raises:
        ValueError: If asset_id is empty or None.
        requests.HTTPError: If RT API returns error response.
        requests.Timeout: If request times out after 30 seconds.
    """
    if not asset_id:
        raise ValueError("Asset ID required")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

## Migration Strategy

For existing code without proper docstrings:

1. **Prioritize by visibility**: Start with public APIs (functions in `__all__`)
2. **Start with module docstrings**: Establish context before diving into functions
3. **Use IDE assistance**: Many IDEs can generate docstring stubs from function signatures
4. **Validate incrementally**: Run `pydocstyle` frequently to catch formatting issues early
5. **Leverage code review**: Ensure new code has proper docstrings before merge

## References

- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [Sphinx Napoleon Extension](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) - For generating HTML docs from Google-style docstrings

---

**Contract Version**: 1.0
**Last Updated**: 2025-01-XX
**Status**: Ready for Implementation
