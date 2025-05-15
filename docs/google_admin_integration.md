# Google Workspace Admin and Chromebook Integration Guide

This guide explains how to set up and configure the integration between Google Workspace Admin Console for Chromebooks and Request Tracker (RT).

## Overview

This integration syncs Chromebook information between Google Workspace Admin Console and RT by:

1. Fetching Chromebook details (serial numbers, MAC addresses) from Google Admin Console
2. Matching these devices with assets in RT
3. Writing back device names and current user information as "annotated user" in Google Workspace

## Prerequisites

- Google Workspace with Admin privileges
- Google Cloud Console project with the Admin SDK API enabled
- A service account with domain-wide delegation
- Request Tracker (RT) with asset tracking capabilities
- Python 3.11+

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Admin SDK API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Admin SDK API" and enable it

## Step 2: Create a Service Account

1. Navigate to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Name it something descriptive like "chromebook-sync"
4. Grant it no project roles (we'll use domain-wide delegation instead)
5. Create and download the JSON key file
6. Save this file securely and note its location

## Step 3: Set Up Domain-Wide Delegation

1. Go to your [Google Admin Console](https://admin.google.com)
2. Navigate to Security > API controls > Domain-wide Delegation
3. Click "Add new" and enter:
   - Client ID: The service account client ID (from the JSON file)
   - OAuth scopes: `https://www.googleapis.com/auth/admin.directory.device.chromeos`
4. Click "Authorize"

## Step 4: Configure Environment Variables

1. Create or update your `.env` file in the project root directory with the following variables:

```
# Google Workspace Configuration
GOOGLE_ADMIN_DOMAIN=yourdomain.com
GOOGLE_ADMIN_SUBJECT=admin@yourdomain.com
GOOGLE_CREDENTIALS_FILE=/path/to/service-account-credentials.json
GOOGLE_API_RATE_LIMIT=0.5
```

Notes:

- `GOOGLE_ADMIN_DOMAIN` is your primary Google Workspace domain
- `GOOGLE_ADMIN_SUBJECT` must be an admin account email in your domain
- `GOOGLE_CREDENTIALS_FILE` should be the absolute path to the JSON key file you downloaded
- `GOOGLE_API_RATE_LIMIT` controls the delay between API calls (in seconds)

## Step 5: Test the Integration

1. Run the sync script in dry-run mode to verify it works without making changes:

```bash
cd /Users/jmartin/rtutils
python scripts/sync_chromebook_data.py --dry-run --verbose
```

2. Review the log output to ensure:
   - The script can connect to Google Admin API
   - Chromebook devices are being retrieved correctly
   - The script can find matching assets in RT
   - The proposed updates look correct

## Step 6: Run an Actual Sync

After verifying everything works correctly in dry-run mode:

```bash
cd /Users/jmartin/rtutils
python scripts/sync_chromebook_data.py --org-unit="/Devices/Chromebooks" --max-results=1000
```

Options:

- `--org-unit`: Specify the Google Admin organizational unit to filter devices
- `--max-results`: Limit the number of devices processed
- `--batch-size`: Control how many devices are updated in each batch
- `--rate-limit`: Adjust the delay between API calls

## Step 7: Set Up Scheduled Execution

1. Make the fish shell script executable:

```bash
chmod +x /Users/jmartin/rtutils/scripts/scheduled_chromebook_sync.fish
```

2. Configure a cron job to run the script at your preferred frequency:

```bash
crontab -e
```

Add a line like:

```
0 5 * * * /Users/jmartin/rtutils/scripts/scheduled_chromebook_sync.fish
```

This runs the script at 5:00 AM every day.

## Troubleshooting

### Common Issues:

1. **Authentication errors**:

   - Verify the service account credentials file exists and is valid
   - Ensure domain-wide delegation is set up correctly
   - Check that the GOOGLE_ADMIN_SUBJECT is an admin user

2. **No devices found**:

   - Verify the organization unit path is correct
   - Check that the account has permissions to view devices

3. **Rate limiting**:

   - Increase the GOOGLE_API_RATE_LIMIT if you're hitting quota limits

4. **No matching assets**:
   - Verify serial numbers or MAC addresses match between systems
   - Use the --verbose flag to see more details about matching attempts

### Logs:

Logs are saved in the following locations:

- Script logs: `instance/logs/chromebook_sync_YYYYMMDD_HHMMSS.log`
- Scheduled job logs: `instance/logs/chromebook_sync_YYYY-MM-DD.log`

## Security Considerations

1. The service account credentials file contains sensitive information
2. Store it securely and restrict access permissions
3. Don't check the credentials file into version control
4. Use the least privilege principle - only grant the OAuth scopes needed

## Additional Notes

- The integration matches devices first by serial number, then by MAC address
- Only devices that match existing RT assets will be updated
- In batch mode, failures with individual devices won't stop the entire sync
- Updates are made individually for each field to minimize impact of errors
