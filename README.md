# RequestTracker Utils

RequestTracker Utils is a Flask-based application designed to manage asset tags and interact with the Request Tracker (RT) system. It provides multiple key functionalities:

1. **Asset Tag Management**: Generate sequential asset tags with configurable prefixes, automatically assign them to assets in RT, and maintain audit logs of tag assignments.

2. **Label Printing**: Generate and print professional-quality asset labels with QR codes, barcodes, and customizable asset information.

3. **RT Integration**: Seamlessly integrate with Request Tracker using both API calls and webhooks for automation.

4. **Batch Processing**: Efficiently handle multiple assets at once for tasks like batch label printing or asset updates.

5. **Device Ownership Management**: Identify all devices belonging to a user and process them together for efficient check-in/check-out workflows.

## Features

### Asset Tag Management

- Generate sequential asset tags with customizable prefixes (default: W12-)
- Automatically assign tags to new assets in Request Tracker
- Maintain audit logs of all tag assignments
- Update asset names in RT to match assigned tags

### Label Printing

- Generate professional-quality asset labels for printing
- Include QR codes for quick access to RT asset details
- Include barcodes for scanning
- Display customizable asset information (name, serial number, model, etc.)
- Print batch labels with one label per page

### RT Integration

- Seamless integration with Request Tracker API
- Webhook support for automatic asset tag assignment
- Batch processing for multiple assets

### Device Ownership Management

- Efficiently retrieve all devices belonging to a specific user
- Associate multiple devices with a single user
- Process device check-ins in batch for users with multiple devices
- Automatically generate comprehensive device lists for inventory management

## Requirements

- Python >= 3.11
- Flask >= 2.2.0
- requests >= 2.28.0
- qrcode >= 7.3.1
- python-barcode >= 0.13.1
- Pillow >= 9.0.0

## Installation

### Standard Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/WesternCUSD12/RequestTrackerUtils.git
   cd RequestTrackerUtils
   ```

2. Install dependencies:

   ```bash
   pip install -e .
   ```

3. Set environment variables for configuration:

   ```bash
   export RT_URL="https://your-rt-instance.com"
   export RT_TOKEN="your-rt-api-token"
   export API_ENDPOINT="/REST/2.0"
   export PREFIX="W12-" # Optional: default asset tag prefix
   ```

4. Run the server:
   ```bash
   python run.py
   ```

The server will start on `http://127.0.0.1:8080` by default.

### Using Nix Development Environment

This project includes a `flake.nix` for reproducible development environments.

1. Enter the development environment:

   ```bash
   nix develop
   # OR
   devenv shell
   ```

2. Run the server:
   ```bash
   python run.py
   ```

## Routes

### Home

### 1. `/`

**Method:** `GET`
**Description:** Home page with documentation and available routes.
**Response:** HTML documentation or JSON list of available routes (based on Accept header)

---

### Label Routes

### 2. `/labels/print`

**Method:** `GET`
**Description:** Generates a label for a given asset.
**Query Parameters:**

- `assetId` (optional): The ID of the asset in the RT system.
- `assetName` (optional): The name of the asset to lookup.

**Example Request:**

```bash
curl "http://127.0.0.1:8080/labels/print?assetId=12345"
```

**Response:** HTML document with the asset label for printing.

---

### 3. `/labels/batch`

**Method:** `GET/POST`
**Description:** Interface for generating batch labels.
**POST Parameters:**

- `query` (optional): RT query to find matching assets.
- `asset_names` (optional): List of asset names to generate labels for.

**Response:** HTML document with multiple asset labels for printing.

---

### 4. `/labels/debug`

**Method:** `GET`
**Description:** Debugging interface for label generation.

---

### 5. `/labels/direct-print`

**Method:** `GET`
**Description:** Direct label printing by asset ID.
**Query Parameters:**

- `id` (required): The asset ID to print.

**Response:** HTML document with the asset label for printing.

---

### Asset Tag Routes

### 6. `/next-asset-tag`

**Method:** `GET`
**Description:** Gets the next available asset tag without incrementing the sequence.
**Response:**

```json
{
  "next_asset_tag": "W12-1025"
}
```

---

### 4. `/confirm-asset-tag`

**Method:** `POST`
**Description:** Confirms an asset tag and associates it with an RT asset ID.
**Request Body:**

```json
{
  "asset_tag": "W12-1025",
  "request_tracker_id": 12345
}
```

**Response:**

```json
{
  "message": "Asset tag confirmation logged successfully. Asset name updated in RT."
}
```

---

### 5. `/update-asset-name`

**Method:** `POST`
**Description:** Updates an asset's name in Request Tracker.
**Request Body:**

```json
{
  "asset_id": 123,
  "asset_name": "W12-0001"
}
```

**Response:**

