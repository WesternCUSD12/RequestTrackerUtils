# Feature Specification: Streamlined Asset Creation with Batch Entry

**Feature Branch**: `001-i-need-to`  
**Created**: 2025-10-08  
**Status**: Draft  
**Input**: User description: "I need to update the page that creates a new asset. It should: allow creating the same asset type (manufacturer, model, etc) over and over but allow updating the serial number and internal name per device. It should auto increment the asset id. It should print an asset label after creation."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Rapid Batch Asset Entry (Priority: P1)

IT staff needs to quickly register multiple identical devices (same manufacturer, model, funding source) by only changing unique identifiers like serial number and internal asset name. This enables efficient processing of bulk device shipments.

**Why this priority**: Core value proposition - dramatically reduces data entry time when receiving shipments of identical devices (e.g., 30 Chromebooks of the same model).

**Independent Test**: Can be fully tested by creating 3 identical assets with different serial numbers and verifying all are created correctly in RT with proper asset tags.

**Acceptance Scenarios**:

1. **Given** IT staff is on the asset creation page, **When** they enter manufacturer, model, and other common details, **Then** these values persist across subsequent asset entries
2. **Given** common asset details are pre-filled, **When** staff updates only the serial number and internal name, **Then** they can quickly create the next asset without re-entering common information
3. **Given** an asset is successfully created, **When** the system generates the asset tag, **Then** it automatically increments from the previous asset (e.g., W12-1001 → W12-1002)
4. **Given** an asset is created with all required fields, **When** creation completes, **Then** the asset label automatically prints or displays for printing

---

### User Story 2 - Asset Label Auto-Generation (Priority: P2)

After creating each asset, staff needs an immediate physical label to attach to the device without navigating to a separate labeling workflow.

**Why this priority**: Streamlines the device preparation workflow - prevents forgetting to print labels or losing track of which devices need labels.

**Independent Test**: Create a single asset and verify a printable label with QR code and asset information is immediately available.

**Acceptance Scenarios**:

1. **Given** an asset is successfully created in RT, **When** the creation process completes, **Then** a printable label is automatically generated and the browser print dialog is triggered immediately
2. **Given** the print dialog opens, **When** staff views the label preview, **Then** it includes all necessary information (asset tag, QR code, serial number, model) for physical identification

---

### User Story 3 - Form State Management (Priority: P3)

When creating multiple similar assets, staff should be able to modify which fields persist and optionally clear the form to start a completely new asset type.

**Why this priority**: Provides flexibility when processing mixed shipments or switching between different device types.

**Independent Test**: Create 3 assets of one type, clear the form, and create 2 assets of a different type to verify form management works correctly.

**Acceptance Scenarios**:

1. **Given** staff is creating multiple assets, **When** they want to start a new asset type, **Then** a "Clear All" button resets all fields to empty
2. **Given** form has persisted values, **When** staff manually changes a persisted field, **Then** the new value becomes the default for subsequent entries
3. **Given** an asset creation fails, **When** the error is displayed, **Then** all entered values are retained so staff can correct and retry without re-entering data

---

### Edge Cases

- What happens when the asset tag sequence runs out or reaches a configured maximum? (Resolved: Add an additional digit, e.g., W12-9999 → W12-10000)
- How does the system handle duplicate serial numbers being entered? (Resolved: Validation prevents creation, organization-wide uniqueness enforced)
- What happens if the label printing service is unavailable or fails? (Resolved: Show success with "Retry Print" button)
- What happens if a user navigates away mid-entry - are unsaved changes preserved? (Resolved: Values persist until browser tab closed)

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST persist common asset fields (manufacturer, model, funding source, category) across multiple asset creation operations within the browser tab session (cleared when tab/window is closed)
- **FR-002**: System MUST provide editable input fields for unique identifiers (serial number, internal asset name) that reset after each successful creation
- **FR-003**: System MUST automatically increment the asset tag identifier following the configured sequence (e.g., W12-1001, W12-1002, W12-1003); when the sequence reaches its maximum (e.g., W12-9999), the system MUST add an additional digit (e.g., W12-10000)
- **FR-004**: System MUST create the asset in RT with all provided information before generating the label
- **FR-005**: System MUST automatically generate a printable asset label and trigger the browser print dialog immediately after successful asset creation
- **FR-006**: System MUST validate that serial numbers are unique across all assets in RT (organization-wide) before creating new assets
- **FR-007**: System MUST display clear success confirmation including the assigned asset tag after each creation
- **FR-011**: System MUST handle label generation failures gracefully by showing success for asset creation with the asset tag and providing a "Retry Print" button to regenerate the label
- **FR-008**: System MUST provide a "Clear All" or "Reset Form" option to empty all persisted fields
- **FR-009**: System MUST preserve form data if asset creation fails, allowing users to correct errors without re-entry
- **FR-010**: System MUST log all asset creation operations with timestamps, asset tags, and user information for audit purposes

### Key Entities

- **Asset**: Represents physical devices being tracked. Key attributes include: asset tag (auto-generated), manufacturer, model, serial number (unique), internal name, funding source, category, creation timestamp, created by user.

- **Asset Tag Sequence**: Tracks the current position in the sequential tag numbering system. Maintains prefix (e.g., W12-) and current number with atomic increment operations.

- **Asset Label**: Print-ready representation of an asset. Includes: asset tag, QR code linking to asset details, serial number, model, manufacturer.

## Clarifications

### Session 2025-10-08

- Q: How should the label be presented to the user after asset creation? → A: Automatically trigger browser print dialog (no preview)
- Q: What should happen when asset is created in RT but label generation/printing fails? → A: Show success message with asset tag and "Retry Print" button
- Q: Serial numbers must be unique within what scope? → A: Unique across all assets in RT (organization-wide)
- Q: Should persisted form values survive browser refresh or only within current page session? → A: Persist until browser tab/window closed (session storage)
- Q: What should happen when asset tag sequence reaches its limit? → A: add a digit

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: IT staff can create 10 identical assets (different serial numbers only) in under 5 minutes
- **SC-002**: Asset tag sequence increments correctly without gaps or duplicates across 100+ consecutive asset creations
- **SC-003**: 95% of asset creation operations automatically generate printable labels within 2 seconds of asset creation
- **SC-004**: Zero duplicate asset tags are assigned during bulk asset entry operations
- **SC-005**: Users successfully complete asset creation on first attempt 90% of the time without validation errors

## Assumptions

- The existing asset tag sequence system (W12- prefix) continues to be used
- Users have appropriate permissions to create assets in RT
- The label printing system integration already exists and follows current label format specifications
- Browser session storage will be used for persisting form values (cleared when tab/window closes)
- Asset creation page is accessed via web browser (not mobile app)
- Labels will use the existing QR code and barcode generation utilities
- RT API integration for asset creation is already functional

## Dependencies

- Existing RT API integration for asset creation
- Current asset tag sequence management system
- Label generation utilities (QR code, barcode, PDF generation)
- RT authentication and authorization system

## Out of Scope

- Modifying the asset tag prefix or numbering scheme
- Bulk import from CSV or external files
- Editing existing assets (this is purely for creation)
- Mobile-specific interface optimizations
- Offline asset creation capability
- Integration with procurement or inventory management systems beyond RT
