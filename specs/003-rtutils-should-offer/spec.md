```markdown
# Feature Specification: Small-format printable asset label (1.1" x 3.5")

**Feature Branch**: `003-rtutils-should-offer`  
**Created**: 2025-10-14  
**Status**: Draft  
**Input**: User description: "rtutils should offer a 1.1\"x3.5\" (29mm x 90.3mm) label in addition to the current label size. The qr code and bar code should be adjusted to fit in the small space. The serial number should be hidden. Spacing and font size can be reduced. The route at labels/print should offer a simple toggle for the full size or smaller label. The default for chargers is the small label, everything else gets the large label."

## Clarifications

### Session 2025-10-14

- Q: What should the QR code and barcode contain? → A: Full asset tracking URL (e.g., https://rt.domain/asset/12345), same as large label
- Q: Where should asset names be truncated on the small label? → A: Fit-to-width (dynamic based on font/space available)
- Q: Should the label size toggle choice persist within a user session? → A: No, always reset to default based on asset type
- Q: What accessibility level is required for the label size toggle? → A: No specific compliance requirement (use HTML best practices)
- Q: How should the system handle cases where generated codes are unscannable? → A: Show warning in preview, allow print anyway (user decides)

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Quick single-label print (Priority: P1)

As a school technician preparing a charger for use, I want to print a compact 1.1"x3.5" label from the existing `labels/print` page so the label fits the charger housing and scans correctly.

**Why this priority**: Chargers are frequently labeled and physically constrained; offering a smaller label reduces waste and improves fit for this high-volume, high-impact device type.

**Independent Test**: Load an asset of type Charger, open `labels/print?id=<id>`, verify the UI shows the label-size toggle set to "Small" by default, preview the small label, and print to a known label printer or export as a print-ready PDF at the specified dimensions. Confirm QR and barcode are visible and scannable with a phone app.

**Acceptance Scenarios**:

1. **Given** an asset of type Charger, **When** the technician opens `labels/print` for that asset, **Then** the small label option is selected by default and the preview shows a 1.1"x3.5" layout without the serial number.
2. **Given** an asset of type Charger, **When** the technician toggles to "Small" and prints, **Then** the output file/printout dimensions match 1.1" x 3.5" (29mm x 90.3mm) within printer margins and the QR code and barcode are present and legible.

---

### User Story 2 - Full-size label for other assets (Priority: P1)

As a technician printing a Chromebook or other device, I want the existing full-size label to remain the default so that larger devices retain the same readable layout and include the serial number.

**Why this priority**: Preserve the current behavior for the majority of asset types and avoid disrupting existing workflows.

**Independent Test**: Open `labels/print` for a non-charger asset and confirm the toggle default is "Large". Print or export a label and verify serial number appears and layout matches the existing full-size label template.

**Acceptance Scenarios**:

1. **Given** an asset that is not a Charger, **When** `labels/print` is opened, **Then** the Large label is selected by default and the preview includes the serial number.

---

### User Story 3 - Manual override and batch printing (Priority: P2)

As a technician printing labels for a mixed batch of assets, I want to choose the label size per item (via the toggle) so I can override defaults when necessary and produce consistent output for batches.

**Why this priority**: Enables flexibility for mixed-device workflows and reduces rework.

**Independent Test**: On the batch-print UI or in the `labels/print` loop, toggle the label size for a specific item before printing; confirm the printed label for that item uses the chosen size and that other items respect their defaults unless changed.

**Acceptance Scenarios**:

1. **Given** a batch of assets including chargers and laptops, **When** the technician selects batch-print and does not change per-item toggles, **Then** chargers are printed with the small label and other devices with the large label.
2. **Given** a batch member with a manual override set to Large, **When** printed, **Then** that item prints the Large label even if it is a Charger.

---

### Edge Cases

- Printer hardware margins make 1.1"x3.5" unprintable — system should provide a PDF export and display a guidance/warning about required printable area.
- Asset names or metadata longer than small label capacity — apply dynamic fit-to-width truncation with ellipsis and show a preview warning indicating truncation occurred.
- If barcode/QR density required to encode data cannot be scanned at small sizes, show warning in preview mode but allow user to proceed with printing (user makes final decision whether to print small label or switch to large).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Provide a new small label template sized 1.1" x 3.5" (29mm x 90.3mm) in addition to the existing full-size label.
- **FR-002**: The `labels/print` route and UI MUST present a toggle labeled "Large / Small" on the single-print page and per-item toggles in batch-print flows; toggle MUST reset to asset-type-based default on each page load (no session persistence); toggle MUST use semantic HTML with appropriate labels (no specific WCAG compliance required).
- **FR-003**: When the small label format is selected, the printed label MUST omit the asset serial number.
- **FR-004**: When the small label format is selected, spacing and font sizes MUST be reduced so required content fits without overlap; template MUST define max font sizes and use dynamic fit-to-width truncation for asset names (truncate with ellipsis when text exceeds available width after layout).
- **FR-005**: QR code and barcode elements MUST be resized and positioned to remain scannable on the small label; both MUST encode the full asset tracking URL (same content as large label); template MUST specify max element dimensions and minimum quiet zones expressed as percentages of label width/height.
- **FR-006**: System MUST select the small label by default for assets identified as Charger (configurable mapping), and large label for other assets.
- **FR-007**: The small label MUST support preview mode that renders at scale and indicates any truncation or layout changes; preview MUST display a warning if QR/barcode may be unscannable due to size constraints, but allow user to proceed with printing.
- **FR-008**: Batch printing flows MUST allow per-item label-size overrides and preserve overrides for the duration of the print job.
- **FR-009**: The small label template MUST export to existing print targets (print dialog and PDF export) and embed the target dimensions and DPI so printing tools can respect sizing.
- **FR-010**: Provide a help tooltip or inline note indicating the serial number is hidden on small labels and how to select the large label to include it.

### Key Entities _(include if feature involves data)_

- **LabelTemplate**: A named template (Large, Small) with attributes: width, height, element positions (QR, barcode, name, ticket/ID), font rules (max sizes), and visibility flags (serial_visible).
- **Asset**: Existing entity (no schema change) used to decide default label size via `asset.type` or a configurable mapping.
- **PrintJob**: Represents an ephemeral print request with per-item overrides for label template selection.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: For Charger assets, the `labels/print` UI defaults to the Small label 100% of the time in a random sample of at least 100 Charger assets.
- **SC-002**: For non-Charger assets, the `labels/print` UI defaults to the Large label 100% of the time in a random sample of at least 100 non-Charger assets.
- **SC-003**: When printed or exported at target dimensions, 95% of sampled Small label QR codes and barcodes are scannable with a standard phone scanning app within 2 seconds on first attempt (sample size: 50 labels).
- **SC-004**: Small label output respects 1.1" x 3.5" target dimensions within printer margin tolerances and renders required elements without overlap for 95% of sample assets (sample size: 200 assets with varying name lengths).
- **SC-005**: Preview mode visually matches printed output for both Small and Large templates as validated by spot-check printing of at least 20 labels.

### Assumptions

- The existing printing/export pipeline supports rendering templates to PDF or direct print and can accept template size metadata (this feature reuses that pipeline).
- Asset type classification is available as `asset.type` or a configurable taxonomy; administrators can map asset types to default label templates.
- Typical thermal label printers have predictable margin tolerances; final printer tuning may be necessary per site.

### Non-goals

- This feature does NOT manage physical printer configurations or drivers.
- It does NOT persist per-asset label preferences beyond the print job (persistent preference could be a follow-up).

### Test Cases (high level)

1. Single-print Charger: open `labels/print?id=<charger>`, confirm Small toggle selected, preview shows no serial number, export PDF at 29mm x 90.3mm, scan QR/barcode.
2. Single-print non-Charger: open `labels/print?id=<laptop>`, confirm Large toggle selected, preview includes serial number, print/export and confirm content.
3. Batch-print mixed: create a batch with chargers and other devices, confirm per-item defaults, toggle an override for a charger to Large, print and verify outputs.
4. Long-name truncation: create asset with very long name, preview small label and assert truncation warning and printed truncation per rules.

---

**END OF SPEC — READY FOR PLANNING**
```

# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing _(mandatory)_

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements _(mandatory)_

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

_Example of marking unclear requirements:_

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities _(include if feature involves data)_

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria _(mandatory)_

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
