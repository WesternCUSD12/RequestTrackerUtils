# Quickstart: Streamlined Asset Creation with Batch Entry

**Feature**: 001-i-need-to  
**Date**: 2025-10-08  
**Audience**: Developers implementing this feature

## Overview

This quickstart guides you through implementing the batch asset creation feature in RequestTrackerUtils. The feature enables rapid entry of multiple identical assets by persisting common fields and auto-incrementing asset tags.

## Prerequisites

- Python 3.11+ installed
- Flask application running (RequestTrackerUtils)
- RT API credentials configured
- Familiarity with Flask blueprints and Jinja2 templates

## Implementation Steps

### Step 1: Create Asset Routes Blueprint

Create `request_tracker_utils/routes/asset_routes.py`:

```python
from flask import Blueprint, jsonify, request, current_app, render_template
from request_tracker_utils.utils.rt_api import search_assets, rt_api_request
from request_tracker_utils.routes.tag_routes import AssetTagManager

bp = Blueprint('asset_routes', __name__, url_prefix='/assets')

@bp.route('/create', methods=['POST'])
def create_asset():
    """Create new asset with automatic tag assignment."""
    data = request.get_json()

    # Validate required fields
    serial_number = data.get('serial_number')
    if not serial_number:
        return jsonify({'success': False, 'error': 'Missing required field: serial_number', 'field': 'serial_number'}), 400

    manufacturer = data.get('manufacturer')
    if not manufacturer:
        return jsonify({'success': False, 'error': 'Missing required field: manufacturer', 'field': 'manufacturer'}), 400

    model = data.get('model')
    if not model:
        return jsonify({'success': False, 'error': 'Missing required field: model', 'field': 'model'}), 400

    # Validate serial number uniqueness
    try:
        query = [{'field': 'CF.{Serial Number}', 'operator': '=', 'value': serial_number}]
        existing = search_assets(query, current_app.config)
        if len(existing) > 0:
            existing_id = existing[0].get('id')
            return jsonify({
                'success': False,
                'error': f'Serial number {serial_number} already exists (Asset #{existing_id})',
                'field': 'serial_number',
                'existing_asset_id': existing_id
            }), 400
    except Exception as e:
        current_app.logger.error(f'Serial validation failed: {e}')
        return jsonify({'success': False, 'error': 'Failed to validate serial number', 'retry': True}), 500

    # Get next asset tag
    tag_manager = AssetTagManager(current_app.config)
    try:
        asset_tag = tag_manager.get_next_tag()
    except Exception as e:
        current_app.logger.error(f'Asset tag generation failed: {e}')
        return jsonify({'success': False, 'error': 'Asset tag sequence unavailable', 'retry': True}), 500

    # Create asset in RT
    try:
        asset_data = {
            'Name': asset_tag,
            'CF.{Serial Number}': serial_number,
            'CF.{Manufacturer}': manufacturer,
            'CF.{Model}': model
        }

        # Add optional fields
        if data.get('internal_name'):
            asset_data['Description'] = data.get('internal_name')
        if data.get('category'):
            asset_data['CF.{Category}': data.get('category')
        if data.get('funding_source'):
            asset_data['CF.{Funding Source}'] = data.get('funding_source')

        response = rt_api_request('POST', '/assets', data=asset_data, config=current_app.config)
        asset_id = response.get('id')

        # Increment sequence and log
        tag_manager.increment_sequence()
        tag_manager.log_confirmation(asset_tag, asset_id)

        current_app.logger.info(f'Asset {asset_tag} created successfully (ID: {asset_id})')

    except Exception as e:
        current_app.logger.error(f'Asset creation failed: {e}')
        return jsonify({'success': False, 'error': f'Failed to create asset in RT: {str(e)}', 'retry': True}), 500

    # Return success (label printing handled client-side)
    return jsonify({
        'success': True,
        'asset_id': asset_id,
        'asset_tag': asset_tag,
        'serial_number': serial_number,
        'label_printed': False,  # Client triggers print
        'message': f'Asset {asset_tag} created successfully'
    }), 201

@bp.route('/validate-serial', methods=['GET'])
def validate_serial():
    """Validate serial number uniqueness."""
    serial_number = request.args.get('serial_number')
    if not serial_number:
        return jsonify({'error': 'Missing required parameter: serial_number'}), 400

    try:
        query = [{'field': 'CF.{Serial Number}', 'operator': '=', 'value': serial_number}]
        existing = search_assets(query, current_app.config)

        if len(existing) > 0:
            asset = existing[0]
            return jsonify({
                'valid': False,
                'serial_number': serial_number,
                'error': 'Serial number already exists',
                'existing_asset_id': asset.get('id'),
                'existing_asset_tag': asset.get('Name')
            })

        return jsonify({'valid': True, 'serial_number': serial_number})

    except Exception as e:
        current_app.logger.error(f'Serial validation error: {e}')
        return jsonify({'error': 'Validation failed', 'retry': True}), 500

@bp.route('/preview-next-tag', methods=['GET'])
def preview_next_tag():
    """Preview the next asset tag."""
    tag_manager = AssetTagManager(current_app.config)
    try:
        next_tag = tag_manager.get_next_tag()
        sequence = tag_manager.get_current_sequence()
        return jsonify({
            'next_tag': next_tag,
            'prefix': tag_manager.prefix,
            'sequence_number': sequence
        })
    except Exception as e:
        current_app.logger.error(f'Tag preview error: {e}')
        return jsonify({'error': 'Failed to get next tag'}), 500

@bp.route('/form', methods=['GET'])
def asset_form():
    """Render the batch asset creation form."""
    return render_template('asset_create.html')
```

