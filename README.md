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

**Response:** A PDF file containing the asset label.

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

## Database Schema

The application uses an SQLite database with the following schema:

```sql
CREATE TABLE asset_tags (
  tag_number INTEGER PRIMARY KEY,
  full_tag TEXT UNIQUE NOT NULL,
  rt_asset_id INTEGER NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TIMESTAMP NULL
);
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
