# Implementation Tasks: Small-format printable asset label (1.1" x 3.5")

**Feature**: Small-format printable asset label (1.1" x 3.5")  
**Branch**: `003-rtutils-should-offer`  
**Generated**: 2025-10-14  
**Status**: Ready for Implementation

---

## Task Overview

**Total Tasks**: 18  
**Estimated Effort**: 8-12 hours  
**MVP Scope**: User Story 1 (Tasks T001-T011) - Quick single-label print for chargers

### Tasks by User Story

- **Setup & Foundation** (T001-T004): 4 tasks - Shared infrastructure for all stories
- **User Story 1** [US1] (T005-T011): 7 tasks - Quick single-label print (P1)
- **User Story 2** [US2] (T012-T014): 3 tasks - Full-size label for other assets (P1)
- **User Story 3** [US3] (T015-T017): 3 tasks - Manual override and batch printing (P2)
- **Polish & Integration** (T018): 1 task - Cross-cutting concerns

### Parallelization Opportunities

- **Phase 1 (Setup)**: T001 [P], T002 [P], T003 [P] can run in parallel (different files)
- **Phase 3 (US1 Core)**: T006 [P], T007 [P] can run in parallel (template vs CSS)
- **Phase 4 (US2)**: T013 [P], T014 [P] can run in parallel (route vs template logic)

---

## Phase 1: Setup & Foundational Infrastructure

**Objective**: Create shared configuration and utilities needed by all user stories.

### T001 [P] - Create LabelTemplate configuration module

**User Story**: Foundation (prerequisite for all stories)  
**File**: `request_tracker_utils/utils/label_config.py` (NEW)  
**Estimate**: 30 minutes

**Description**: Create the `LabelTemplate` dataclass and `LABEL_TEMPLATES` dictionary with dimensions for both large and small label variants.

**Acceptance Criteria**:

- File created at `request_tracker_utils/utils/label_config.py`
- `LabelTemplate` dataclass defined with 9 fields: `name`, `width_mm`, `height_mm`, `qr_size_mm`, `barcode_width_mm`, `barcode_height_mm`, `font_size_pt`, `show_serial`, `text_max_width_mm`
- `LABEL_TEMPLATES` dict contains both `'large'` and `'small'` configurations
- Large template: 100mm x 62mm, QR 50mm, barcode 80x15mm, font 14pt, serial visible, text max 90mm
- Small template: 29mm x 90.3mm, QR 20mm, barcode 70x8mm, font 10pt, serial hidden, text max 60mm
- Validation: All dimension fields are positive floats, font size ≥ 6, text max width < label width

**Implementation**:

```python
from dataclasses import dataclass

@dataclass
class LabelTemplate:
    name: str
    width_mm: float
    height_mm: float
    qr_size_mm: float
    barcode_width_mm: float
    barcode_height_mm: float
    font_size_pt: int
    show_serial: bool
    text_max_width_mm: float

LABEL_TEMPLATES = {
    'large': LabelTemplate(
        name='large',
        width_mm=100.0,
        height_mm=62.0,
        qr_size_mm=50.0,
        barcode_width_mm=80.0,
        barcode_height_mm=15.0,
        font_size_pt=14,
        show_serial=True,
        text_max_width_mm=90.0
    ),
    'small': LabelTemplate(
        name='small',
        width_mm=29.0,
        height_mm=90.3,
        qr_size_mm=20.0,
        barcode_width_mm=70.0,
        barcode_height_mm=8.0,
        font_size_pt=10,
        show_serial=False,
        text_max_width_mm=60.0
    )
}
```

---

### T002 [P] - Create text truncation utility

**User Story**: Foundation (prerequisite for US1, US2, US3)  
**File**: `request_tracker_utils/utils/text_utils.py` (NEW)  
**Estimate**: 45 minutes

**Description**: Implement `truncate_text_to_width()` function using ReportLab's `pdfmetrics.stringWidth()` for accurate text measurement and binary search truncation algorithm.

**Acceptance Criteria**:

