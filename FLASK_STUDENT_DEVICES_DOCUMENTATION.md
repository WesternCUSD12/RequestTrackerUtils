# Flask Student Device Check-in Page - Complete Documentation

**Status**: Reference documentation for 007 audit session page redesign  
**Source**: 004-student-device-audit branch - `/students/student-devices` endpoint  
**Template**: `request_tracker_utils/templates/student_devices.html` (1864 lines)  
**Date Captured**: December 8, 2025

---

## Overview

The Flask `/students/student-devices` page is a professional dashboard for tracking student device check-in status. This document captures its complete visual design and functionality for reference when enhancing the 007 Django audit session detail page.

---

## Page Layout & Components

### 1. Page Header

- **Title**: "Student Device Tracking"
- **Subtitle**: "Track device check-ins by grade for the [YEAR] school year."
- **Breadcrumb**: Home > Devices > Student Device List
- **Visual**: Simple, professional header with clear hierarchy

---

### 2. Dashboard Summary Cards (4-Column Grid)

Located at the top of the page, these cards provide quick metrics overview.

#### Card 1: Total Students

- **Color**: Primary Blue (`bg-primary text-white`)
- **Title**: "Total Students"
- **Value**: Large display-4 font size (very prominent)
- **Subtitle**: "All students" (small text)
- **Data Binding**: `{{ stats.total_students }}`

#### Card 2: Checked In

- **Color**: Success Green (`bg-success text-white`)
- **Title**: "Checked In"
- **Value**: Large display-4 font size
- **Subtitle**: "All students"
- **Data Binding**: `{{ stats.checked_in }}`

#### Card 3: Pending

- **Color**: Warning Yellow (`bg-warning text-dark`)
- **Title**: "Pending"
- **Value**: Large display-4 font size
- **Subtitle**: "All students"
- **Data Binding**: `{{ stats.not_checked_in }}`

#### Card 4: Completion Rate

- **Color**: Info Cyan (`bg-info text-white`)
- **Title**: "Completion Rate"
- **Value**: Large display-4 with percentage format (e.g., "45.3%")
- **Subtitle**: "All students"
- **Data Binding**: `{{ "%.1f"|format(stats.completion_rate) }}%`

**Card Styling**:

- Bootstrap card class: `card`
- Height: `h-100` (full height in row)
- Responsive: 3 columns on desktop (col-md-3)
- Text color: White on colored backgrounds (good contrast)
- Padding: Standard card-body padding (1.5rem)

---

### 3. Filter Students Section

#### Visual Design

- **Card**: Standard Bootstrap card
- **Header**: Blue background (`bg-primary text-white`)
- **Title**: "Filter Students" (h5 heading)
- **Layout**: Form with 3 columns (responsive grid)

#### Filter Components

**Column 1: Grade Levels (50% width)**

- **Type**: Checkboxes (multiple select)
- **Grades**: 6, 7, 8, 9, 10, 11, 12
- **Quick Actions**: "Select All", "Clear" buttons
- **JavaScript Class**: `grade-filter`

**Column 2: Check-in Status (25% width)**

- **Type**: Dropdown/Select
- **ID**: `statusFilter`
- **Options**: "All Statuses", "Checked In", "Not Checked In"
- **Styling**: `form-select` Bootstrap class

**Column 3: Search Students (25% width)**

- **Type**: Text input with clear button
- **ID**: `searchInput`
- **Placeholder**: "Name or ID..."
- **Clear Button**: `#clearSearch` with X icon

---

### 4. Student List Table

Location: Below filters in a card container

**8 Columns**:

1. **ID** - Student identifier
2. **First Name** - Student's first name
3. **Last Name** - Student's last name
4. **Grade** - Grade level (6-12)
5. **Check-in Status** - Dynamic badge (color-coded)
6. **Device Info** - Asset tag + device type (or "-" if not checked in)
7. **Check-in Date** - Formatted date or "-"
8. **Actions** - Conditional buttons based on status

#### Status Badges

