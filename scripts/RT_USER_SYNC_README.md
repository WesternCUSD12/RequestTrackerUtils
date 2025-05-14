# RT User Custom Fields Sync

This feature allows syncing student data from the student information system database to RT user custom fields.

## Overview

The scripts in this feature update two custom fields in RT users:

- **Grade** - Updates the user's grade level from the student database
- **Student ID** - Updates the user's student ID from the student database

These custom fields must be created in RT before using these scripts.

## Prerequisites

1. RT (Request Tracker) must have custom fields created for users:

   - A field for storing the student's grade (usually named "Grade")
   - A field for storing the student ID (usually named "Student ID")

2. Students in the database must have an RT user ID assigned in the `rt_user_id` field

## Usage

### Manual Sync

Run the script manually to sync student data to RT:

```bash
# Run a dry run first (no changes made)
./scripts/update_rt_user_custom_fields.py --dry-run

# Run the actual sync
./scripts/update_rt_user_custom_fields.py

# Run with slower rate limiting (for overloaded RT servers)
./scripts/update_rt_user_custom_fields.py --rate-limit 1.0

# Run in batches (process 50 students, pause, then continue)
./scripts/update_rt_user_custom_fields.py --batch-size 50 --batch-delay 10
```

### Scheduled Sync

Set up a cron job to run the sync automatically:

```bash
# Edit crontab
crontab -e

# Add a line to run the sync daily at 1:00 AM
0 1 * * * /path/to/rtutils/scripts/sync_rt_users.sh >> /path/to/logdir/rt_sync_cron.log 2>&1
```

## Troubleshooting

### Common Issues

1. **Missing Custom Fields**

   - Ensure that the RT installation has the necessary custom fields created for users
   - The script will log an error if it can't find the proper custom fields

2. **Authentication Failures**

   - Check that the RT token in the environment variables or config is valid
   - Ensure the token has permissions to update user records

3. **Missing RT User IDs**

   - Students without an RT user ID will be skipped
   - Check that students have the `rt_user_id` field populated in the database

4. **RT Server Overloaded**
   - If the RT server returns 500 errors, the script will retry with backoff
   - Use `--rate-limit` option to slow down API calls (e.g., `--rate-limit 1.0` for 1 second between calls)
   - Use `--batch-size` and `--batch-delay` to process users in smaller groups with pauses

## Logging

Logs are written to the following locations:

- Manual sync: Standard output (can be redirected)
- Scheduled sync: `~/.rtutils/logs/rt_user_sync_YYYY-MM-DD.log`