- File created at `request_tracker_utils/utils/text_utils.py`
- Function signature: `truncate_text_to_width(text: str, font_name: str, font_size: int, max_width_mm: float) -> str`
- Uses `reportlab.pdfbase.pdfmetrics.stringWidth()` for width calculation
- Converts mm to points (mm \* 2.834645)
- Binary search algorithm finds max characters that fit (with "..." suffix if truncated)
- Returns original text if it fits, truncated text + "..." if too long
- Edge cases: Empty string returns "", single character too wide returns "..."
- Includes docstring with examples

**Implementation Notes**:

- Binary search on character count (not pixel-by-pixel)
- Account for ellipsis width when truncating
- Test with ReportLab's 'Helvetica' font (standard)

---

### T003 [P] - Update generate_qr_code() for configurable sizing

**User Story**: Foundation (prerequisite for US1)  
**File**: `request_tracker_utils/routes/label_routes.py` (MODIFY)  
**Estimate**: 20 minutes

**Description**: Modify existing `generate_qr_code()` function to accept a `box_size` parameter (defaults to 10 for backward compatibility, use 5 for small labels).

**Acceptance Criteria**:

- Function signature updated: `generate_qr_code(data: str, box_size: int = 10) -> str`
- Passes `box_size` to `qrcode.QRCode(box_size=box_size, ...)`
- Error correction set to Medium (`qrcode.constants.ERROR_CORRECT_M`)
- Border size: 1 module (minimum quiet zone)
- Returns Base64-encoded PNG data URI (existing behavior preserved)
- Backward compatibility: Existing calls without `box_size` param default to 10 (large label behavior)

**Testing Note**: Test with both `box_size=10` (large) and `box_size=5` (small) to verify scannability.

---

### T004 [P] - Update generate_barcode() for configurable dimensions

**User Story**: Foundation (prerequisite for US1)  
**File**: `request_tracker_utils/routes/label_routes.py` (MODIFY)  
**Estimate**: 20 minutes

**Description**: Modify existing `generate_barcode()` function to accept `width_mm` and `height_mm` parameters (defaults to 80.0 and 15.0 for backward compatibility).

**Acceptance Criteria**:

- Function signature updated: `generate_barcode(code: str, width_mm: float = 80.0, height_mm: float = 15.0) -> str`
- Uses Code128 barcode format (existing)
- Passes custom options to ImageWriter:
  ```python
  options = {
      'module_width': 0.2,
      'module_height': height_mm,
      'quiet_zone': 2.5,
      'font_size': 8,
      'text_distance': 1.0
  }
  ```
- Returns Base64-encoded PNG data URI (existing behavior preserved)
- Backward compatibility: Existing calls without dimension params default to 80mm x 15mm

---

## Phase 2: User Story 1 - Quick single-label print (Priority P1)

**Goal**: Enable technicians to print compact 1.1"x3.5" labels for chargers with automatic default selection.

**Independent Test Criteria**:

- Load Charger asset → `labels/print` UI defaults to Small label
- Preview shows 29mm x 90.3mm layout without serial number
- QR code and barcode scannable with phone app
- PDF export at exact dimensions

---

### T005 [US1] - Create small_label.html template

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/templates/small_label.html` (NEW)  
**Estimate**: 60 minutes

**Description**: Create new Jinja2 template for small label with 29mm x 90.3mm @page dimensions, compact layout (QR left, text center, barcode bottom), and no serial number.

**Acceptance Criteria**:

- File created at `request_tracker_utils/templates/small_label.html`
- Extends `base.html` (existing pattern)
- CSS @page rule: `@page { size: 29mm 90.3mm; margin: 0; }`
- Layout structure:
  - QR code: 20mm x 20mm, top-left (2mm from edges)
  - Asset name: 10pt font, center-aligned, max width 60mm (uses `{{ truncated_name }}`)
  - Barcode: 70mm x 8mm, bottom, horizontally centered
- No serial number display (omitted per FR-003)
- Print button with `.no-print` class (hidden in print mode)
- Background color: white, no borders
- Context variables expected: `asset`, `qr_code` (base64), `barcode` (base64), `truncated_name`, `tracking_url`

**Template Structure**:

```jinja2
{% extends "base.html" %}