**Checked In (Success)**
\`\`\`html
<span class="badge bg-success">Checked In</span>
\`\`\`

- Color: Green (#198754)

**Not Checked In (Warning)**
\`\`\`html
<span class="badge bg-warning text-dark">Not Checked In</span>
\`\`\`

- Color: Yellow (#ffc107)

---

## JavaScript Functionality

### Filter Functionality (Must Replicate)

#### Grade Filter

- **Selector**: `.grade-filter` checkboxes
- **Event**: Change event listener
- **Action**: Triggers table update with selected grades

#### Status Filter

- **Selector**: `#statusFilter` dropdown
- **Values**: `all`, `checked_in`, `not_checked_in`
- **Event**: Change event listener

#### Search Filter

- **Selector**: `#searchInput` text input
- **Event**: Input/change event listener
- **Search Fields**: Student ID, First Name, Last Name
- **Case Insensitive**: Yes

#### Combined Filtering Logic

- **AND operation**: Only students matching ALL selected filters are shown
- **No Results**: Shows no-results message when 0 rows match
- **Count Update**: Updates student count badge dynamically

### Required JavaScript Functions

- `filterStudents()` - Main filter function
- `updateTableVisibility()` - Show/hide rows based on filters
- `updateStudentCount()` - Update count badge
- `selectAllGrades()` - Check all grade checkboxes
- `clearAllGrades()` - Uncheck all grade checkboxes
- `clearSearch()` - Clear search input
- `getMatchingRows()` - Get visible rows after filters applied

---

## Key Features to Replicate in 007

1. ✅ **4-Column Summary Cards**

   - Colorful backgrounds (blue, green, yellow, cyan)
   - Large font sizes (display-4)
   - Prominent metrics

2. ✅ **Filter Section**

   - Grade level multi-select with quick buttons
   - Status dropdown (All / Checked In / Pending)
   - Search box with clear button
   - Combined filtering (AND logic)
   - Real-time table updates

3. ✅ **Student Table**

   - 8 columns with all information
   - Color-coded status badges (green/yellow)
   - Conditional action buttons per row
   - Student count display

4. ✅ **Loading & Empty States**
   - Loading spinner
   - "No results" message
   - Dynamic count badge

---

## Implementation Notes for 007

### Filter Form HTML Structure

\`\`\`html

<form id="filterForm" class="row g-3">
  <div class="col-md-6">
    <!-- Grade checkboxes -->
  </div>
  <div class="col-md-3">
    <!-- Status dropdown -->
  </div>
  <div class="col-md-3">
    <!-- Search input -->
  </div>
</form>
\`\`\`

### Filter Logic

The filter student function must:

1. Listen to changes on `.grade-filter` checkboxes
2. Listen to changes on `#statusFilter` dropdown
3. Listen to input on `#searchInput` text field
4. For each table row, check if it matches ALL active filters
5. Show/hide rows based on filter match
6. Update count badge with visible row count
7. Show/hide empty state message

---

## Color Reference

| Component            | Color  | Hex     | Bootstrap Class |
| -------------------- | ------ | ------- | --------------- |
| Total Students Card  | Blue   | #0d6efd | bg-primary      |
| Checked In Card      | Green  | #198754 | bg-success      |
| Pending Card         | Yellow | #ffc107 | bg-warning      |
| Completion Card      | Cyan   | #0dcaf0 | bg-info         |
| Checked In Badge     | Green  | #198754 | bg-success      |
| Not Checked In Badge | Yellow | #ffc107 | bg-warning      |

---

## Implementation Guide for 007 Audit Session Page

### 1. Filter Section HTML (Replace current filters)

