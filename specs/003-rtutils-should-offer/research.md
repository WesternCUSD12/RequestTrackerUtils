# Phase 0: Research & Decisions

## Overview

This document captures technical research and decisions for the small label template feature (1.1" x 3.5" / 29mm x 90.3mm). All [NEEDS CLARIFICATION] items from the spec have been resolved during the clarify phase.

## Research Questions

### 1. QR Code Size & Scannability at 29mm x 90.3mm

**Question**: What QR code dimensions ensure 95% scannability on small labels?

**Research**:

- Current large labels (100mm x 62mm) use QR codes approximately 50mm x 50mm
- QR code minimum readable size depends on:
  - Error correction level (L/M/Q/H)
  - Data density (full URL ~50-80 characters)
  - Print resolution (thermal printers typically 203 DPI)
  - Scanning distance (handheld scanners: 5-15cm typical)
- Industry standards suggest minimum 15mm x 15mm for URL-encoded QR codes with medium error correction
- At 29mm width, QR code can occupy ~18-20mm square (leaving margins for text)

**Decision**:

- Use **20mm x 20mm QR codes** on small labels
- Set error correction to **Medium (M)** for balance of data/redundancy
- Full asset tracking URL fits within this constraint
- Existing `qrcode` library supports box_size adjustment: `qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=1)`
- Generate at high DPI (300) to ensure crisp printing on thermal printers

**Validation**: Test print and scan at Phase 2 (Implementation).

---

### 2. Dynamic Text Truncation Algorithm

**Question**: How to implement fit-to-width truncation for asset names on small labels?

**Research**:

- Current large labels display full asset names in fixed font (14pt sans-serif)
- Small labels have ~70mm horizontal space for text (90.3mm - 20mm QR)
- Two approaches:
  1. **CSS-based**: `text-overflow: ellipsis` with `overflow: hidden` (simple, but no print-time calculation)
  2. **Server-side**: Calculate character width using font metrics (precise, works with PDF generation)
- Font rendering: ReportLab's `stringWidth()` function calculates exact text width in points
- Target font: 10pt sans-serif for small labels (down from 14pt on large labels)

**Decision**:

- **Server-side truncation** using ReportLab's `pdfmetrics.stringWidth()` before rendering
- Algorithm:

  ```python
  from reportlab.pdfbase import pdfmetrics
  from reportlab.pdfbase.ttfonts import TTFont

  def truncate_text_to_width(text, font_name, font_size, max_width_mm):
      max_width_pt = max_width_mm * 2.834645  # mm to points conversion
      full_width = pdfmetrics.stringWidth(text, font_name, font_size)
      if full_width <= max_width_pt:
          return text

      # Binary search for max characters that fit
      ellipsis_width = pdfmetrics.stringWidth("...", font_name, font_size)
      available_width = max_width_pt - ellipsis_width

      left, right = 0, len(text)
      while left < right:
          mid = (left + right + 1) // 2
          test_text = text[:mid]
          if pdfmetrics.stringWidth(test_text, font_name, font_size) <= available_width:
              left = mid
          else:
              right = mid - 1

      return text[:left] + "..."
  ```

- Also apply CSS fallback (`text-overflow: ellipsis`) for HTML preview consistency

**Validation**: Test with long asset names (50+ characters) at Phase 2.

---

### 3. Barcode Width Optimization

**Question**: Can Code128 barcodes fit horizontally on 29mm x 90.3mm labels?

**Research**:

- Current large labels use Code128 barcodes with asset tag codes (e.g., "ASSET-12345")
- Code128 variable width depends on character count: typical asset tags are 8-12 characters
- Barcode height can be reduced for small labels (current: ~15mm; small: ~8mm)
- Width compression: Code128 supports high-density encoding (11 modules per character)
- At 90.3mm width, full barcode can span 70-80mm (accounting for quiet zones)

**Decision**:

- Use **Code128** barcode at reduced height (**8mm**) for small labels
- Set barcode width to **70mm** (fits comfortably with 10mm margins)
- Use `python-barcode` library with custom sizing:

  ```python
  from barcode import Code128
  from barcode.writer import ImageWriter

  options = {
      'module_width': 0.2,  # mm per module
      'module_height': 8.0,  # mm
      'quiet_zone': 2.5,    # mm
      'font_size': 8,       # pt
      'text_distance': 1.0  # mm
  }
  barcode = Code128(asset_code, writer=ImageWriter())
  ```

- Position barcode at bottom of label (same as large labels)

**Validation**: Test scannability with handheld scanners at Phase 2.

---

### 4. CSS @page Sizing Strategy

**Question**: How to support dual label sizes in same Flask app with @page rules?

**Research**:

- Current approach: Single `@page { size: 100mm 62mm }` rule in base.html
- Two options for dual sizing:
  1. **Template-specific CSS**: Override @page in label.html vs small_label.html
  2. **Dynamic CSS via template variable**: Pass `label_size_class` to base.html and conditionally render @page
