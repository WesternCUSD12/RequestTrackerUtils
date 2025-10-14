# Implementation Plan: Small-format printable asset label (1.1" x 3.5")

**Branch**: `003-rtutils-should-offer` | **Date**: 2025-10-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-rtutils-should-offer/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add a new small label template (1.1" x 3.5" / 29mm x 90.3mm) for compact device labels, primarily for chargers. The implementation extends the existing Flask-based label printing system with a new template option, size toggle UI, and automatic default selection based on asset type. The small label omits serial numbers, uses dynamic text truncation, and maintains QR/barcode scannability through size optimization.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 2.2+, ReportLab 3.6+ (PDF generation), qrcode 7.3+, python-barcode 0.13+, Pillow (image manipulation)  
**Storage**: File-based templates and CSS; existing SQLite database for asset metadata (no schema changes required)  
**Testing**: pytest with Flask test client; integration tests for rendering and PDF export  
**Target Platform**: Linux/macOS server with thermal label printer support (Brother QL-series or similar)
**Project Type**: Web application (Flask backend with Jinja2 templates)  
**Performance Goals**: Label preview render < 500ms; PDF generation < 1s; support 50 concurrent label generation requests with graceful degradation (requests beyond 50 concurrent receive HTTP 503 Service Unavailable with Retry-After header; existing requests complete normally)  
**Constraints**: Label dimensions fixed at 1.1" x 3.5" (29mm x 90.3mm) with ±2mm printer margin tolerance; QR/barcode must be scannable at small size (95% success rate target)  
**Scale/Scope**: ~5000 assets in system; 100-200 labels printed daily; 2 label templates (Large, Small); single-page preview UI

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

**Integration-First Architecture**:

- [x] Feature integrates with existing RT systems (reads asset metadata; no Google Workspace interaction needed)
- [x] Provides both REST API endpoints (`/labels/print?size=small`) and web interface (toggle in UI)
- [x] Maintains cross-system data consistency (no data writes; rendering only)

**Error Handling & Logging**:

- [x] All external API calls include try/catch with descriptive errors (reuses existing RT fetch functions with error handling)
- [x] Sufficient logging for debugging without exposing sensitive data (logs template selection, truncation warnings, QR generation issues)
- [N/A] Rate limiting and retry logic for external APIs (no new external API calls; reads from existing RT integration)

**API Compatibility**:

- [x] Maintains backward compatibility for existing endpoints (`/labels/print` without size param defaults to large label)
- [x] New fields only, no removal/type changes to existing fields (adds optional `size` query param; response unchanged)
- [N/A] Follows semantic versioning for breaking changes (no breaking changes; additive only)

**Data Integrity**:

- [N/A] Atomic operations with proper transaction handling (no database writes)
- [N/A] Database validation at API and schema levels (no schema changes)
- [N/A] Migration scripts with rollback procedures (no migrations required)

**Observability**:

- [x] Clear success/failure feedback with actionable errors (preview shows truncation/unscannable warnings)
- [x] Audit logging with timestamps for all operations (logs template selection and print requests)
- [N/A] Administrative status reporting (no admin operations; user-facing print only)

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
│   ├── label_routes.py           # MODIFY: Add size parameter, template selection logic
│   └── __init__.py               # (no changes)
│
├── templates/
│   ├── label.html                # (no changes - large label template)
│   ├── small_label.html          # NEW: Small label template (29mm x 90.3mm)
│   └── label_form.html           # MODIFY: Add radio buttons for size selection
│
├── utils/
│   ├── label_config.py           # NEW: LabelTemplate dataclass + LABEL_TEMPLATES dict
│   ├── pdf_generator.py          # MODIFY: Extend create_pdf_label() for small size
│   └── text_utils.py             # NEW: truncate_text_to_width() function
│
└── static/
    └── css/
        └── labels.css            # MODIFY: Add @page rules for small labels