```html
<div class="card mb-4">
  <div class="card-header bg-primary text-white">
    <h5 class="mb-0">Filter Students</h5>
  </div>
  <div class="card-body">
    <form id="filterForm" class="row g-3">
      <!-- Grade Levels Column (50%) -->
      <div class="col-md-6">
        <label class="form-label">Grade Levels</label>
        <div id="gradeCheckboxes" class="d-flex flex-wrap gap-2">
          <div class="form-check form-check-inline">
            <input
              class="form-check-input grade-filter"
              type="checkbox"
              value="9"
              id="grade9"
            />
            <label class="form-check-label" for="grade9">Grade 9</label>
          </div>
          <div class="form-check form-check-inline">
            <input
              class="form-check-input grade-filter"
              type="checkbox"
              value="10"
              id="grade10"
            />
            <label class="form-check-label" for="grade10">Grade 10</label>
          </div>
          <div class="form-check form-check-inline">
            <input
              class="form-check-input grade-filter"
              type="checkbox"
              value="11"
              id="grade11"
            />
            <label class="form-check-label" for="grade11">Grade 11</label>
          </div>
          <div class="form-check form-check-inline">
            <input
              class="form-check-input grade-filter"
              type="checkbox"
              value="12"
              id="grade12"
            />
            <label class="form-check-label" for="grade12">Grade 12</label>
          </div>
          <div class="ms-3">
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              id="selectAllGrades"
            >
              Select All
            </button>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              id="clearAllGrades"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      <!-- Status Dropdown Column (25%) -->
      <div class="col-md-3">
        <label for="statusFilter" class="form-label">Audit Status</label>
        <select class="form-select" id="statusFilter">
          <option value="all" selected>All Statuses</option>
          <option value="audited">Audited</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <!-- Search Column (25%) -->
      <div class="col-md-3">
        <label for="searchInput" class="form-label">Search Students</label>
        <div class="input-group">
          <input
            type="text"
            class="form-control"
            id="searchInput"
            placeholder="Name or ID..."
          />
          <button
            class="btn btn-outline-secondary"
            type="button"
            id="clearSearch"
          >
            <i class="bi bi-x"></i>
          </button>
        </div>
      </div>
    </form>
  </div>
</div>
```

### 2. JavaScript Filter Implementation

Add this JavaScript to your audit session detail template:

```javascript
<script>
// Listen to filter changes
document.querySelectorAll('.grade-filter').forEach(checkbox => {
  checkbox.addEventListener('change', filterStudents);
});
document.getElementById('statusFilter').addEventListener('change', filterStudents);
document.getElementById('searchInput').addEventListener('input', filterStudents);

// Quick select buttons
document.getElementById('selectAllGrades').addEventListener('click', selectAllGrades);
document.getElementById('clearAllGrades').addEventListener('click', clearAllGrades);
document.getElementById('clearSearch').addEventListener('click', clearSearch);

function filterStudents() {
  // Get selected values
  const selectedGrades = Array.from(document.querySelectorAll('.grade-filter:checked'))
    .map(cb => cb.value);
  const selectedStatus = document.getElementById('statusFilter').value;
  const searchText = document.getElementById('searchInput').value.toLowerCase();

  // Filter table rows
  let visibleCount = 0;
  document.querySelectorAll('#studentTable tbody tr').forEach(row => {
    const grade = row.dataset.grade;
    const status = row.dataset.status;
    const name = row.textContent.toLowerCase();

    const gradeMatch = selectedGrades.length === 0 || selectedGrades.includes(grade);
    const statusMatch = selectedStatus === 'all' || selectedStatus === status;
    const searchMatch = searchText === '' || name.includes(searchText);

    if (gradeMatch && statusMatch && searchMatch) {
      row.style.display = '';
      visibleCount++;
    } else {
      row.style.display = 'none';
    }
  });

  // Update count
  const countBadge = document.querySelector('[id*="student-count"], .student-count, [class*="count"]');
  if (countBadge) {
    countBadge.textContent = `${visibleCount} students`;
  }

  // Show/hide empty state
  const noResults = document.getElementById('noResultsMessage');
  if (noResults) {
    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
  }
}

function selectAllGrades() {
  document.querySelectorAll('.grade-filter').forEach(cb => cb.checked = true);
  filterStudents();
}

function clearAllGrades() {
  document.querySelectorAll('.grade-filter').forEach(cb => cb.checked = false);
  filterStudents();
}

function clearSearch() {
  document.getElementById('searchInput').value = '';
  filterStudents();
}
</script>
```

### 3. Table Row Data Attributes

Ensure your table rows have data attributes for filtering:

```html
<tr data-grade="10" data-status="pending">
  <!-- Row content -->
</tr>
```

The `data-grade` should match grade values, and `data-status` should be either "audited" or "pending".

### 4. Empty State HTML

Add this for when no results match filters:

```html
<div id="noResultsMessage" class="alert alert-info m-3" style="display: none;">
  <i class="bi bi-info-circle me-2"></i>
  No students match your current filters.
</div>
```

---

**Last Updated**: December 8, 2025  
**Reference Branch**: 004-student-device-audit  
**Target Branch**: 007-unified-student-data
