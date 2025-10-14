/**
 * Asset Batch Creation - Form State Management
 * 
 * Handles browser sessionStorage persistence for common fields,
 * form submission, validation, and catalog dropdown loading.
 */

// Session storage configuration
const STORAGE_KEY = 'assetBatchForm';

// Fields that persist across submissions (common asset attributes)
const PERSISTED_FIELDS = [
  'manufacturer',
  'model',
  'category',
  'funding_source'
];

// Fields that clear after each successful submission (unique identifiers)
const CLEARED_FIELDS = [
  'serial_number'
  // internal_name is auto-generated, not user input
];

// Load catalog options from RT for dropdowns
async function loadCatalogOptions() {
  try {
    // Load catalogs
    const catalogResponse = await fetch('/assets/catalogs');
    if (!catalogResponse.ok) {
      throw new Error('Failed to load catalogs');
    }
    const catalogData = await catalogResponse.json();

    // Populate catalog dropdown
    const catalogSelect = document.getElementById('catalog');
    catalogSelect.innerHTML = '<option value="">-- Select Catalog --</option>';
    catalogData.catalogs.forEach(cat => {
      const option = document.createElement('option');
      option.value = cat;
      option.textContent = cat;
      catalogSelect.appendChild(option);
    });

    // Load manufacturer options
    const response = await fetch('/assets/catalog-options');
    if (!response.ok) {
      throw new Error('Failed to load catalog options');
    }

    const data = await response.json();

    // Populate manufacturer dropdown (only field with RT predefined values)
    const manufacturerSelect = document.getElementById('manufacturer');
    manufacturerSelect.innerHTML = '<option value="">-- Select Manufacturer --</option>';
    data.manufacturers.forEach(mfr => {
      const option = document.createElement('option');
      option.value = mfr;
      option.textContent = mfr;
      manufacturerSelect.appendChild(option);
    });

    console.log('Catalog options loaded:', {
      catalogs: catalogData.catalogs.length,
      manufacturers: data.manufacturers.length
    });

    // After loading options, restore any saved form state
    loadFormState();

  } catch (error) {
    console.error('Error loading catalog options:', error);
    showError('Failed to load catalog options from Request Tracker. Please refresh the page.');
  }
}

// T015: SessionStorage persistence logic
function loadFormState() {
  const saved = sessionStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const formData = JSON.parse(saved);
      PERSISTED_FIELDS.forEach(field => {
        if (formData[field]) {
          const element = document.getElementById(field);
          if (element) {
            element.value = formData[field];
          }
        }
      });
    } catch (e) {
      console.error('Failed to load form state:', e);
    }
  }
}

function saveFormState() {
  const formData = {};
  PERSISTED_FIELDS.forEach(field => {
    const element = document.getElementById(field);
    if (element) {
      formData[field] = element.value;
    }
  });
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(formData));
}

// T016: Clear unique fields after successful creation
function clearUniqueFields() {
  CLEARED_FIELDS.forEach(field => {
    const element = document.getElementById(field);
    if (element) {
      element.value = '';
    }
  });
  // Focus first unique field for next entry
  const firstField = document.getElementById(CLEARED_FIELDS[0]);
  if (firstField) {
    firstField.focus();
  }
}

// T017: Load and display next asset tag
async function loadNextTag() {
  try {
    const testModeToggle = document.getElementById('testModeToggle');
    const isTestMode = testModeToggle && testModeToggle.checked;
    const prefix = isTestMode ? 'TEST' : 'W12';

    const response = await fetch(`/assets/preview-next-tag?prefix=${prefix}`);
    if (response.ok) {
      const data = await response.json();
      const tagElement = document.getElementById('nextTag');
      if (tagElement && data.next_tag) {
        tagElement.textContent = data.next_tag;
      }
    }
  } catch (error) {
    console.error('Failed to load next tag:', error);
  }
}

