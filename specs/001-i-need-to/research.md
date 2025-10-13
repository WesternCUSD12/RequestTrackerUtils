# Research: Streamlined Asset Creation with Batch Entry

**Feature**: 001-i-need-to  
**Date**: 2025-10-08  
**Status**: Complete

## Overview

Research for implementing rapid batch asset creation with form persistence and automatic label printing in the existing RequestTrackerUtils Flask application.

## Research Areas

### 1. Browser Session Storage for Form Persistence

**Decision**: Use browser `sessionStorage` API

**Rationale**:

- Automatically cleared when browser tab/window closes (matches FR-001 requirement)
- Survives page refreshes and form submissions
- Simple JavaScript API with broad browser support
- No server-side session management needed
- 5-10MB storage limit per origin (sufficient for form data)

**Alternatives Considered**:

- `localStorage`: Rejected - persists across browser restarts (not desired per clarifications)
- Cookies: Rejected - size limitations, sent with every request (unnecessary overhead)
- Server-side sessions: Rejected - adds complexity, requires session cleanup logic

**Implementation Pattern**:

```javascript
// Store form values after each successful submission
sessionStorage.setItem('assetForm', JSON.stringify(formData))

// Restore on page load
const saved = JSON.parse(sessionStorage.getItem('assetForm') || '{}')

// Clear all button
sessionStorage.removeItem('assetForm')
```

**Browser Compatibility**: IE 8+, Chrome, Firefox, Safari, Edge (100% coverage for target browsers)

---

### 2. Automatic Browser Print Dialog Triggering

**Decision**: Use `window.print()` API with hidden iframe containing label HTML

**Rationale**:

- Native browser print dialog (no plugins required)
- Works cross-browser with minor CSS adjustments
- Allows print preview before printing (user can cancel)
- Handles QR code and barcode rendering correctly
- Existing label generation can be reused

**Alternatives Considered**:

- Direct printer access: Rejected - requires browser extensions, security concerns
- PDF download only: Rejected - doesn't meet automatic print requirement
- New tab with auto-print: Rejected - blocked by popup blockers, leaves tabs open

**Implementation Pattern**:

```javascript
// After asset creation succeeds
fetch('/labels/print?asset_id=' + assetId)
  .then(response => response.text())
  .then(html => {
    // Create hidden iframe
    const iframe = document.createElement('iframe')
    iframe.style.display = 'none'
    document.body.appendChild(iframe)

    // Load label HTML
    iframe.contentDocument.write(html)
    iframe.contentDocument.close()

    // Trigger print dialog
    iframe.contentWindow.print()

    // Cleanup after print/cancel
    setTimeout(() => iframe.remove(), 1000)
  })
```

**Browser Compatibility**: Chrome, Firefox, Safari, Edge (modern browsers) - graceful degradation for older browsers (manual print button shown)

---

### 3. Organization-Wide Serial Number Uniqueness Validation

**Decision**: Query RT API before asset creation with serial number filter

**Rationale**:

- RT is the source of truth for all assets
- Existing RT API supports custom field queries
- Validates against all assets organization-wide
- Prevents duplicate creation at API level
- ~200-500ms query latency acceptable for validation

**Alternatives Considered**:

- Local database cache: Rejected - adds sync complexity, stale data risk
- Client-side validation only: Rejected - race conditions possible
- Post-creation validation: Rejected - harder to rollback, poor UX

**Implementation Pattern**:

```python
# In asset creation route
def validate_serial_uniqueness(serial_number):
    query = [{'field': 'CF.{Serial Number}',
              'operator': '=',
              'value': serial_number}]
    existing = search_assets(query, config)
    return len(existing) == 0

# Before creating asset
if not validate_serial_uniqueness(serial_number):
    return error("Serial number already exists")
```

**Performance**: 200-500ms per validation (acceptable for success criteria of < 2s total per asset)

---

### 4. Asset Tag Sequence Digit Expansion

**Decision**: Dynamic zero-padding adjustment when sequence exceeds current digit count

**Rationale**:

- Existing AssetTagManager now uses 5-digit zero-padding (00001-99999)
- When reaching 100000, automatically use 6 digits (no leading zeros dropped)
- Maintains sortability and consistency
- No manual intervention required
- Prefix (W12-) remains unchanged

**Alternatives Considered**:

- Fixed 6+ digit padding from start: Rejected - wastes label space, existing tags are 5-digit
- Manual sequence reset: Rejected - requires admin intervention, error-prone
- New prefix after overflow: Rejected - breaks organizational naming convention

**Implementation Pattern**:

```python
def get_next_tag(self):
    current_number = self.get_current_sequence()
  # Calculate required digits (minimum 5)
  digit_count = max(5, len(str(current_number)))
    return f"{self.prefix}{current_number:0{digit_count}d}"

# Examples:
# 00001 → W12-00001 (5 digits)
# 99999 → W12-99999 (5 digits)
# 100000 → W12-100000 (6 digits, automatic expansion)
# 999999 → W12-999999 (6 digits)
# 1000000 → W12-1000000 (7 digits, automatic expansion)
```