### Step 2: Register Blueprint

In `request_tracker_utils/__init__.py`, add the new blueprint:

```python
from request_tracker_utils.routes import label_routes, tag_routes, device_routes, student_routes, asset_routes

# ... in create_app():
app.register_blueprint(asset_routes.bp)  # Add this line
```

### Step 3: Create Template

Create `request_tracker_utils/templates/asset_create.html`:

```html
{% extends 'base.html' %} {% block title %}Batch Asset Creation{% endblock %} {%
block content %}
<div class="container py-4">
  <h1>Batch Asset Creation</h1>
  <p class="lead">
    Quickly create multiple assets with automatic tag assignment and label
    printing
  </p>

  <div class="row">
    <div class="col-md-8">
      <div class="card">
        <div class="card-header bg-primary text-white">
          <h5 class="mb-0">Asset Information</h5>
        </div>
        <div class="card-body">
          <form id="assetForm">
            <!-- Common fields (persisted) -->
            <div class="mb-3">
              <label for="manufacturer" class="form-label"
                >Manufacturer *</label
              >
              <input
                type="text"
                class="form-control"
                id="manufacturer"
                required
              />
            </div>

            <div class="mb-3">
              <label for="model" class="form-label">Model *</label>
              <input type="text" class="form-control" id="model" required />
            </div>

            <div class="mb-3">
              <label for="category" class="form-label">Category</label>
              <input type="text" class="form-control" id="category" />
            </div>

            <div class="mb-3">
              <label for="funding_source" class="form-label"
                >Funding Source</label
              >
              <input type="text" class="form-control" id="funding_source" />
            </div>

            <hr />

            <!-- Unique fields (cleared after each) -->
            <div class="mb-3">
              <label for="serial_number" class="form-label"
                >Serial Number *
                <small class="text-muted">(unique per device)</small></label
              >
              <input
                type="text"
                class="form-control"
                id="serial_number"
                required
              />
              <div class="invalid-feedback">Serial number already exists</div>
            </div>

            <div class="mb-3">
              <label for="internal_name" class="form-label"
                >Internal Name
                <small class="text-muted">(optional description)</small></label
              >
              <input type="text" class="form-control" id="internal_name" />
            </div>

            <div class="d-flex gap-2">
              <button type="submit" class="btn btn-primary">
                <i class="bi bi-plus-circle"></i> Create Asset
              </button>
              <button
                type="button"
                class="btn btn-outline-secondary"
                id="clearAllBtn"
              >
                <i class="bi bi-x-circle"></i> Clear All
              </button>
            </div>
          </form>
        </div>
      </div>

      <div
        id="successAlert"
        class="alert alert-success mt-3"
        style="display:none;"
      >
        <i class="bi bi-check-circle"></i> <span id="successMessage"></span>
        <button
          type="button"
          id="retryPrintBtn"
          class="btn btn-sm btn-outline-success ms-2"
          style="display:none;"
        >
          <i class="bi bi-printer"></i> Retry Print
        </button>
      </div>

      <div
        id="errorAlert"
        class="alert alert-danger mt-3"
        style="display:none;"
      >
        <i class="bi bi-exclamation-triangle"></i>
        <span id="errorMessage"></span>
      </div>
    </div>

    <div class="col-md-4">
      <div class="card">
        <div class="card-header bg-secondary text-white">
          <h5 class="mb-0">Next Asset Tag</h5>
        </div>
        <div class="card-body">
          <<<<<<< HEAD
          <div class="display-6" id="nextTag">W12-####</div>
          =======
          <div class="display-6" id="nextTag">W12-#####</div>
          >>>>>>> main
          <small class="text-muted">Auto-assigned on creation</small>
        </div>
      </div>

      <div class="card mt-3">
        <div class="card-header">
          <h6 class="mb-0">Tips</h6>
        </div>
        <div class="card-body">
          <ul class="small mb-0">
            <li>Common fields persist across entries</li>
            <li>Serial number cleared after each asset</li>
            <li>Labels print automatically</li>
            <li>Use Tab key for quick navigation</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="/static/js/asset_batch.js"></script>
{% endblock %}
```