- Browser print behavior: @page rules override system print settings; last rule wins if multiple defined

**Decision**:

- **Template-specific CSS** (option 1) for clarity and maintainability
- Keep existing `label.html` with `@page { size: 100mm 62mm }`
- Create new `small_label.html` with `@page { size: 29mm 90.3mm; margin: 0; }`
- Route logic in `label_routes.py`:
  ```python
  @bp.route('/labels/print')
  def print_label():
      size = request.args.get('size', 'large')  # default to large
      template = 'small_label.html' if size == 'small' else 'label.html'
      # ... asset lookup logic ...
      return render_template(template, asset=asset, qr_code=qr, barcode=bc)
  ```
- Print CSS:
  ```css
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
  ```

**Validation**: Test in Chrome, Firefox, Safari print dialogs at Phase 2.

---

### 5. Default Size Selection Logic

**Question**: How to implement "chargers default to small" without database changes?

**Research**:

- Spec requirement: "Chargers and similar accessories should default to small labels"
- Asset types stored in RT custom fields (examined via `get_custom_field_value()` in label_routes.py)
- Current RT schema: Assets have "Type" custom field (values: "Chromebook", "Charger", "Hotspot", etc.)
- No database writes allowed per constitutional principle

**Decision**:

- **Client-side default selection** based on asset type
- Modify label form UI to pre-select radio button:
  ```python
  # In label_routes.py or form rendering route
  asset_type = get_custom_field_value(asset_id, 'Type')
  default_size = 'small' if asset_type in ['Charger', 'Power Adapter', 'Cable'] else 'large'
  ```
- HTML template with dynamic default:
  ```html
  <form method="GET" action="/labels/print">
    <input type="hidden" name="id" value="{{ asset.id }}" />
    <label>
      <input type="radio" name="size" value="large" {% if default_size ==
      'large' %}checked{% endif %}> Large Label (100mm x 62mm)
    </label>
    <label>
      <input type="radio" name="size" value="small" {% if default_size ==
      'small' %}checked{% endif %}> Small Label (29mm x 90.3mm)
    </label>
    <button type="submit">Print Label</button>
  </form>
  ```
- No persistence: Each form load recalculates default from asset type

**Validation**: Test with charger assets vs. Chromebook assets at Phase 2.

---

## Technology Decisions

### PDF Generation Library

**Decision**: Use **ReportLab** for PDF exports (already dependency for other features)

**Rationale**:

- Already in `pyproject.toml` (version 3.6+)
- Precise control over QR/barcode positioning
- Supports custom page sizes (`pagesize=(29*mm, 90.3*mm)`)
- Compatible with existing `generate_qr_code()` and `generate_barcode()` Base64 approach

**Implementation**:

```python
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

def create_small_label_pdf(asset_name, asset_code, qr_image, barcode_image):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(90.3*mm, 29*mm))

    # Draw QR code (20mm x 20mm, left side)
    c.drawImage(qr_image, 2*mm, 4*mm, width=20*mm, height=20*mm)

    # Draw truncated asset name (10pt, center)
    truncated_name = truncate_text_to_width(asset_name, 'Helvetica', 10, 60)
    c.setFont('Helvetica', 10)
    c.drawString(25*mm, 20*mm, truncated_name)

    # Draw barcode (70mm x 8mm, bottom)
    c.drawImage(barcode_image, 10*mm, 1*mm, width=70*mm, height=8*mm)

    c.save()
    return buffer.getvalue()
```

---

### Template Architecture

**Decision**: Separate templates (`label.html` for large, `small_label.html` for small)

**Rationale**:

- Clear separation of concerns (100mm x 62mm vs 29mm x 90.3mm layouts)
- Avoids complex conditional logic in single template
- Easier to maintain distinct @page rules and element positioning
- Minimal code duplication (both share base.html for common assets)

**Structure**:

```
templates/
  base.html           # Common head, CSS, JS (no @page rule)
  label.html          # Large label (extends base, includes @page 100mm x 62mm)
  small_label.html    # Small label (extends base, includes @page 29mm x 90.3mm)
  label_form.html     # New: size selection form with radio buttons
```

---

## Open Questions

_None remaining. All clarifications resolved during clarify phase._

---

## Phase 0 Completion Checklist

- [x] QR code sizing researched (20mm x 20mm, Medium error correction)
- [x] Text truncation algorithm designed (ReportLab stringWidth + binary search)
- [x] Barcode optimization confirmed (Code128, 70mm x 8mm)
- [x] CSS @page strategy decided (separate templates with distinct rules)
- [x] Default size logic designed (client-side based on asset Type field)
- [x] PDF generation approach confirmed (ReportLab with custom pagesize)
- [x] Template architecture finalized (separate label.html / small_label.html)
- [x] No blockers remaining for Phase 1 design

**Gate Status**: ✅ Ready to proceed to Phase 1 (Design)