tests/
├── test_label_routes.py          # MODIFY: Add small label print tests
├── test_text_truncation.py       # NEW: Unit tests for truncate_text_to_width()
└── test_label_config.py          # NEW: Tests for LabelTemplate dataclass
```

**Structure Decision**: Web application (Flask backend with Jinja2 templates)

**Key Paths**:

- **Modified Routes**: `request_tracker_utils/routes/label_routes.py` (add `size` param logic)
- **New Template**: `request_tracker_utils/templates/small_label.html` (29mm x 90.3mm layout)
- **New Config Module**: `request_tracker_utils/utils/label_config.py` (LabelTemplate definitions)
- **New Utility**: `request_tracker_utils/utils/text_utils.py` (truncation function)
- **Test Files**: Add 2 new test files, modify 1 existing (label_routes tests)

## Complexity Tracking

_No violations detected. Constitution Check passed with all N/A items justified (no DB writes, no external APIs, no breaking changes)._

---

## Phase 0: Outline & Research

**Objective**: Resolve technical unknowns and document key decisions before design.

**Deliverables**:

- ✅ **research.md**: Technical research covering QR code sizing, text truncation algorithm, barcode optimization, CSS @page strategy, and default size selection logic
  - File: `specs/003-rtutils-should-offer/research.md`
  - Status: Complete (7 research questions resolved, 2 technology decisions documented)

**Key Decisions**:

1. **QR Code Sizing**: 20mm x 20mm with Medium error correction (balance of data/redundancy for 50-80 char URLs)
2. **Text Truncation**: Server-side using ReportLab `pdfmetrics.stringWidth()` with binary search algorithm
3. **Barcode Dimensions**: Code128 at 70mm x 8mm (reduced height, full width for scannability)
4. **CSS Strategy**: Separate templates with template-specific `@page` rules (label.html vs small_label.html)
5. **Default Logic**: Client-side selection based on RT asset "Type" field (chargers → small, Chromebooks → large)
6. **PDF Library**: ReportLab (existing dependency, precise control over positioning)
7. **Template Architecture**: Separate small_label.html (avoids complex conditionals in single template)

**Gate Status**: ✅ **PASSED** - All research questions resolved, no blockers for Phase 1.

---

## Phase 1: Design & Contracts

**Objective**: Define data models, API contracts, and user-facing documentation.

**Deliverables**:

- ✅ **data-model.md**: Entity definitions (LabelTemplate, Asset, PrintJob) with validation rules and data flow diagram
  - File: `specs/003-rtutils-should-offer/data-model.md`
  - Status: Complete (3 entities defined, no DB schema changes confirmed)
- ✅ **contracts/api.md**: API contract for modified `/labels/print` endpoint with backward compatibility guarantees
  - File: `specs/003-rtutils-should-offer/contracts/api.md`
  - Status: Complete (GET /labels/print extended with `size` param, internal function contracts defined)
- ✅ **quickstart.md**: User-facing guide covering when to use small labels, print workflow, troubleshooting, and printer configuration
  - File: `specs/003-rtutils-should-offer/quickstart.md`
  - Status: Complete (5 sections: overview, print workflow, layout reference, troubleshooting, best practices)

**Key Design Points**:

1. **LabelTemplate Dataclass**: Defines dimensions, font size, QR/barcode sizing for "large" and "small" variants
2. **No Database Changes**: All configuration is code-based (LABEL_TEMPLATES dict in label_config.py)
3. **Backward Compatibility**: `/labels/print` without `size` param defaults to "large" (existing behavior preserved)
4. **Error Handling**: Preview warnings for truncated names and potentially unscannable QR codes
5. **Print Job Lifecycle**: Ephemeral (no persistence; created on request, discarded after response)

**Constitution Re-Check**: ✅ **PASSED** - Design artifacts confirm no violations (no DB writes, no breaking API changes, proper error handling).

---

## Phase 2: Implementation & Testing

**Objective**: Implement small label feature with full test coverage.

**Status**: ⏸️ **NOT STARTED** - Awaiting completion of `/speckit.tasks` command to generate tasks.md.

**Key Implementation Areas** (preview):

1. **Backend Changes**:

   - Create `label_config.py` with LabelTemplate dataclass and LABEL_TEMPLATES dict
   - Modify `label_routes.py:print_label()` to handle `size` query param and template selection
   - Create `text_utils.py:truncate_text_to_width()` using ReportLab stringWidth
   - Extend `pdf_generator.py:create_pdf_label()` to support small label dimensions
   - Update `generate_qr_code()` and `generate_barcode()` to accept size/dimension parameters

2. **Frontend Changes**:

   - Create `small_label.html` template with 29mm x 90.3mm @page rules
   - Modify `label_form.html` to add radio buttons for size selection (pre-select based on asset Type)
   - Add CSS for small label print styling (labels.css or embedded in small_label.html)

3. **Testing**:
   - Unit tests: `test_text_truncation.py` (10+ test cases for edge cases)
   - Unit tests: `test_label_config.py` (validate LabelTemplate dataclass)
   - Integration tests: `test_label_routes.py` (add small label print workflow tests)
   - Manual testing: Print test labels on thermal printer, verify QR/barcode scannability

**Next Steps**:

1. Run `/speckit.tasks` to generate `tasks.md` with Markdown task list
2. Agent implements tasks sequentially, marking progress in tasks.md
3. Run tests after each task completion (pytest)
4. Final validation: Print test labels and verify scannability

---

## Phase 3: Agent Context Update

**Objective**: Update agent context file with new paths and patterns for future AI assistance.

**Command**: `.specify/scripts/bash/update-agent-context.sh copilot`

**Context Updates**:

- Add `request_tracker_utils/utils/label_config.py` (LabelTemplate definitions)
- Add `request_tracker_utils/templates/small_label.html` (small label template)
- Add `request_tracker_utils/utils/text_utils.py` (truncation utility)
- Document `size` query parameter for `/labels/print` route
- Note default size selection logic (chargers → small, others → large)

**Status**: ⏸️ **PENDING** - Run after Phase 2 implementation complete.

---

## Phase 4: Deployment & Validation

**Objective**: Deploy to production and validate with real-world usage.

**Deployment Steps**:

1. Merge feature branch `003-rtutils-should-offer` to `main`
2. Deploy Flask app to production server (standard deployment process)
3. Update printer configuration to support 29mm x 90.3mm custom paper size
4. Train IT staff on small label workflow (share quickstart.md)

**Validation Criteria** (from spec.md Success Criteria):

1. ✅ Small label template renders correctly at 29mm x 90.3mm in browser print preview
2. ✅ QR codes and barcodes on small labels scan successfully with handheld scanners (95%+ success rate)
3. ✅ Charger assets default to small label, Chromebooks default to large label in form UI
4. ✅ Asset names longer than 60mm are truncated with "..." in small label preview and PDF
5. ✅ Users can toggle between large and small labels without refreshing the page

**Rollback Plan**:

- Remove `size` parameter handling from label_routes.py (reverts to large-only)
- No database rollback needed (no schema changes)
- Redeploy previous version if critical issues detected

**Status**: ⏸️ **PENDING** - Run after Phase 2-3 complete.

---

## Plan Completion Checklist

- [x] Summary section filled with feature overview
- [x] Technical Context section filled with Python/Flask stack details
- [x] Constitution Check completed and passed (no violations)
- [x] Project Structure documented with concrete file paths
- [x] Phase 0 research.md generated and completed
- [x] Phase 1 data-model.md generated and completed
- [x] Phase 1 contracts/api.md generated and completed
- [x] Phase 1 quickstart.md generated and completed
- [x] Phase 1 Constitution Re-Check passed
- [x] Phase 2 implementation overview documented (tasks.md generation pending)
- [x] Phase 3 agent context update command documented
- [x] Phase 4 deployment strategy outlined

**Overall Status**: ✅ **PLAN COMPLETE** - Ready for `/speckit.tasks` command to generate implementation tasks.