{% block content %}
<style>
    @media print {
        @page {
            size: 29mm 90.3mm;
            margin: 0;
        }
        body {
            margin: 0;
            padding: 0;
        }
        .no-print {
            display: none;
        }
    }
    .label-container {
        width: 29mm;
        height: 90.3mm;
        position: relative;
        background: white;
    }
    .qr-code {
        position: absolute;
        top: 2mm;
        left: 2mm;
        width: 20mm;
        height: 20mm;
    }
    .asset-name {
        position: absolute;
        top: 24mm;
        left: 50%;
        transform: translateX(-50%);
        font-size: 10pt;
        text-align: center;
        max-width: 60mm;
        word-wrap: break-word;
    }
    .barcode {
        position: absolute;
        bottom: 1mm;
        left: 50%;
        transform: translateX(-50%);
        width: 70mm;
        height: 8mm;
    }
</style>

<div class="label-container">
    <img src="{{ qr_code }}" alt="QR Code" class="qr-code">
    <span class="asset-name">{{ truncated_name }}</span>
    <img src="{{ barcode }}" alt="Barcode" class="barcode">
</div>

<button class="no-print" onclick="window.print()">Print Label</button>
{% endblock %}
```

---

### T006 [US1] [P] - Add CSS for small label print styling

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/static/css/labels.css` (MODIFY or CREATE)  
**Estimate**: 15 minutes

**Description**: Add or update CSS file with print-specific styles for small labels (may be embedded in template if no separate CSS file exists).

**Acceptance Criteria**:

- If `labels.css` exists: Add small label styles to existing file
- If not: Embed styles in `small_label.html` template (covered by T005)
- Print media query ensures @page dimensions applied
- `.no-print` class hides UI elements during printing
- Label container sized exactly to 29mm x 90.3mm

**Note**: This task may be absorbed into T005 if no separate CSS file is used (check existing pattern in `label.html`).

---

### T007 [US1] [P] - Extend print_label() route with size parameter handling

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/routes/label_routes.py` (MODIFY)  
**Estimate**: 45 minutes

**Description**: Modify `print_label()` route to accept optional `size` query parameter, load appropriate `LabelTemplate`, select correct Jinja2 template, and pass truncated text to template context.

**Acceptance Criteria**:

- Route signature: `@bp.route('/labels/print')` (existing, no change)
- Parse `size` query param: `size = request.args.get('size', 'large')`
- Validate `size` in `['large', 'small']`, return 400 error if invalid
- Import and use `LABEL_TEMPLATES` from `label_config`
- Load template config: `template_config = LABEL_TEMPLATES.get(size, LABEL_TEMPLATES['large'])`
- Call `truncate_text_to_width(asset.Name, 'Helvetica', template_config.font_size_pt, template_config.text_max_width_mm)`
- Select Jinja2 template: `'small_label.html'` if size == `'small'`, else `'label.html'`
- Pass `truncated_name` to template context
- Generate QR code with appropriate `box_size`: `generate_qr_code(tracking_url, box_size=5 if size=='small' else 10)`
- Generate barcode with template dimensions: `generate_barcode(asset.AssetTag, width_mm=template_config.barcode_width_mm, height_mm=template_config.barcode_height_mm)`
- Backward compatibility: Existing calls without `size` param default to `'large'`
- Error handling: Log template selection and any truncation warnings

**Code Changes**:

```python
from request_tracker_utils.utils.label_config import LABEL_TEMPLATES
from request_tracker_utils.utils.text_utils import truncate_text_to_width