### Step 4: Create JavaScript Module

Create `request_tracker_utils/static/js/asset_batch.js`:

```javascript
// Session storage key
const STORAGE_KEY = 'assetBatchForm'

// Fields that persist across submissions
const PERSISTED_FIELDS = ['manufacturer', 'model', 'category', 'funding_source']

// Fields that clear after each submission
const CLEARED_FIELDS = ['serial_number', 'internal_name']

// Load persisted form state on page load
document.addEventListener('DOMContentLoaded', function () {
  loadFormState()
  loadNextTag()

  // Set up form submission
  document.getElementById('assetForm').addEventListener('submit', handleSubmit)

  // Clear all button
  document.getElementById('clearAllBtn').addEventListener('click', clearAll)
})

function loadFormState() {
  const saved = sessionStorage.getItem(STORAGE_KEY)
  if (saved) {
    const formData = JSON.parse(saved)
    PERSISTED_FIELDS.forEach(field => {
      if (formData[field]) {
        document.getElementById(field).value = formData[field]
      }
    })
  }
}

function saveFormState() {
  const formData = {}
  PERSISTED_FIELDS.forEach(field => {
    formData[field] = document.getElementById(field).value
  })
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(formData))
}

function clearUniqueFields() {
  CLEARED_FIELDS.forEach(field => {
    document.getElementById(field).value = ''
  })
  // Focus first cleared field
  document.getElementById('serial_number').focus()
}

function clearAll() {
  sessionStorage.removeItem(STORAGE_KEY)
  document.getElementById('assetForm').reset()
  hideAlerts()
  loadNextTag()
}

async function loadNextTag() {
  try {
    const response = await fetch('/assets/preview-next-tag')
    const data = await response.json()
    document.getElementById('nextTag').textContent = data.next_tag
  } catch (error) {
    console.error('Failed to load next tag:', error)
  }
}

async function handleSubmit(event) {
  event.preventDefault()

  hideAlerts()

  // Collect form data
  const formData = {
    serial_number: document.getElementById('serial_number').value,
    internal_name: document.getElementById('internal_name').value,
    manufacturer: document.getElementById('manufacturer').value,
    model: document.getElementById('model').value,
    category: document.getElementById('category').value,
    funding_source: document.getElementById('funding_source').value
  }

  try {
    // Create asset
    const response = await fetch('/assets/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })

    const result = await response.json()

    if (result.success) {
      // Save persisted fields
      saveFormState()

      // Clear unique fields
      clearUniqueFields()

      // Update next tag preview
      loadNextTag()

      // Show success message
      showSuccess(result)

      // Trigger label printing
      printLabel(result.asset_id)
    } else {
      showError(result.error)
    }
  } catch (error) {
    showError('Failed to create asset: ' + error.message)
  }
}

function printLabel(assetId) {
  fetch(`/labels/print?asset_id=${assetId}`)
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

      // Cleanup
      setTimeout(() => iframe.remove(), 1000)
    })
    .catch(error => {
      console.error('Label printing failed:', error)
      showLabelError(assetId)
    })
}

function showSuccess(result) {
  const alert = document.getElementById('successAlert')
  const message = document.getElementById('successMessage')
  message.textContent = result.message
  alert.style.display = 'block'

  // Scroll to success message
  alert.scrollIntoView({ behavior: 'smooth', block: 'nearest' })

  // Auto-hide after 3 seconds
  setTimeout(() => {
    alert.style.display = 'none'
  }, 3000)
}

function showError(errorText) {
  const alert = document.getElementById('errorAlert')
  const message = document.getElementById('errorMessage')
  message.textContent = errorText
  alert.style.display = 'block'
}

function showLabelError(assetId) {
  const message = document.getElementById('successMessage')
  message.textContent += ' (Label printing failed)'

  const retryBtn = document.getElementById('retryPrintBtn')
  retryBtn.style.display = 'inline-block'
  retryBtn.onclick = () => printLabel(assetId)
}

function hideAlerts() {
  document.getElementById('successAlert').style.display = 'none'
  document.getElementById('errorAlert').style.display = 'none'
  document.getElementById('retryPrintBtn').style.display = 'none'
}
```

