# Data Model

## Overview

This feature adds a new small label template (29mm x 90.3mm) without requiring database schema changes. All data models are ephemeral (in-memory) or leverage existing RT asset metadata.

---

## Entities

### 1. LabelTemplate (Ephemeral)

**Purpose**: Represents label sizing and layout configuration

**Attributes**:
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | `str` | Template identifier | `"large"` or `"small"` |
| `width_mm` | `float` | Label width in millimeters | `100.0` (large), `29.0` (small) |
| `height_mm` | `float` | Label height in millimeters | `62.0` (large), `90.3` (small) |
| `qr_size_mm` | `float` | QR code dimension (square) | `50.0` (large), `20.0` (small) |
| `barcode_width_mm` | `float` | Barcode width | `80.0` (large), `70.0` (small) |
| `barcode_height_mm` | `float` | Barcode height | `15.0` (large), `8.0` (small) |
| `font_size_pt` | `int` | Asset name font size (points) | `14` (large), `10` (small) |
| `show_serial` | `bool` | Whether to display serial number | `True` (large), `False` (small) |
| `text_max_width_mm` | `float` | Max width for asset name text | `90.0` (large), `60.0` (small) |

**Lifecycle**: Created on-demand in `print_label()` route based on `size` query parameter

**Implementation**:

```python
# request_tracker_utils/utils/label_config.py
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

**Relationships**: None (standalone configuration)

**Validation Rules**:

- `name` must be `"large"` or `"small"`
- All dimension fields must be positive floats
- `font_size_pt` must be integer ≥ 6
- `text_max_width_mm` must be less than `width_mm`

---

### 2. Asset (Existing RT Entity)

**Purpose**: Represents physical hardware tracked in Request Tracker

**Relevant Fields** (from RT Custom Fields):
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | `int` | RT asset ID | `12345` |
| `Name` | `str` | Asset display name | `"Student Chromebook 101"` |
| `AssetTag` | `str` | Barcode-printed asset code | `"ASSET-12345"` |
| `Type` | `str` | Asset category | `"Chromebook"`, `"Charger"`, `"Hotspot"` |
| `SerialNumber` | `str` | Manufacturer serial | `"5CD1234ABC"` (optional for small labels) |

**Source**: Fetched via existing RT REST API in `label_routes.py:print_label()`

**Changes**: None (read-only for label generation)

---

### 3. PrintJob (Ephemeral)

**Purpose**: Represents a single label print request (in-memory only, no persistence)

**Attributes**:
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `asset_id` | `int` | RT asset ID being printed | `12345` |
| `template_name` | `str` | Selected label size | `"small"` |
| `asset_name` | `str` | Full asset name (pre-truncation) | `"Student Chromebook 101 - Room 204"` |
| `truncated_name` | `str` | Asset name after fit-to-width | `"Student Chromebook..."` |
| `asset_code` | `str` | Barcode value | `"ASSET-12345"` |
| `tracking_url` | `str` | Full URL for QR code | `"https://rt.example.edu/asset/12345"` |
| `qr_base64` | `str` | Base64-encoded QR image | `"data:image/png;base64,iVBOR..."` |
| `barcode_base64` | `str` | Base64-encoded barcode image | `"data:image/png;base64,iVBOR..."` |
| `format` | `str` | Output format | `"html"` or `"pdf"` |

**Lifecycle**:

1. Created in `print_label()` from request args and RT asset data
2. Passed to template rendering or PDF generation
3. Discarded after response sent (no persistence)

**Implementation**:

```python
# In label_routes.py
from typing import NamedTuple

class PrintJob(NamedTuple):
    asset_id: int
    template_name: str
    asset_name: str
    truncated_name: str
    asset_code: str
    tracking_url: str
    qr_base64: str
    barcode_base64: str
    format: str = 'html'
```

**Validation Rules**:

- `asset_id` must exist in RT
- `template_name` must be `"large"` or `"small"`
- `format` must be `"html"` or `"pdf"`
- `qr_base64` and `barcode_base64` must be valid data URIs

---

## Data Flow

### Print Label Request Flow

```
1. User submits form → GET /labels/print?id=12345&size=small&format=html
                         │
2. Route handler         │
   ├─ Parse query params │
   ├─ Fetch RT asset     │ (existing RT API)
   ├─ Load LabelTemplate │ (from LABEL_TEMPLATES dict)
   │                      │
3. Generate images       │
   ├─ generate_qr_code() │ (existing function, adjust size)
   ├─ generate_barcode() │ (existing function, adjust height/width)
   │                      │
4. Text processing       │
   └─ truncate_text()    │ (new function, uses ReportLab stringWidth)
                         │
5. Create PrintJob       │ (ephemeral NamedTuple)
                         │
6. Render output         │
   ├─ HTML: render_template('small_label.html', job=print_job)
   └─ PDF:  create_small_label_pdf(print_job) → BytesIO → send_file()
```

---

## Database Schema Changes

**None required.** This feature is purely rendering/presentation logic with no persistent state.

**Rationale**:

- Label templates are static configuration (code-based)
- Print jobs are ephemeral (no need to track history)
- Asset metadata already exists in RT (read-only access)
- Default size selection calculated on-the-fly from asset Type field

---

## Migration Strategy

**N/A** - No database migrations needed.

---

## Data Integrity Considerations

### RT Asset Data Consistency

- **Issue**: Asset name/type may change between form load and print
- **Mitigation**: Each print request fetches fresh data from RT API (no caching)
- **Validation**: Route handler returns 404 if asset_id not found in RT

### QR Code URL Stability

- **Issue**: RT base URL configuration must be consistent
- **Mitigation**: Read from `config.RT_BASE_URL` (existing pattern in codebase)
- **Validation**: Config validation at app startup (existing pattern)

### Truncation Consistency

- **Issue**: Asset name truncation must match preview vs. PDF
- **Mitigation**: Both HTML and PDF use same `truncate_text_to_width()` function
- **Validation**: Unit test compares HTML text and PDF text extraction

---

## Phase 1 Data Model Checklist

- [x] LabelTemplate dataclass defined with all sizing parameters
- [x] Asset entity documented (existing RT fields, read-only)
- [x] PrintJob ephemeral model defined (NamedTuple with validation)
- [x] Data flow diagram covers request → render pipeline
- [x] No database migrations required (confirmed)
- [x] Data integrity risks identified and mitigated
- [x] Configuration-driven design (templates as code, not DB records)

**Gate Status**: ✅ Ready for implementation (Phase 2)
