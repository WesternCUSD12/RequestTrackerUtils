# Environment Variable Matrix

Captured: 2025-10-13
Source: `request_tracker_utils/config.py`

| Variable          | Type         | Default                                                                                    | Required | Sensitive | Description                                                | Notes                                                                  |
| ----------------- | ------------ | ------------------------------------------------------------------------------------------ | -------- | --------- | ---------------------------------------------------------- | ---------------------------------------------------------------------- |
| `RT_TOKEN`        | string       | `"default-token-if-not-set"`                                                               | Yes\*    | Yes       | Authentication token for Request Tracker API requests.     | Application should fail fast; add explicit validation in future tasks. |
| `WORKING_DIR`     | path         | Platform-specific (`~/.rtutils` on macOS/other, `/var/lib/request-tracker-utils` on Linux) | No       | No        | Filesystem workspace for SQLite DB, logs, and cache files. | Automatically coerced to absolute path when provided.                  |
| `RT_URL`          | string (URL) | `"https://tickets.wc-12.com"`                                                              | No       | No        | Base URL for the Request Tracker instance.                 | Update per environment (dev/staging/prod).                             |
| `LABEL_WIDTH_MM`  | int          | `100`                                                                                      | No       | No        | Label width in millimeters for PDF generation.             | Works with default label stock; adjust for new printer media.          |
| `LABEL_HEIGHT_MM` | int          | `62`                                                                                       | No       | No        | Label height in millimeters.                               | Keep in sync with label template assets.                               |
| `PREFIX`          | string       | `"W12-"`                                                                                   | No       | No        | Prefix prepended to generated asset tags.                  | Ensure matches district naming convention.                             |
| `PADDING`         | int          | `4`                                                                                        | No       | No        | Millimeter padding around label contents.                  | Impacts barcode/QR readability.                                        |
| `PORT`            | int          | `8080`                                                                                     | No       | No        | HTTP port for Flask development server.                    | Systemd service may override; document in deployment module.           |
| `RT_CATALOG`      | string       | `"General assets"`                                                                         | No       | No        | Default RT asset catalog used for queries/creation.        | Set per-institution to avoid cross-team collisions.                    |

\* While `RT_TOKEN` provides a placeholder default in code, production environments must set a real secret. Tasks in later phases will introduce startup validation to enforce this requirement.