@bp.route('/labels/print')
def print_label():
    size = request.args.get('size', 'large')

    # Validate size parameter
    if size not in ['large', 'small']:
        return jsonify({"error": "Invalid size. Must be 'large' or 'small'"}), 400

    # Get template configuration
    template_config = LABEL_TEMPLATES.get(size, LABEL_TEMPLATES['large'])

    # ... existing asset lookup logic ...

    # Truncate asset name based on template
    truncated_name = truncate_text_to_width(
        asset['Name'],
        'Helvetica',
        template_config.font_size_pt,
        template_config.text_max_width_mm
    )

    # Generate QR and barcode with template-specific sizing
    qr_box_size = 5 if size == 'small' else 10
    qr_code = generate_qr_code(tracking_url, box_size=qr_box_size)
    barcode = generate_barcode(
        asset['AssetTag'],
        width_mm=template_config.barcode_width_mm,
        height_mm=template_config.barcode_height_mm
    )

    # Select template
    template_name = 'small_label.html' if size == 'small' else 'label.html'

    # Render template
    return render_template(
        template_name,
        asset=asset,
        qr_code=qr_code,
        barcode=barcode,
        truncated_name=truncated_name,
        tracking_url=tracking_url
    )
```

---

### T008 [US1] - Add default size selection logic based on asset type

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/routes/label_routes.py` (MODIFY)  
**Estimate**: 30 minutes

**Description**: Add logic to determine default label size based on asset Type field (chargers → small, others → large). This will be used by the UI to pre-select the radio button.

**Acceptance Criteria**:

- Create helper function: `get_default_label_size(asset_type: str) -> str`
- Logic: Return `'small'` if `asset_type` in `['Charger', 'Power Adapter', 'Cable']`, else `'large'`
- Make asset type list configurable (use `current_app.config.get('SMALL_LABEL_ASSET_TYPES', ['Charger', 'Power Adapter', 'Cable'])`)
- Case-insensitive comparison (`asset_type.lower()`)
- Pass `default_size` to template context (used by label form in T009)
- Function used in both single-print and batch-print routes

**Implementation**:

```python
def get_default_label_size(asset_type: str) -> str:
    """Determine default label size based on asset type."""
    small_label_types = current_app.config.get(
        'SMALL_LABEL_ASSET_TYPES',
        ['Charger', 'Power Adapter', 'Cable']
    )
    return 'small' if asset_type.lower() in [t.lower() for t in small_label_types] else 'large'
```

---

### T009 [US1] - Create/modify label form with size toggle UI

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/templates/label_form.html` (MODIFY or CREATE)  
**Estimate**: 45 minutes

**Description**: Create or modify the label selection form to include radio buttons for Large/Small label size with default pre-selection based on asset type.

**Acceptance Criteria**:

- File at `request_tracker_utils/templates/label_form.html` (create if doesn't exist, modify if exists)
- Form submits to `/labels/print` with GET method
- Hidden input: `<input type="hidden" name="id" value="{{ asset.id }}">`
- Radio buttons for size selection:
  ```html
  <label>
    <input type="radio" name="size" value="large" {% if default_size == 'large'
    %}checked{% endif %}> Large Label (100mm x 62mm) - Includes serial number
  </label>
  <label>
    <input type="radio" name="size" value="small" {% if default_size == 'small'
    %}checked{% endif %}> Small Label (29mm x 90.3mm) - Compact, no serial
    number
  </label>
  ```
- Submit button: "Preview Label"
- Help note or tooltip (per FR-010): Display inline note below radio buttons or help icon with tooltip: "ℹ️ <strong>Note:</strong> Small labels omit serial numbers to save space. Select Large label if serial tracking is required for this asset."
- Help styling: Light blue background (#d1ecf1) with info icon, or use title attribute on help icon for tooltip
- Semantic HTML with proper labels (no WCAG compliance required, but use best practices)
- Context variable expected: `asset`, `default_size`

**Help Note Example**:

```html
<div
  class="help-note"
  style="background: #d1ecf1; padding: 8px; margin-top: 10px; border-left: 3px solid #0c5460; font-size: 0.9em;"
>
  ℹ️ <strong>Note:</strong> Small labels omit serial numbers to save space.
  Select <strong>Large label</strong> if serial tracking is required for this
  asset.
