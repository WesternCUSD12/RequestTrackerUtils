# API Contracts

## Overview

This feature does **not introduce new REST API endpoints**. It extends the existing `/labels/print` route with an optional `size` query parameter. This document defines the modified contract and backward compatibility guarantees.

---

## Modified Endpoint

### `GET /labels/print`

**Description**: Generate and display/download a label for a specified asset

**Changes**:

- Added optional `size` query parameter
- Maintains 100% backward compatibility (no `size` param → defaults to `large`)

**Request**:

| Parameter | Type  | Required | Default   | Description                      | Example                |
| --------- | ----- | -------- | --------- | -------------------------------- | ---------------------- |
| `id`      | `int` | Yes      | -         | RT asset ID                      | `12345`                |
| `name`    | `str` | No\*     | -         | Asset name (alternative to `id`) | `"Chromebook-101"`     |
| `size`    | `str` | No       | `"large"` | Label template size              | `"small"` or `"large"` |
| `format`  | `str` | No       | `"html"`  | Output format                    | `"html"` or `"pdf"`    |

\*Either `id` or `name` must be provided (existing behavior)

**Response (HTML)**:

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <style>
        @page { size: 29mm 90.3mm; margin: 0; }
        /* ... small label CSS ... */
    </style>
</head>
<body>
    <div class="label-container">
        <img src="data:image/png;base64,..." alt="QR Code">
        <span class="asset-name">Chromebook...</span>
        <img src="data:image/png;base64,..." alt="Barcode">
    </div>
    <button class="no-print" onclick="window.print()">Print Label</button>
</body>
</html>
```

**Response (PDF)**:

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="label-ASSET-12345.pdf"

[Binary PDF data with 29mm x 90.3mm page size]
```

**Error Responses**:

| Status | Condition                   | Response Body                                           |
| ------ | --------------------------- | ------------------------------------------------------- |
| 400    | Missing `id` and `name`     | `{"error": "Asset ID or name required"}`                |
| 400    | Invalid `size` value        | `{"error": "Invalid size. Must be 'large' or 'small'"}` |
| 404    | Asset not found in RT       | `{"error": "Asset not found: 12345"}`                   |
| 500    | RT API failure              | `{"error": "Failed to fetch asset data"}`               |
| 500    | QR/barcode generation fails | `{"error": "Failed to generate label images"}`          |

**Backward Compatibility**:

- Existing calls without `size` param continue to work (default `"large"`)
- Existing calls with `format=pdf` continue to work (now supports small PDF)
- No changes to error handling or response structure

**Examples**:

```bash
# Large label (existing behavior)
GET /labels/print?id=12345

# Small label (new behavior)
GET /labels/print?id=12345&size=small

# Small PDF export (new behavior)
GET /labels/print?id=12345&size=small&format=pdf

# Asset lookup by name (existing behavior, works with small size)
GET /labels/print?name=Chromebook-101&size=small
```

---

## Internal Function Contracts

### `generate_qr_code(data: str, size: int = 10) -> str`

**Description**: Generate Base64-encoded QR code image

**Changes**:

- Modified `size` parameter to accept small label dimensions (new default `size=10` for large, `size=5` for small)

**Signature**:

```python
def generate_qr_code(data: str, size: int = 10) -> str:
    """
    Generate QR code as Base64 data URI.

    Args:
        data: Content to encode (typically asset tracking URL)
        size: QR box size in pixels (10 for large labels, 5 for small)

    Returns:
        Base64-encoded PNG image data URI

    Raises:
        ValueError: If data is empty or size is non-positive
    """
```

**Backward Compatibility**: Existing calls with no `size` argument default to `10` (large label behavior preserved)

---

### `generate_barcode(code: str, width: float = 80.0, height: float = 15.0) -> str`

**Description**: Generate Base64-encoded Code128 barcode image

**Changes**:

- Added `width` and `height` parameters for small label sizing

**Signature**:

```python
def generate_barcode(code: str, width: float = 80.0, height: float = 15.0) -> str:
    """
    Generate Code128 barcode as Base64 data URI.

    Args:
        code: Asset tag code (e.g., "ASSET-12345")
        width: Barcode width in mm (80.0 for large, 70.0 for small)
        height: Barcode height in mm (15.0 for large, 8.0 for small)

    Returns:
        Base64-encoded PNG image data URI

    Raises:
        ValueError: If code is empty or dimensions are non-positive
    """
```

**Backward Compatibility**: Existing calls with no dimension arguments default to large label sizes (80.0mm x 15.0mm)

---

### `truncate_text_to_width(text: str, font: str, size: int, max_width: float) -> str`

**Description**: Truncate text to fit within specified width (new function)

**Signature**:

```python
def truncate_text_to_width(text: str, font: str, size: int, max_width: float) -> str:
    """
    Truncate text with ellipsis to fit within maximum width.

    Uses ReportLab's pdfmetrics.stringWidth for precise calculation.

    Args:
        text: Full text to potentially truncate
        font: Font name ('Helvetica', 'Helvetica-Bold', etc.)
        size: Font size in points
        max_width: Maximum width in millimeters

    Returns:
        Original text or truncated text with "..." suffix

    Examples:
        >>> truncate_text_to_width("Very Long Asset Name", "Helvetica", 10, 60.0)
        "Very Long Asset..."

        >>> truncate_text_to_width("Short", "Helvetica", 10, 60.0)
        "Short"
    """
```

**Usage**: Called during both HTML and PDF rendering to ensure consistency

---

## Template Contracts

### `small_label.html`

**Description**: Jinja2 template for small label rendering (new file)

**Required Context Variables**:

```python
{
    'asset': {
        'id': int,
        'Name': str,              # Full asset name (pre-truncation)
        'AssetTag': str,          # Barcode value
        'Type': str,              # Asset category
        # SerialNumber not used in small labels
    },
    'qr_code': str,               # Base64 data URI from generate_qr_code()
    'barcode': str,               # Base64 data URI from generate_barcode()
    'truncated_name': str,        # Result of truncate_text_to_width()
    'tracking_url': str           # Full URL encoded in QR code
}
```

**Output**: HTML with embedded `@page { size: 29mm 90.3mm }` and inline images

---

### `label_form.html` (Modified)

**Description**: Label size selection form (new file, or modified existing form)

**Required Context Variables**:

```python
{
    'asset': {
        'id': int,
        'Name': str,
        'Type': str               # Used to determine default_size
    },
    'default_size': str           # 'large' or 'small' based on asset Type
}
```

**User Actions**:

- Select `large` or `small` radio button (pre-selected based on `default_size`)
- Submit form → redirects to `/labels/print?id={asset.id}&size={selected_size}`

---

## Configuration Contracts

### `LabelTemplate` (New)

**Description**: Dataclass defining label dimensions (see data-model.md)

**Configuration Source**: `request_tracker_utils/utils/label_config.py`

**Contract**:

```python
LABEL_TEMPLATES: Dict[str, LabelTemplate] = {
    'large': LabelTemplate(name='large', width_mm=100.0, height_mm=62.0, ...),
    'small': LabelTemplate(name='small', width_mm=29.0, height_mm=90.3, ...)
}
```

**Access Pattern**:

```python
from request_tracker_utils.utils.label_config import LABEL_TEMPLATES

template = LABEL_TEMPLATES.get(size, LABEL_TEMPLATES['large'])  # Safe fallback
```

**Validation**: `size` parameter must match keys in `LABEL_TEMPLATES` dict

---

## Non-Breaking Change Checklist

- [x] Existing `/labels/print` calls without `size` param work unchanged
- [x] Default behavior (large label) preserved when `size` omitted
- [x] Existing error responses unchanged (added new 400 for invalid size)
- [x] No changes to RT API integration (read-only asset fetching)
- [x] No database schema changes
- [x] Internal function signatures extended with optional params (defaults preserve old behavior)
- [x] PDF export (`format=pdf`) works with both label sizes

**Gate Status**: ✅ All contracts maintain backward compatibility
