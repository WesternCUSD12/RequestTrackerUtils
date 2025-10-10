# API Contract: Batch Asset Creation

**Feature**: 001-i-need-to  
**Date**: 2025-10-08

## Endpoints

### POST /assets/create

Create a new asset in RT with automatic asset tag assignment and optional label printing.

**Authentication**: Required (existing RT token-based auth)

**Request**:

```http
POST /assets/create HTTP/1.1
Content-Type: application/json

{
  "serial_number": "ABC123456",
  "internal_name": "Dell CB 3100 #1",
  "manufacturer": "Dell",
  "model": "Chromebook 3100",
  "category": "Laptop",
  "funding_source": "Title I"
}
```

**Request Body Schema**:

| Field          | Type   | Required | Validation                                      | Description                               |
| -------------- | ------ | -------- | ----------------------------------------------- | ----------------------------------------- |
| serial_number  | string | Yes      | Non-empty, max 50 chars, alphanumeric + hyphens | Device serial number (must be unique)     |
| internal_name  | string | No       | Max 100 chars                                   | Internal asset name/description           |
| manufacturer   | string | Yes      | Non-empty, max 100 chars                        | Device manufacturer                       |
| model          | string | Yes      | Non-empty, max 100 chars                        | Device model                              |
| category       | string | No       | Max 50 chars                                    | Asset category (e.g., "Laptop", "Tablet") |
| funding_source | string | No       | Max 100 chars                                   | Funding source for purchase               |

**Success Response** (201 Created):

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "success": true,
  "asset_id": 12345,
  "asset_tag": "W12-1234",
  "serial_number": "ABC123456",
  "label_printed": true,
  "message": "Asset W12-1234 created successfully"
}
```

**Success Response Schema**:

| Field           | Type    | Description                                                         |
| --------------- | ------- | ------------------------------------------------------------------- |
| success         | boolean | Always `true` for successful creation                               |
| asset_id        | integer | RT asset ID                                                         |
| asset_tag       | string  | Assigned asset tag (e.g., "W12-1234")                               |
| serial_number   | string  | Serial number from request                                          |
| label_printed   | boolean | Whether label printing succeeded                                    |
| message         | string  | User-friendly success message                                       |
| retry_print_url | string? | Present if `label_printed` is `false` - URL to retry label printing |

**Partial Success Response** (201 Created, label failed):

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "success": true,
  "asset_id": 12345,
  "asset_tag": "W12-1234",
  "serial_number": "ABC123456",
  "label_printed": false,
  "message": "Asset W12-1234 created successfully, but label printing failed",
  "retry_print_url": "/labels/print?asset_id=12345"
}
```

**Error Responses**:

**400 Bad Request - Missing Required Field**:

```json
{
  "success": false,
  "error": "Missing required field: serial_number",
  "field": "serial_number"
}
```

**400 Bad Request - Duplicate Serial Number**:

```json
{
  "success": false,
  "error": "Serial number ABC123456 already exists (Asset #45678)",
  "field": "serial_number",
  "existing_asset_id": 45678
}
```

**400 Bad Request - Invalid Format**:

```json
{
  "success": false,
  "error": "Serial number contains invalid characters",
  "field": "serial_number",
  "validation_rule": "alphanumeric and hyphens only"
}
```

**500 Internal Server Error - RT API Failure**:

```json
{
  "success": false,
  "error": "Failed to create asset in RT: Connection timeout",
  "retry": true
}
```

**500 Internal Server Error - Asset Tag Sequence Error**:

```json
{
  "success": false,
  "error": "Asset tag sequence unavailable",
  "retry": true
}
```

**Status Codes**:

- `201 Created`: Asset successfully created (even if label printing failed)
- `400 Bad Request`: Validation error or duplicate serial number
- `401 Unauthorized`: Missing or invalid authentication
- `500 Internal Server Error`: Server-side error (RT API, file system, etc.)

**Rate Limiting**: None (internal tool, low volume)

**Idempotency**: Not idempotent - each request creates a new asset with a new tag

---

### GET /assets/validate-serial

Validate serial number uniqueness without creating an asset (for client-side validation).

**Authentication**: Required

**Request**:

```http
GET /assets/validate-serial?serial_number=ABC123456 HTTP/1.1
```

**Query Parameters**:

| Parameter     | Type   | Required | Description               |
| ------------- | ------ | -------- | ------------------------- |
| serial_number | string | Yes      | Serial number to validate |

**Success Response** (200 OK):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "valid": true,
  "serial_number": "ABC123456"
}
```

**Duplicate Found Response** (200 OK):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "valid": false,
  "serial_number": "ABC123456",
  "error": "Serial number already exists",
  "existing_asset_id": 45678,
  "existing_asset_tag": "W12-0789"
}
```

**Response Schema**:

| Field              | Type     | Description                                           |
| ------------------ | -------- | ----------------------------------------------------- |
| valid              | boolean  | `true` if serial number is available                  |
| serial_number      | string   | Serial number that was checked                        |
| error              | string?  | Present if `valid` is `false` - reason for invalidity |
| existing_asset_id  | integer? | Present if duplicate found - ID of existing asset     |
| existing_asset_tag | string?  | Present if duplicate found - tag of existing asset    |

**Error Responses**:

**400 Bad Request - Missing Parameter**:

```json
{
  "error": "Missing required parameter: serial_number"
}
```

**Status Codes**:

- `200 OK`: Validation completed (check `valid` field)
- `400 Bad Request`: Missing or invalid parameter
- `401 Unauthorized`: Missing or invalid authentication
- `500 Internal Server Error`: RT API error

---

### GET /assets/preview-next-tag

Get the next asset tag that will be assigned (for UI preview).

**Authentication**: Required

**Request**:

```http
GET /assets/preview-next-tag HTTP/1.1
```

**Success Response** (200 OK):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "next_tag": "W12-1235",
  "prefix": "W12-",
  "sequence_number": 1235
}
```

**Response Schema**:

| Field           | Type    | Description                            |
| --------------- | ------- | -------------------------------------- |
| next_tag        | string  | Full next asset tag (e.g., "W12-1235") |
| prefix          | string  | Tag prefix (e.g., "W12-")              |
| sequence_number | integer | Current sequence number                |

**Status Codes**:

- `200 OK`: Tag retrieved successfully
- `401 Unauthorized`: Missing or invalid authentication
- `500 Internal Server Error`: Sequence file unavailable

**Note**: This endpoint does NOT increment the sequence - it only previews the next tag.

---

### POST /assets/batch/clear-form

Clear persisted form state (server-side session if applicable, primarily client-side sessionStorage).

**Authentication**: Required

**Request**:

```http
POST /assets/batch/clear-form HTTP/1.1
```

**Success Response** (200 OK):

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "message": "Form state cleared"
}
```

**Status Codes**:

- `200 OK`: Form state cleared (or no state existed)
- `401 Unauthorized`: Missing or invalid authentication

**Note**: This endpoint is primarily for consistency - the actual form state lives in browser sessionStorage and is cleared client-side.

---

## Existing Endpoints (Reused)

### GET /labels/print

Generate and return label HTML for printing (existing endpoint, no changes).

**Request**:

```http
GET /labels/print?asset_id=12345 HTTP/1.1
```

**Query Parameters**:

| Parameter | Type    | Required | Description |
| --------- | ------- | -------- | ----------- |
| asset_id  | integer | Yes      | RT asset ID |

**Success Response** (200 OK):

```http
HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html>
<html>
<head>
  <style>/* Print-optimized CSS */</style>
</head>
<body>
  <div class="label">
    <img src="data:image/png;base64,..." alt="QR Code" />
    <div class="asset-tag">W12-1234</div>
    <div class="serial">ABC123456</div>
    <div class="model">Dell Chromebook 3100</div>
    <img src="data:image/png;base64,..." alt="Barcode" />
  </div>
</body>
</html>
```

**Error Responses**:

**404 Not Found**:

```json
{
  "error": "Asset not found"
}
```

**Status Codes**:

- `200 OK`: Label HTML generated successfully
- `404 Not Found`: Asset ID doesn't exist in RT
- `500 Internal Server Error`: Label generation failed

---

## Data Flow Example

### Successful Asset Creation with Label Printing

```
Client                          Server                          RT API
  |                               |                               |
  | POST /assets/create           |                               |
  |------------------------------>|                               |
  |                               | Query serial uniqueness       |
  |                               |------------------------------>|
  |                               |<------------------------------|
  |                               | (no duplicates found)         |
  |                               |                               |
  |                               | Get next asset tag (W12-1234) |
  |                               | (file system)                 |
  |                               |                               |
  |                               | POST /asset (create)          |
  |                               |------------------------------>|
  |                               |<------------------------------|
  |                               | (asset created, ID: 12345)    |
  |                               |                               |
  |                               | Increment sequence            |
  |                               | Log assignment                |
  |                               | (file system)                 |
  |                               |                               |
  |<------------------------------|                               |
  | 201 Created                   |                               |
  | {asset_id: 12345,             |                               |
  |  asset_tag: "W12-1234",       |                               |
  |  label_printed: false}        |                               |
  |                               |                               |
  | GET /labels/print?asset_id=12345                              |
  |------------------------------>|                               |
  |                               | Fetch asset details           |
  |                               |------------------------------>|
  |                               |<------------------------------|
  |                               | Generate label HTML           |
  |<------------------------------|                               |
  | 200 OK (HTML)                 |                               |
  |                               |                               |
  | window.print()                |                               |
  | (client-side)                 |                               |
```

### Asset Creation with Duplicate Serial Number

```
Client                          Server                          RT API
  |                               |                               |
  | POST /assets/create           |                               |
  |------------------------------>|                               |
  |                               | Query serial uniqueness       |
  |                               |------------------------------>|
  |                               |<------------------------------|
  |                               | (duplicate found, ID: 45678)  |
  |                               |                               |
  |<------------------------------|                               |
  | 400 Bad Request               |                               |
  | {error: "Serial number exists",                               |
  |  existing_asset_id: 45678}    |                               |
```

---

## Backward Compatibility

All new endpoints are additive - no existing endpoints are modified. The feature can be deployed without affecting existing functionality.

**New Routes**:

- `/assets/create` - NEW
- `/assets/validate-serial` - NEW
- `/assets/preview-next-tag` - NEW
- `/assets/batch/clear-form` - NEW

**Reused Routes** (no changes):

- `/labels/print` - EXISTING
- `/next-asset-tag` - EXISTING (tag_routes.py)

---

## Error Handling Principles

1. **Validation errors** (400): Client can correct and retry
2. **Duplicate detection** (400): Client must change serial number
3. **RT API errors** (500): Client should retry after delay
4. **File system errors** (500): Client should retry after delay
5. **Label generation errors**: Asset created successfully, label can be retried independently

All error responses include actionable messages suitable for display to end users.