// Load and display next internal name
async function loadInternalName() {
  try {
    const internalNameField = document.getElementById('internal_name');
    if (internalNameField) {
      internalNameField.value = 'Generating...';
      internalNameField.classList.add('text-muted');
    }

    const response = await fetch('/assets/preview-internal-name');
    if (response.ok) {
      const data = await response.json();
      if (internalNameField && data.internal_name) {
        internalNameField.value = data.internal_name;
        internalNameField.classList.remove('text-muted');
      }
    } else {
      if (internalNameField) {
        internalNameField.value = 'Error generating name';
      }
    }
  } catch (error) {
    console.error('Failed to load internal name:', error);
    const internalNameField = document.getElementById('internal_name');
    if (internalNameField) {
      internalNameField.value = 'Error loading name';
    }
  }
}

// T018: Success/error alert display with label printing
function showSuccess(result) {
  hideAlerts();
  const successAlert = document.getElementById('successAlert');
  const successMessage = document.getElementById('successMessage');
  const retryPrintBtn = document.getElementById('retryPrintBtn');

  if (successAlert && successMessage) {
    // Build success message with asset link
    const assetName = result.internal_name
      ? `${result.asset_tag} - "${result.internal_name}"`
      : result.asset_tag;

    // Get RT URL from container data attribute (set in template)
    const container = document.querySelector('.container[data-rt-url]');
    const rtUrl = container ? container.dataset.rtUrl : 'https://tickets.wc-12.com';
    const assetLink = `${rtUrl}/Asset/Display.html?id=${result.asset_id}`;

    // Create message with link
    successMessage.innerHTML = `
      Asset created successfully! 
      <a href="${assetLink}" target="_blank" class="alert-link">
        ${assetName} <i class="bi bi-box-arrow-up-right"></i>
      </a>
    `;
    successAlert.style.display = 'block';

    // Store label URL for retry button
    if (result.label_url && retryPrintBtn) {
      retryPrintBtn.style.display = 'inline-block';
      retryPrintBtn.onclick = () => printLabel(result.label_url);
    }

    // Automatically open label in new window/tab
    if (result.label_url) {
      printLabel(result.label_url);
    }

    // Auto-hide after 8 seconds (increased to read the name)
    setTimeout(() => {
      successAlert.style.display = 'none';
    }, 8000);
  }
}

// Print/open label in new window
function printLabel(labelUrl) {
  try {
    // Open label in new window/tab
    const labelWindow = window.open(labelUrl, '_blank');

    if (!labelWindow) {
      // Popup was blocked - show message
      showError('Pop-up blocked. Please allow pop-ups to print labels automatically.');
    } else {
      console.log('Label opened:', labelUrl);
    }
  } catch (error) {
    console.error('Error opening label:', error);
    showError('Failed to open label. Please try printing manually.');
  }
}

function showError(errorText) {
  hideAlerts();
  const errorAlert = document.getElementById('errorAlert');
  if (errorAlert) {
    errorAlert.textContent = `✗ Error: ${errorText}`;
    errorAlert.style.display = 'block';
  }
}

function hideAlerts() {
  const successAlert = document.getElementById('successAlert');
  const errorAlert = document.getElementById('errorAlert');
  if (successAlert) successAlert.style.display = 'none';
  if (errorAlert) errorAlert.style.display = 'none';
}

// T027: Clear All functionality
function clearAll() {
  // Clear sessionStorage
  sessionStorage.removeItem(STORAGE_KEY);

  // Reset all form fields
  const form = document.getElementById('assetForm');
  if (form) {
    form.reset();
  }

  // Hide alerts
  hideAlerts();

  // Reload previews
  loadNextTag();
  loadInternalName();


  // Show brief confirmation
  const successAlert = document.getElementById('successAlert');
  const successMessage = document.getElementById('successMessage');
  if (successAlert && successMessage) {
    successMessage.textContent = 'Form cleared successfully';
    successAlert.style.display = 'block';

    // Auto-hide after 2 seconds
    setTimeout(() => {
      successAlert.style.display = 'none';
    }, 2000);
  }
}

