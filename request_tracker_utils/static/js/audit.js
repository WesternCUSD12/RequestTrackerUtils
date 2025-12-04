/**
 * Client-side JavaScript for student device audit functionality
 * Handles CSV upload, student filtering, and audit verification
 */

// Pending duplicate confirmation data
let pendingUploadData = null;

/**
 * Initialize event listeners when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function () {
    // CSV Upload Form
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUploadSubmit);
    }

    // Duplicate confirmation buttons
    const confirmBtn = document.getElementById('confirmDuplicates');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', confirmDuplicateUpload);
    }

    const cancelBtn = document.getElementById('cancelUpload');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelUpload);
    }

    // Student list filtering
    const applyFilterBtn = document.getElementById('applyFilter');
    if (applyFilterBtn) {
        applyFilterBtn.addEventListener('click', filterStudents);
    }

    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // Filter on Enter key
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                filterStudents();
            }
        });
    }

    // Load students if we're viewing a session
    if (typeof SESSION_ID !== 'undefined' && SESSION_ID) {
        loadStudents();
    }
});

/**
 * Handle CSV upload form submission
 * @param {Event} e - Form submit event
 */
function handleUploadSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const uploadBtn = document.getElementById('uploadBtn');
    const spinner = document.getElementById('uploadSpinner');
    const errorDiv = document.getElementById('uploadError');
    const successDiv = document.getElementById('uploadSuccess');

    // Clear previous messages
    errorDiv.classList.add('d-none');
    successDiv.classList.add('d-none');

    // Show loading state
    uploadBtn.disabled = true;
    spinner.classList.remove('d-none');

    fetch('/devices/audit/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => {
            if (!response.ok && response.status !== 200) {
                return response.json().then(data => {
                    throw new Error(data.error || 'Upload failed');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.require_confirmation) {
                // Show duplicate warning
                showDuplicateWarning(data);
                pendingUploadData = formData;
            } else if (data.success) {
                // Redirect to session view
                successDiv.textContent = `Upload successful! ${data.student_count} students added.`;
                successDiv.classList.remove('d-none');

                setTimeout(() => {
                    window.location.href = `/devices/audit/session/${data.session_id}`;
                }, 1500);
            } else if (data.error) {
                showError(data.error, data.details);
            }
        })
        .catch(error => {
            showError('Upload failed: ' + error.message);
        })
        .finally(() => {
            uploadBtn.disabled = false;
            spinner.classList.add('d-none');
        });
}

/**
 * Show duplicate student warning
 * @param {Object} data - Response data with duplicates
 */
function showDuplicateWarning(data) {
    const warningDiv = document.getElementById('duplicateWarning');
    const duplicateList = document.getElementById('duplicateList');

    duplicateList.innerHTML = '';
    data.duplicates.forEach(dup => {
        const li = document.createElement('li');
        li.textContent = `${dup.name} - Grade ${dup.grade} (${dup.advisor})`;
        duplicateList.appendChild(li);
    });

    warningDiv.classList.remove('d-none');
}

/**
 * Confirm upload with duplicates
 */
function confirmDuplicateUpload() {
    // This would require backend support for forced upload
    // For now, show error asking user to clean CSV
    showError('Please remove duplicate entries from your CSV and try again.');
    cancelUpload();
}

/**
 * Cancel upload and hide duplicate warning
 */
function cancelUpload() {
    const warningDiv = document.getElementById('duplicateWarning');
    warningDiv.classList.add('d-none');
    pendingUploadData = null;
}

/**
 * Show error message
 * @param {string} message - Error message
 * @param {Array} details - Optional error details
 */
function showError(message, details = null) {
    const errorDiv = document.getElementById('uploadError');
    let errorHtml = `<strong>Error:</strong> ${message}`;

    if (details && details.length > 0) {
        errorHtml += '<ul>';
        details.forEach(detail => {
            errorHtml += `<li>${detail}</li>`;
        });
        errorHtml += '</ul>';
    }

    errorDiv.innerHTML = errorHtml;
    errorDiv.classList.remove('d-none');
}

/**
 * Load students for current session
 */
function loadStudents() {
    const tableBody = document.getElementById('studentTableBody');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const noStudentsDiv = document.getElementById('noStudents');

    console.log('[loadStudents] Starting to load students...');
    console.log('[loadStudents] tableBody:', tableBody);
    console.log('[loadStudents] SESSION_ID:', SESSION_ID);

    if (!tableBody || !SESSION_ID) {
        console.error('[loadStudents] Missing required elements. tableBody:', !!tableBody, 'SESSION_ID:', SESSION_ID);
        return;
    }

    // Show loading spinner
    loadingSpinner.classList.remove('d-none');
    tableBody.innerHTML = '';
    noStudentsDiv.classList.add('d-none');

    // Get filter values
    const searchQuery = document.getElementById('searchInput')?.value || '';
    const auditedFilter = document.getElementById('auditedFilter')?.value || 'false';

    console.log('[loadStudents] Filters - search:', searchQuery, 'audited:', auditedFilter);

    // Build query params
    let queryParams = new URLSearchParams();
    if (searchQuery) queryParams.append('search', searchQuery);
    if (auditedFilter !== 'all') queryParams.append('audited', auditedFilter);

    const url = `/devices/audit/session/${SESSION_ID}/students?${queryParams}`;
    console.log('[loadStudents] Fetching from URL:', url);

    fetch(url)
        .then(response => {
            console.log('[loadStudents] Response status:', response.status, response.statusText);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('[loadStudents] Received data:', data);
            loadingSpinner.classList.add('d-none');

            if (!data.students || data.students.length === 0) {
                console.log('[loadStudents] No students found in response');
                noStudentsDiv.classList.remove('d-none');
                return;
            }

            console.log('[loadStudents] Populating table with', data.students.length, 'students');

            // Populate table
            data.students.forEach((student, index) => {
                const row = document.createElement('tr');

                const statusBadge = student.audited
                    ? '<span class="badge bg-success">Audited</span>'
                    : '<span class="badge bg-warning">Pending</span>';

                const actionBtn = student.audited
                    ? `<span class="text-muted">Completed by ${student.auditor_name || 'Unknown'}</span>`
                    : `<a href="/devices/audit/student/${student.id}" class="btn btn-sm btn-primary">Audit</a>`;

                row.innerHTML = `
                    <td>${student.name}</td>
                    <td>${student.grade}</td>
                    <td>${student.advisor}</td>
                    <td>${statusBadge}</td>
                    <td>${actionBtn}</td>
                `;

                tableBody.appendChild(row);
            });

            console.log('[loadStudents] Table populated successfully');
        })
        .catch(error => {
            console.error('[loadStudents] Error:', error);
            loadingSpinner.classList.add('d-none');
            noStudentsDiv.textContent = 'Error loading students: ' + error.message;
            noStudentsDiv.classList.remove('d-none');
        });
}

/**
 * Filter students based on search and filter criteria
 */
function filterStudents() {
    loadStudents();
}

/**
 * Verify student device audit (placeholder for T034)
 */
function verifyStudent() {
    // Will be implemented in Phase 4
    console.log('Verify student - to be implemented');
}

/**
 * Apply notes filter (placeholder for T044)
 */
function applyNotesFilter() {
    // Will be implemented for User Story 4
    console.log('Apply notes filter - to be implemented');
}

/**
 * Re-audit student (placeholder for T052)
 */
function reauditStudent(studentId) {
    // Will be implemented in Phase 6
    console.log('Re-audit student - to be implemented');
}