</div>
```

---

### T010 [US1] - Add preview warnings for truncation and scannability

**User Story**: US1 - Quick single-label print  
**File**: `request_tracker_utils/templates/small_label.html` (MODIFY)  
**Estimate**: 25 minutes

**Description**: Add conditional warning messages to small label template when asset name is truncated or QR code may be unscannable (per FR-007).

**Acceptance Criteria**:

- Check if `truncated_name` ends with "..." (indicates truncation)
- Display truncation warning banner above print button: "⚠️ Asset name truncated to fit small label. Full name: [original name]"
- Check if tracking URL length > 80 characters (may exceed small QR capacity)
- Display QR scannability warning if URL too long: "⚠️ QR code may be difficult to scan at small size. Consider using large label."
- Both warnings styled with yellow background, black text, visible only on screen (not printed)
- Warnings include `.no-print` class
- Add `tracking_url` to template context in route handler for length check

**Template Addition**:

```jinja2
{% if truncated_name.endswith('...') %}
<div class="truncation-warning no-print" style="background: #fff3cd; padding: 10px; margin-bottom: 10px; border: 1px solid #ffc107;">
    ⚠️ <strong>Asset name truncated</strong> to fit small label.<br>
    Full name: {{ asset.Name }}
</div>
{% endif %}

{% if tracking_url|length > 80 %}
<div class="qr-warning no-print" style="background: #fff3cd; padding: 10px; margin-bottom: 10px; border: 1px solid #ffc107;">
    ⚠️ <strong>QR code may be difficult to scan</strong> at small size due to long URL.<br>
    Consider using <strong>Large label</strong> for better scannability.