### Step 5: Update Asset Tag Manager (if needed)

Ensure `AssetTagManager` in `tag_routes.py` supports dynamic digit expansion:

```python
def get_next_tag(self):
    """Get the next asset tag with dynamic zero-padding."""
    current_number = self.get_current_sequence()
    # Calculate required digits (minimum 4)
    digit_count = max(4, len(str(current_number)))
    return f"{self.prefix}{current_number:0{digit_count}d}"
```

### Step 6: Test the Feature

1. **Start the Flask application**:

   ```bash
   python run.py
   ```

2. **Navigate to the form**:

   ```
   http://localhost:8080/assets/form
   ```

3. **Create test assets**:

   - Fill in manufacturer, model (these will persist)
   - Enter unique serial number
   - Click "Create Asset"
   - Verify print dialog opens
   - Notice common fields remain filled
   - Serial number field is cleared

4. **Test validation**:

   - Try creating asset with duplicate serial number
   - Verify error message displayed

5. **Test "Clear All"**:
   - Click "Clear All" button
   - Verify all fields empty
   - Verify sessionStorage cleared

## Integration Points

### With Existing Code

- **RT API**: Uses existing `rt_api.py` utilities
- **Asset Tags**: Uses existing `AssetTagManager` from `tag_routes.py`
- **Label Generation**: Uses existing `/labels/print` endpoint
- **Authentication**: Uses existing Flask authentication

### No Breaking Changes

All changes are additive - no existing functionality is modified.

## Deployment Checklist

- [ ] Blueprint registered in `__init__.py`
- [ ] Template created in `templates/`
- [ ] JavaScript file created in `static/js/`
- [ ] RT API credentials configured
- [ ] Asset tag sequence file accessible
- [ ] Label generation dependencies installed (reportlab, qrcode, python-barcode)
- [ ] Browser print functionality tested

## Performance Considerations

- Each asset creation: ~1-2 seconds (RT API + label generation)
- Session storage: Negligible overhead
- Print dialog: Opens immediately after asset creation

## Security Notes

- Serial number validation prevents duplicates
- Session storage isolated per browser tab
- RT authentication required for all endpoints
- Input sanitization via Flask's built-in protections