```json
{
  "message": "Asset name updated successfully to 'W12-0001'",
  "old_name": "Previous Name",
  "new_name": "W12-0001",
  "asset_id": 123
}
```

---

### 6. `/webhook/asset-created`

**Method:** `POST`
**Description:** Webhook endpoint for RT to call when a new asset is created.
**Request Body:**

```json
{
  "asset_id": 123,
  "event": "create",
  "timestamp": 1680123456
}
```

**Response:**

```json
{
  "message": "Asset tag W12-0001 assigned to asset 123",
  "asset_id": 123,
  "asset_tag": "W12-0001",
  "previous_name": "Previous Name"
}
```

---

## Automatic Asset Tag Assignment

This application can automatically assign asset tags to newly created assets in Request Tracker using a webhook. This eliminates the need for manual tag assignment and ensures consistent tag formatting.

### RT Webhook Configuration

To automatically assign asset tags when assets are created in Request Tracker, configure a webhook Scrip:

1. Go to Admin > Global > Scrips > Create
2. Set these Scrip properties:
   - Description: Auto Asset Tag Assignment
   - Condition: On Create
   - Stage: TransactionCreate
   - Action: User Defined
   - Template: User Defined
3. In the Custom Condition code, add:

```perl
return 1 if $self->TransactionObj->Type eq 'Create' && $self->TransactionObj->ObjectType eq 'RT::Asset';
return 0;
```

4. In the Custom Action code, add:

```perl
use LWP::UserAgent;
use JSON;
use HTTP::Request;

my $asset_id = $self->TransactionObj->ObjectId;
my $webhook_url = 'http://your-server-address/webhook/asset-created';

# Get the asset object to modify it later
my $asset = RT::Asset->new($RT::SystemUser);
$asset->Load($asset_id);

# Use eval for error handling
eval {
  # Create a user agent for making HTTP requests
  my $ua = LWP::UserAgent->new(timeout => 10);

  # Send POST request to the webhook with the asset ID
  my $response = $ua->post(
    $webhook_url,
    'Content-Type' => 'application/json',
    'Content' => encode_json({
      asset_id => $asset_id,
      event => 'create',
      timestamp => time()
    })
  );

  # Check if the request was successful
  if ($response->is_success) {
    # Parse the JSON response
    my $result = decode_json($response->decoded_content);

    # If the webhook assigned a tag, update the asset name in RT
    if ($result->{asset_tag}) {
      my $new_tag = $result->{asset_tag};

      # Update the asset's name
      $RT::Logger->info("Updating asset #$asset_id name to '$new_tag'");
      $asset->SetName($new_tag);

      # Log the result
      $RT::Logger->info("Asset #$asset_id name updated to: " . $asset->Name);
    } else {
      $RT::Logger->warning("No asset tag received from webhook for asset #$asset_id");
    }
  } else {
    # Log the error if the webhook request failed
    $RT::Logger->error("Webhook request failed: " . $response->status_line);
    $RT::Logger->error("Response content: " . $response->decoded_content);
  }
};
if ($@) {
  # Catch any exceptions and log them
  $RT::Logger->error("Error in asset creation webhook: $@");
}

# Return success regardless of webhook result to avoid affecting RT
return 1;
```

5. Apply to: Assets
6. Set appropriate Queue/Catalog restrictions if needed
7. Save the Scrip

**Note:** Be sure to replace 'http://your-server-address' with your actual server URL.

---

## NixOS Service Module

This project includes a NixOS service module for deploying the Flask app as a systemd service.

### Configuration Options

| Option        | Type   | Default                                    | Description                           |
| ------------- | ------ | ------------------------------------------ | ------------------------------------- |
| `enable`      | bool   | `false`                                    | Enable the Flask app service.         |
| `host`        | string | `"127.0.0.1"`                              | Host address for the Flask app.       |
| `port`        | int    | `5000`                                     | Port for the Flask app.               |
| `secretsFile` | path   | `"/etc/request-tracker-utils/secrets.env"` | Path to the secrets environment file. |

### Example Configuration

To use this module via a Nix flake, add the following to your `flake.nix`:

```nix
{
   inputs = {
      nixpkgs.url = "github:NixOS/nixpkgs";
      request-tracker-utils.url = "github:WesternCUSD12/RequestTrackerUtils";
   };

   outputs = { self, nixpkgs, request-tracker-utils }: {
      nixosConfigurations.mySystem = nixpkgs.lib.nixosSystem {
         system = "x86_64-linux";
         modules = [
            ./hardware-configuration.nix
            request-tracker-utils.nixosModule
            {
               services.requestTrackerUtils = {
                  enable = true;
                  host = "0.0.0.0";
                  port = 8080;
                  secretsFile = "/run/secrets/request-tracker-utils.env";
               };
            }
         ];
      };
   };
}
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
