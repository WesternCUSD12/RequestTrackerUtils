# RT Asset Utils

RT Asset Utils is a Flask-based application designed to manage asset tags and interact with the Request Tracker (RT) system. It provides endpoints for generating asset tags, confirming them, and printing labels.

## Requirements

- Python >= 3.11
- Flask >= 2.2.0
- pandas >= 1.5.0
- requests >= 2.28.0
- click >= 8.0.0
- reportlab >= 3.6.0
- qrcode >= 7.3.1

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd nix-python-devenv
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database:

   ```bash
   flask init-db
   ```

4. Run the server:
   ```bash
   python run.py
   ```

The server will start on `http://127.0.0.1:5000`.

## Routes

### 1. `/`

**Method:** `GET`
**Description:** A simple route to check if the server is running.
**Response:**

```json
{
  "message": "Server is running!"
}
```

---

### 2. `/print_label`

**Method:** `GET`
**Description:** Generates a PDF label for a given asset ID.
**Query Parameters:**

- `assetId` (required): The ID of the asset in the RT system.

**Example Request:**

```bash
curl "http://127.0.0.1:5000/print_label?assetId=12345"
```

**Response:** A html doc containing the asset label.

---

### 3. `/next-asset-tag`

**Method:** `GET`
**Description:** Generates the next available asset tag.
**Response:**

```json
{
  "tag_number": 1025,
  "full_tag": "W12-1025"
}
```

---

### 4. `/confirm-asset-tag`

**Method:** `POST`
**Description:** Confirms an asset tag and associates it with an RT asset ID.
**Request Body:**

```json
{
  "tag_number": 1025,
  "rt_asset_id": 12345
}
```

**Response:**

```json
{
  "message": "Asset tag confirmed successfully."
}
```

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