## Next Steps

After implementing basic functionality, consider:

- Add keyboard shortcuts (Ctrl+Enter to submit)
- Add serial number barcode scanner support
- Add batch statistics (X assets created this session)
- Add undo last creation option

## Troubleshooting

**Print dialog doesn't open**:

- Check browser popup blocker settings
- Verify label endpoint returns HTML

**Serial validation slow**:

- Check RT API response time
- Consider adding loading indicator

**Session storage not persisting**:

- Check browser console for errors
- Verify STORAGE_KEY is consistent

**Asset tag sequence errors**:

- Check file permissions on `asset_tag_sequence.txt`
- Verify AssetTagManager initialization

## Implementation Deviations

The following deviations from the original design were made during implementation for improved user experience:

### Label Printing (User Story 2)

**Original Design**: Use hidden iframe with window.print() to trigger browser print dialog

**Actual Implementation**: Use `window.open()` to open label in new tab/window

**Rationale**:
<<<<<<< HEAD

=======

> > > > > > > main

- Better UX: Users can preview label before printing
- More reliable: Avoids iframe sandboxing issues in modern browsers
- Easier troubleshooting: Label URL visible in browser tab

**Code Location**: `request_tracker_utils/static/js/asset_batch.js` - `printLabel()` function

### Clear All Functionality (User Story 3)

**Original Design**: POST endpoint `/assets/batch/clear-form` for server-side clearing

**Actual Implementation**: Client-side only clearing via `sessionStorage.removeItem()`

**Rationale**:
<<<<<<< HEAD

=======

> > > > > > > main

- Simpler architecture: No server round-trip needed
- Better performance: Instant clearing
- Sufficient for use case: sessionStorage is browser-local

**Code Location**: `request_tracker_utils/static/js/asset_batch.js` - `clearAll()` function

### TEST Mode Feature

**Additional Feature**: Added TEST mode toggle to switch between W12 and TEST prefixes

**Implementation**:
<<<<<<< HEAD

=======

> > > > > > > main

- Separate sequence files for each prefix (`asset_tag_sequence_test.txt`, `asset_tag_sequence_w12.txt`)
- Toggle switch in asset creation form
- Independent sequence counters
- Admin page enhancements for managing both sequences

**Code Locations**:
<<<<<<< HEAD

=======

> > > > > > > main

- `request_tracker_utils/routes/tag_routes.py` - `AssetTagManager` accepts `prefix` parameter
- `request_tracker_utils/templates/asset_create.html` - TEST mode toggle switch
- `request_tracker_utils/static/js/asset_batch.js` - Prefix parameter in API calls
- `request_tracker_utils/templates/asset_tag_admin.html` - Dual sequence management UI

### Asset Links in Success Messages

**Additional Feature**: Added clickable links to created assets in success messages

**Implementation**:
<<<<<<< HEAD

=======

> > > > > > > main

- Success message includes link to RT asset display page
- Opens in new tab with external link icon
- Provides quick access to verify created asset

**Code Location**: `request_tracker_utils/static/js/asset_batch.js` - `showSuccess()` function

### Breadcrumb Navigation

**Additional Feature**: Added breadcrumb navigation to asset creation form

**Implementation**:
<<<<<<< HEAD

=======

> > > > > > > main

- Standard Bootstrap breadcrumb component
- Links back to home page
- Consistent with other pages in application

**Code Location**: `request_tracker_utils/templates/asset_create.html`

### Home Page Integration

**Additional Feature**: Added batch asset creation link to home page

**Implementation**:
<<<<<<< HEAD

=======

> > > > > > > main

- Prominent link at top of Web Interfaces section
- Descriptive subtitle
- Plus-circle icon for visual consistency

**Code Location**: `request_tracker_utils/templates/index.html`

## Support

For issues or questions, refer to:

- Feature spec: `specs/001-i-need-to/spec.md`
- API contracts: `specs/001-i-need-to/contracts/api-contract.md`
- Data model: `specs/001-i-need-to/data-model.md`