</div>
{% endif %}
```

---

### T011 [US1] - Integration test for US1 acceptance scenarios

**User Story**: US1 - Quick single-label print  
**File**: `tests/test_label_routes.py` (MODIFY)  
**Estimate**: 45 minutes

**Description**: Add integration tests covering US1 acceptance scenarios (Charger asset defaults to Small, preview shows correct layout, QR/barcode present).

**Acceptance Criteria**:

- Test 1: `test_charger_defaults_to_small_label()`
  - Mock asset with Type="Charger"
  - GET `/labels/print?id=<charger_id>`
  - Assert default_size == 'small' in response context
  - Assert template used is `small_label.html`
- Test 2: `test_small_label_omits_serial_number()`
  - GET `/labels/print?id=<charger_id>&size=small`
  - Assert `show_serial == False` in template config
  - Assert "SerialNumber" not in rendered HTML
- Test 3: `test_small_label_dimensions()`
  - GET `/labels/print?id=<charger_id>&size=small`
  - Assert `@page { size: 29mm 90.3mm }` in response HTML
- Test 4: `test_qr_barcode_present_in_small_label()`
  - GET `/labels/print?id=<charger_id>&size=small`
  - Assert QR code base64 image present in HTML
  - Assert barcode base64 image present in HTML
- Test 5: `test_backward_compatibility_no_size_param()`
  - GET `/labels/print?id=<laptop_id>` (no size param)
  - Assert template used is `label.html` (large)
- Uses Flask test client and pytest fixtures for asset mocking

**Checkpoint**: ✅ **US1 Complete** - Small label printing for chargers is functional and tested.

---

## Phase 3: User Story 2 - Full-size label for other assets (Priority P1)

**Goal**: Preserve existing full-size label behavior for non-charger assets (Chromebooks, laptops, etc.) with serial number display.

**Independent Test Criteria**:

- Load non-Charger asset → `labels/print` UI defaults to Large label
- Preview includes serial number
- Layout matches existing full-size label

---

### T012 [US2] - Ensure large label template compatibility

**User Story**: US2 - Full-size label for other assets  
**File**: `request_tracker_utils/templates/label.html` (VERIFY/NO CHANGE)  
**Estimate**: 15 minutes

**Description**: Verify existing `label.html` template works with modified route logic and no regressions introduced.

**Acceptance Criteria**:

- Review existing `label.html` to confirm it expects: `asset`, `qr_code`, `barcode` context variables
- Verify @page dimensions are `100mm 62mm` (existing)
- Confirm serial number is displayed (existing behavior)
- No changes needed if existing template compatible
- If template expects different context variables, update route handler to maintain compatibility

**Testing**: Manual spot-check by loading large label preview for a Chromebook asset.

---

### T013 [US2] [P] - Add default size logic for non-charger assets

**User Story**: US2 - Full-size label for other assets  
**File**: `request_tracker_utils/routes/label_routes.py` (VERIFY)  
**Estimate**: 10 minutes

**Description**: Verify `get_default_label_size()` helper correctly returns `'large'` for all non-charger asset types.

**Acceptance Criteria**:

- Function returns `'large'` for asset types: "Chromebook", "Laptop", "Hotspot", "iPad", etc.
- Only returns `'small'` for configured small label types (Charger, Power Adapter, Cable)
- Case-insensitive matching works correctly
- Test with various asset types to confirm defaults

**Testing**: Unit test in `test_label_config.py` (created in T014).

---

### T014 [US2] [P] - Integration test for US2 acceptance scenario

**User Story**: US2 - Full-size label for other assets  
**File**: `tests/test_label_routes.py` (MODIFY)  
**Estimate**: 30 minutes

**Description**: Add integration test covering US2 acceptance scenario (non-Charger asset defaults to Large label with serial number).

**Acceptance Criteria**:

- Test: `test_non_charger_defaults_to_large_label()`
  - Mock asset with Type="Chromebook"
  - GET `/labels/print?id=<chromebook_id>`
  - Assert default_size == 'large' in response context
  - Assert template used is `label.html`
  - Assert serial number present in rendered HTML
- Test: `test_large_label_includes_serial_number()`
  - GET `/labels/print?id=<chromebook_id>&size=large`
  - Assert `show_serial == True` in template config
  - Assert asset SerialNumber appears in HTML
- Uses Flask test client and pytest fixtures

**Checkpoint**: ✅ **US2 Complete** - Large label behavior preserved for non-charger assets.

---

## Phase 4: User Story 3 - Manual override and batch printing (Priority P2)

**Goal**: Enable manual override of default label size and support batch printing with per-item size selection.

**Independent Test Criteria**:

- Toggle size for individual asset overrides default
- Batch print respects per-item defaults and overrides
- Mixed batch (chargers + laptops) prints correct sizes

---

### T015 [US3] - Add batch print route with per-item size support

**User Story**: US3 - Manual override and batch printing  
**File**: `request_tracker_utils/routes/label_routes.py` (MODIFY or NEW)  
**Estimate**: 60 minutes

**Description**: Create or modify batch print route to accept per-item size overrides and generate multiple labels in one PDF or print job.

**Acceptance Criteria**:

- Route: `@bp.route('/labels/batch-print', methods=['POST'])`
- Accepts JSON payload:
  ```json
  {
    "assets": [
      { "id": 12345, "size": "small" },
      { "id": 12346, "size": "large" },
      { "id": 12347 } // uses default based on asset type
    ]
  }
  ```
- For each asset: Fetch asset data, determine size (use override if provided, else default)
- Generate labels using same logic as single-print route
- Return multi-page PDF with one label per page
- Each page sized to appropriate label dimensions
- Error handling: Skip assets that fail to load, return partial results with warnings

---

### T016 [US3] - Add batch label form UI with per-item toggles

**User Story**: US3 - Manual override and batch printing  
**File**: `request_tracker_utils/templates/batch_labels_form.html` (MODIFY or CREATE)  
**Estimate**: 60 minutes

**Description**: Create or modify batch label form to allow per-item size selection with default pre-selection based on asset types.

**Acceptance Criteria**:

- Form displays list of assets (from query param or session)
- Each row shows: Asset ID, Asset Name, Asset Type, Size Toggle (radio buttons)
- Size toggle pre-selected based on asset type (via `get_default_label_size()`)
- Submit button: "Print All Labels"
- JavaScript collects form data and POSTs to `/labels/batch-print`
- Visual grouping: Show chargers grouped separately for clarity
- Allow "Select All Small" / "Select All Large" bulk action buttons

---

### T017 [US3] - Integration test for US3 acceptance scenarios

**User Story**: US3 - Manual override and batch printing  
**File**: `tests/test_label_routes.py` (MODIFY)  
**Estimate**: 45 minutes

**Description**: Add integration tests covering US3 acceptance scenarios (batch print with mixed assets, manual overrides).

**Acceptance Criteria**:

- Test: `test_batch_print_mixed_defaults()`
  - POST `/labels/batch-print` with 3 chargers and 2 Chromebooks (no size overrides)
  - Assert 5 labels generated: 3 small (chargers), 2 large (Chromebooks)
- Test: `test_batch_print_manual_override()`
  - POST `/labels/batch-print` with charger asset, size override to "large"
  - Assert charger label generated at large size despite being charger type
- Test: `test_batch_print_preserves_overrides()`
  - POST `/labels/batch-print` with mixed assets and overrides
  - Assert each asset respects its explicit override or default
- Uses Flask test client, mocks asset data

**Checkpoint**: ✅ **US3 Complete** - Batch printing with per-item size control is functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Objective**: Final touches, documentation, and production readiness.

---

### T018 - Add PDF export support for small labels

**User Story**: US1/US2/US3 (cross-cutting)  
**File**: `request_tracker_utils/utils/pdf_generator.py` (MODIFY)  
**Estimate**: 60 minutes

**Description**: Extend `create_pdf_label()` function to support small label dimensions and generate proper PDF with embedded QR/barcode.

**Acceptance Criteria**:

- Function signature: `create_pdf_label(asset_data: dict, template_config: LabelTemplate, qr_image: bytes, barcode_image: bytes) -> bytes`
- Uses ReportLab's `canvas.Canvas` with `pagesize=(template_config.width_mm * mm, template_config.height_mm * mm)`
- Draws QR code at correct position (2mm, 4mm) with size `template_config.qr_size_mm`
- Draws truncated asset name at center with font size `template_config.font_size_pt`
- Draws barcode at bottom with dimensions `template_config.barcode_width_mm x template_config.barcode_height_mm`
- Omits serial number if `template_config.show_serial == False`
- Returns PDF bytes (BytesIO buffer)
- Integrate into `print_label()` route: Check `format` query param, return PDF if `format='pdf'`

**Implementation**:

```python
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from io import BytesIO