**Testing**: Verify no gaps or duplicates across digit boundary transitions

---

### 5. Partial Failure Handling (RT Success, Label Failure)

**Decision**: Show success message with asset tag and provide "Retry Print" button

**Rationale**:

- Asset is successfully created in RT (source of truth)
- Label can be regenerated any time from asset tag
- User can continue with next asset without blocking
- Clear feedback about what succeeded vs. failed
- Matches existing label printing patterns in codebase

**Alternatives Considered**:

- Rollback asset creation: Rejected - complicated, RT is source of truth
- Block next entry until printed: Rejected - interrupts batch workflow
- Auto-retry: Rejected - may fail repeatedly, annoying for user

**Implementation Pattern**:

```python
try:
    # Create asset in RT
    asset_id = create_asset_in_rt(form_data)
    asset_tag = get_current_tag()

    try:
        # Attempt label generation
        generate_and_print_label(asset_id)
        return success(asset_tag, label_printed=True)
    except LabelError:
        # Asset created but label failed
        return success(asset_tag, label_printed=False,
                      retry_url=f'/labels/print?asset_id={asset_id}')
except RTError:
    # Asset creation failed - preserve form data
    return error("Asset creation failed", preserve_form=True)
```

**User Flow**: Success message → "Label failed to print" → "Retry Print" button → continue to next asset

---

### 6. Form Reset Behavior and Field Persistence Rules

**Decision**: Dual-mode form with selective field clearing

**Rationale**:

- Common fields (manufacturer, model, category, funding source) persist
- Unique fields (serial number, internal name) clear after success
- "Clear All" button resets everything to empty
- Failed submissions preserve all fields for correction
- Aligns with rapid batch entry workflow

**Implementation**:

- Persisted fields: manufacturer, model, category, funding source, any custom fields marked "common"
- Cleared fields: serial number, internal asset name
- Manual override: any field can be edited; new value becomes persisted default

**JavaScript State Management**:

```javascript
const PERSISTED_FIELDS = ['manufacturer', 'model', 'category', 'funding']
const CLEARED_FIELDS = ['serial_number', 'internal_name']

function handleSuccess(response) {
  // Save persisted fields
  const formData = {}
  PERSISTED_FIELDS.forEach(field => {
    formData[field] = form[field].value
  })
  sessionStorage.setItem('assetForm', JSON.stringify(formData))

  // Clear unique fields
  CLEARED_FIELDS.forEach(field => {
    form[field].value = ''
  })

  // Focus first cleared field
  form.serial_number.focus()
}
```

---

## Best Practices Applied

### Flask Blueprint Organization

- Create new `asset_routes.py` blueprint for batch creation endpoints
- Mount under `/assets` prefix to separate from existing tags/labels
- Follow existing pattern in `tag_routes.py` and `label_routes.py`

### Template Inheritance

- Extend existing `base.html` template for consistent UI
- Reuse Bootstrap CSS classes and icon patterns
- Follow existing form structure patterns

### Error Handling

- Use Flask's `jsonify()` for API responses
- Include status codes (400 for validation, 500 for server errors)
- Log errors with `current_app.logger`
- Display user-friendly messages in UI

### Testing Strategy

- Integration tests for RT API interaction
- Browser tests for print dialog behavior
- Serial number uniqueness validation tests
- Session storage persistence tests
- Form state management tests

---

## Dependencies

**No new external dependencies required** - all functionality achievable with existing stack:

- Flask (web framework) ✓
- requests (RT API calls) ✓
- reportlab (PDF/label generation) ✓
- qrcode (QR code generation) ✓
- python-barcode (barcode generation) ✓
- Jinja2 (templating) ✓

Client-side uses only standard browser APIs (sessionStorage, window.print, fetch).

---

## Performance Considerations

**Per-Asset Creation Timeline**:

1. Serial number validation: 200-500ms (RT API query)
2. Asset creation in RT: 300-800ms (RT API POST)
3. Asset tag increment: <10ms (file write with lock)
4. Label generation: 100-300ms (PDF generation)
5. Print dialog trigger: <50ms (JavaScript execution)

**Total**: 600-1660ms per asset (well under 2-second target in SC-003)

**Batch of 10 Assets**:

- Average: 1.0s × 10 = 10 seconds
- User entry time: ~15-20 seconds (typing serial numbers)
- **Total estimate**: 25-30 seconds (well under 5-minute target in SC-001)

---

## Security Considerations

- **Authentication**: Existing RT token-based auth reused
- **Authorization**: Existing user permissions enforced
- **Input Validation**: Serial numbers, asset tags validated before RT API calls
- **XSS Protection**: All user input escaped in templates (Jinja2 auto-escaping)
- **CSRF Protection**: Flask's built-in CSRF protection applied to forms
- **Session Data**: sessionStorage isolated per origin, not transmitted to server

---

## Conclusion

All technical approaches validated and ready for Phase 1 design. No blocking issues identified. Existing codebase infrastructure supports all requirements without new external dependencies.
