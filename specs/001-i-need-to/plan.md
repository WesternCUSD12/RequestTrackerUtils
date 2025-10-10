# Implementation Plan: Streamlined Asset Creation with Batch Entry

**Branch**: `001-i-need-to` | **Date**: 2025-10-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-i-need-to/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature enhances the asset creation page to support rapid batch entry of identical devices. IT staff can create multiple assets by persisting common fields (manufacturer, model, funding source) across entries while only updating unique identifiers (serial number, internal name) for each device. The system automatically increments asset tags sequentially and triggers the browser print dialog for immediate label printing after each successful creation. This dramatically reduces data entry time when processing bulk device shipments, targeting completion of 10 identical assets in under 5 minutes.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 2.2+, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+  
**Storage**: File-based (asset_tag_sequence.txt for sequence tracking, session storage in browser for form persistence)  
**Testing**: Integration tests for RT API interaction, browser-based testing for print dialog behavior  
**Target Platform**: Web browser (Chrome, Firefox, Safari) accessing Flask web server  
**Project Type**: Web application (Flask backend with Jinja2 templates for frontend)  
**Performance Goals**: Asset creation + label generation < 2 seconds per device (95% of operations per SC-003); batch of 10 assets in < 5 minutes total (per SC-001)  
**Constraints**: Browser session storage only (cleared on tab close); sequential asset tag assignment must be atomic to prevent collisions; print dialog must work across major browsers  
**Scale/Scope**: Small team (< 50 IT staff users); processing batches of 10-50 identical assets per session; organization-wide serial number uniqueness validation

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Integration-First Architecture**:

- [x] Feature integrates with existing RT/Google Workspace systems - Uses existing RT API for asset creation, label generation utilities
- [x] Provides both REST API endpoints and web interface - New web form with supporting API endpoints for asset creation
- [x] Maintains cross-system data consistency - Asset created in RT before label generation; failures handled gracefully

**Error Handling & Logging**:

- [x] All external API calls include try/catch with descriptive errors - RT API calls wrapped in error handling with user-friendly messages
- [x] Sufficient logging for debugging without exposing sensitive data - Audit logs with timestamps, asset tags, user info (FR-010)
- [x] Rate limiting and retry logic for external APIs - Existing RT API integration includes retry logic; print dialog triggered after successful RT creation

**API Compatibility**:

- [x] Maintains backward compatibility for existing endpoints - No existing endpoints modified; new routes added only
- [x] New fields only, no removal/type changes to existing fields - New feature, no changes to existing API contracts
- [x] Follows semantic versioning for breaking changes - N/A, additive changes only

**Data Integrity**:

- [x] Atomic operations with proper transaction handling - Asset tag sequence increment uses file locking (existing AssetTagManager)
- [x] Database validation at API and schema levels - Serial number uniqueness validated against RT before creation (FR-006)
- [x] Migration scripts with rollback procedures - N/A, no database schema changes required

**Observability**:

- [x] Clear success/failure feedback with actionable errors - Success confirmation with asset tag; "Retry Print" button on label failures (FR-007, FR-011)
- [x] Audit logging with timestamps for all operations - Asset creation operations logged with timestamps, tags, user (FR-010)
- [x] Administrative status reporting - Success messages show asset tag; error states preserved for correction (FR-009)

**✅ All gates PASSED - Constitution compliance verified post-design**

## Phase 1 Completion Report

**Phase 1 Status**: ✅ COMPLETE

### Artifacts Created

1. **research.md** ✅

   - 6 technical research areas documented
   - sessionStorage API usage patterns defined
   - window.print() implementation strategy established
   - Serial uniqueness validation approach confirmed
   - Dynamic tag expansion algorithm specified
   - Partial failure handling patterns defined
   - Form reset behaviors clarified

2. **data-model.md** ✅

   - 6 entities documented with validation rules
   - Data relationships and constraints defined
   - 14-step asset creation flow documented
   - Error handling flows specified
   - State management patterns clarified

3. **contracts/api-contract.md** ✅

   - 4 new endpoints fully specified
   - 1 reused endpoint documented
   - Request/response schemas defined
   - Error scenarios enumerated
   - HTTP status codes specified

4. **quickstart.md** ✅

   - Complete implementation guide created
   - Code samples for all components
   - Step-by-step integration instructions
   - Testing procedures documented
   - Troubleshooting guide included

5. **Agent Context Update** ✅
   - GitHub Copilot instructions updated
   - Python 3.11+ + Flask 2.2+ registered
   - File-based storage noted
   - Recent changes logged

### Constitution Re-Evaluation

All 15 constitution gates remain **PASSED** after Phase 1 design:

- Integration patterns validated against existing code
- Error handling strategies fully specified
- API compatibility verified (additive only)
- Data integrity mechanisms confirmed
- Observability patterns documented

### Ready for Phase 2

**Next Step**: User should invoke `/speckit.tasks` command to:

1. Generate tasks.md with prioritized implementation breakdown
2. Create atomic, testable task units
3. Begin implementation execution

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
request_tracker_utils/
├── routes/
│   ├── asset_routes.py      # NEW: Batch asset creation endpoints
│   ├── tag_routes.py         # EXISTING: Asset tag management (reused)
│   └── label_routes.py       # EXISTING: Label generation (reused)
├── templates/
│   ├── asset_create.html     # NEW: Batch asset creation form
│   └── base.html             # EXISTING: Template base (extended)
├── utils/
│   ├── rt_api.py             # EXISTING: RT API integration (reused)
│   └── pdf_generator.py      # EXISTING: Label generation (reused)
└── static/
    └── js/
        └── asset_batch.js    # NEW: Form state management & session storage

tests/
└── integration/
    └── test_asset_batch.py   # NEW: Integration tests for batch creation
```

**Structure Decision**: Web application using Flask with Jinja2 templates. This feature adds new routes and templates to the existing Flask application structure. Leverages existing RT API integration (`rt_api.py`), asset tag management (`AssetTagManager` in `tag_routes.py`), and label generation utilities (`pdf_generator.py`, `label_routes.py`). No database schema changes required - uses file-based sequence tracking and browser session storage for form persistence.

## Complexity Tracking

_No violations - all Constitution gates passed_