def create_pdf_label(asset_data, template_config, qr_image_b64, barcode_image_b64):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(template_config.width_mm * mm, template_config.height_mm * mm))

    # Decode base64 images
    # ... (decode qr_image_b64 and barcode_image_b64 to image objects)

    # Draw QR code
    c.drawImage(qr_image, 2*mm, 4*mm, width=template_config.qr_size_mm*mm, height=template_config.qr_size_mm*mm)

    # Draw truncated asset name
    c.setFont('Helvetica', template_config.font_size_pt)
    c.drawString(...)

    # Draw barcode
    c.drawImage(barcode_image, ..., width=template_config.barcode_width_mm*mm, height=template_config.barcode_height_mm*mm)

    c.save()
    return buffer.getvalue()
```

---

## Unit Tests (Optional - Not in User Stories)

The following unit tests are optional (no explicit testing requirement in spec). Include if TDD approach desired:

### T-UT1 - Unit tests for LabelTemplate dataclass

**File**: `tests/test_label_config.py` (NEW)  
**Estimate**: 30 minutes

**Description**: Unit tests for `LabelTemplate` dataclass and `LABEL_TEMPLATES` dictionary.

**Tests**:

- `test_label_template_creation()`: Create LabelTemplate instances, verify all fields
- `test_label_templates_dict_keys()`: Assert 'large' and 'small' keys exist
- `test_large_template_dimensions()`: Assert large template has correct dimensions
- `test_small_template_dimensions()`: Assert small template has correct dimensions
- `test_small_template_hides_serial()`: Assert small template `show_serial == False`

---

### T-UT2 - Unit tests for text truncation function

**File**: `tests/test_text_truncation.py` (NEW)  
**Estimate**: 45 minutes

**Description**: Comprehensive unit tests for `truncate_text_to_width()` function.

**Tests**:

- `test_text_fits_no_truncation()`: Short text returns unchanged
- `test_text_too_long_truncates()`: Long text truncated with "..."
- `test_empty_string()`: Empty string returns ""
- `test_single_char_too_wide()`: Single char wider than max returns "..."
- `test_ellipsis_width_accounted()`: Truncation leaves room for "..."
- `test_different_fonts()`: Test with Helvetica, Helvetica-Bold, Times
- `test_different_font_sizes()`: Test with 8pt, 10pt, 14pt
- `test_unicode_characters()`: Test with emoji, accented chars

---

## Task Dependencies & Execution Order

### Critical Path (Sequential)

```
T001 (label_config.py) → T007 (route handler) → T005 (small template) → T010 (preview warnings)
                      ↓