// T033: Show/hide loading indicator
function setLoading(isLoading) {
  const submitBtn = document.getElementById('submitBtn');
  const submitBtnText = document.getElementById('submitBtnText');
  const submitBtnSpinner = document.getElementById('submitBtnSpinner');

  if (submitBtn) {
    submitBtn.disabled = isLoading;
  }
  if (submitBtnText) {
    submitBtnText.style.display = isLoading ? 'none' : 'inline';
  }
  if (submitBtnSpinner) {
    submitBtnSpinner.style.display = isLoading ? 'inline-block' : 'none';
  }
}

// T037: Client-side validation
function validateForm(data) {
  // Required fields
  if (!data.serial_number || !data.serial_number.trim()) {
    return 'Serial number is required';
  }
  if (!data.manufacturer || !data.manufacturer.trim()) {
    return 'Manufacturer is required';
  }
  if (!data.model || !data.model.trim()) {
    return 'Model is required';
  }
  if (!data.catalog || !data.catalog.trim()) {
    return 'Catalog is required';
  }

  // Serial number format (alphanumeric and hyphens only)
  const serialPattern = /^[A-Za-z0-9-]+$/;
  if (!serialPattern.test(data.serial_number)) {
    return 'Serial number can only contain letters, numbers, and hyphens';
  }

  return null; // Valid
}

// T014: Form submission handler
async function handleSubmit(event) {
  event.preventDefault();
  hideAlerts();

  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());


  // T037: Validate before submission
  const validationError = validateForm(data);
  if (validationError) {
    showError(validationError);
    return;
  }

  // Include test mode prefix if enabled
  const testModeToggle = document.getElementById('testModeToggle');
  if (testModeToggle && testModeToggle.checked) {
    data.prefix = 'TEST';
  } else {
    data.prefix = 'W12';
  }

  setLoading(true);

  try {
    const response = await fetch('/assets/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok) {
      // Success path (FR-002, FR-007)
      saveFormState();           // Persist common fields
      clearUniqueFields();       // Clear serial_number
      loadNextTag();             // Update next tag preview
      loadInternalName();        // Generate new internal name for next asset
      showSuccess(result);       // Show success message
    } else {
      // Error path (FR-009: preserve form data on error)
      showError(result.error || 'Failed to create asset');
    }
  } catch (error) {
    console.error('Submit error:', error);
    showError('Network error. Please try again.');
  } finally {
    setLoading(false);
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
  // Load catalog options first (populates dropdowns and restores state)
  loadCatalogOptions();

  // Load next asset tag preview
  loadNextTag();

  // Load initial internal name
  loadInternalName();

  // Wire up form submission
  const form = document.getElementById('assetForm');
  if (form) {
    form.addEventListener('submit', handleSubmit);
  }

  // T028: Wire up Clear All button
  const clearAllBtn = document.getElementById('clearAllBtn');
  if (clearAllBtn) {
    clearAllBtn.addEventListener('click', clearAll);
  }

  // Wire up Test Mode toggle
  const testModeToggle = document.getElementById('testModeToggle');
  if (testModeToggle) {
    testModeToggle.addEventListener('change', loadNextTag);
  }

  // Auto-select label size based on category
  const categoryField = document.getElementById('category');
  const labelSizeSmall = document.getElementById('label_size_small');
  const labelSizeLarge = document.getElementById('label_size_large');

  if (categoryField && labelSizeSmall && labelSizeLarge) {
    categoryField.addEventListener('input', function () {
      const category = this.value.toLowerCase().trim();

      // Auto-select small label for chargers, large for everything else
      if (category === 'charger') {
        labelSizeSmall.checked = true;
        console.log('Auto-selected small label for charger');
      } else if (category !== '') {
        labelSizeLarge.checked = true;
        console.log('Auto-selected large label for', category);
      }
    });
  }
});