T002 (text_utils.py) → T007 (route handler)
                      ↓
T003 (QR sizing) → T007 (route handler)
T004 (barcode sizing) → T007 (route handler)
```

### Parallelizable Workflows

**Phase 1 (Setup) - All Parallel**:

```
T001 (label_config.py) [P]
T002 (text_utils.py) [P]
T003 (QR function) [P]
T004 (barcode function) [P]
```

**Phase 2 (US1 Core) - Partial Parallel**:

```
T005 (small template) [P]  \
T006 (CSS) [P]              → T010 (warnings) → T011 (tests)
T007 (route handler)       /
T008 (default logic) → T009 (form UI)
```

**Phase 3 (US2) - Parallel**:

```
T012 (verify large template) [P]
T013 (default logic verify) [P]
T014 (tests) [P]
```

**Phase 4 (US3) - Sequential**:

```
T015 (batch route) → T016 (batch UI) → T017 (batch tests)
```

---

## Implementation Strategy

### MVP Scope (User Story 1 Only)

**Tasks**: T001-T011 (11 tasks)  
**Estimate**: 6-7 hours  
**Deliverable**: Single-label printing for chargers with automatic Small label default

**Why MVP First**:

- User Story 1 delivers immediate value (most common use case: charger labels)
- Independently testable and deployable
- Validates technical approach (QR/barcode sizing, truncation algorithm)
- Can be used in production while US2/US3 are in progress

### Incremental Delivery

1. **Sprint 1**: MVP (US1) - Tasks T001-T011
2. **Sprint 2**: US2 (Large label preservation) - Tasks T012-T014
3. **Sprint 3**: US3 (Batch printing) - Tasks T015-T017
4. **Sprint 4**: Polish - Task T018 (PDF export)

### Parallel Execution Examples

**Phase 1 (4 developers)**:

- Dev 1: T001 (label_config.py)
- Dev 2: T002 (text_utils.py)
- Dev 3: T003 (QR sizing)
- Dev 4: T004 (barcode sizing)

**Phase 2 (3 developers after Phase 1 complete)**:

- Dev 1: T005 + T010 (small template + warnings)
- Dev 2: T007 + T008 (route handler + default logic)
- Dev 3: T009 (form UI)

**Phase 3 (all parallel, 3 developers)**:

- Dev 1: T012
- Dev 2: T013
- Dev 3: T014

---

## Definition of Done (Per Task)

Each task is considered complete when:

1. ✅ **Code written** - Implementation matches acceptance criteria
2. ✅ **Manual test** - Task creator has tested locally (if UI/route)
3. ✅ **Committed** - Code pushed to feature branch `003-rtutils-should-offer`
4. ✅ **Documented** - Docstrings added for new functions, comments for complex logic
5. ✅ **No regressions** - Existing large label tests still pass (run `pytest tests/test_label_routes.py`)

**Per User Story Checkpoint**:

- All tasks in story phase complete
- Independent test criteria validated (per spec.md acceptance scenarios)
- Manual print test conducted (QR/barcode scanned with phone)

---

## Next Steps

1. **Review this task list** with team for estimates and priority validation
2. **Assign tasks** to developers (consider parallel execution opportunities)
3. **Create GitHub issues** from tasks (link to this file for context)
4. **Begin Sprint 1** (MVP - Tasks T001-T011)
5. **Run `/speckit.validate`** after each user story checkpoint to verify spec compliance

---

**Generated by**: `/speckit.tasks` command  
**Source documents**: [spec.md](./spec.md), [plan.md](./plan.md), [data-model.md](./data-model.md), [contracts/api.md](./contracts/api.md)  
**Implementation starts**: After team review and task assignment
