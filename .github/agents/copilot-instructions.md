# RequestTrackerUtils Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-01

## Active Technologies
- Python 3.11+ + Django 4.2 LTS, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+, Pillow, WhiteNoise (005-django-refactor)
- SQLite3 (new database at `{WORKING_DIR}/database.sqlite`), managed via Django ORM (005-django-refactor)
- Python 3.11+ (existing project standard) + Django 4.2 LTS, google-auth 2.x, google-auth-oauthlib 1.x, google-auth-httplib2 0.x (006-google-auth)
- SQLite3 (existing `database.sqlite`) - extend User model with google_user_id and user_role fields (006-google-auth)
- Python 3.11+ + Django 4.2 LTS, python-ldap (for LDAPS connectivity) (006-ldap-auth)
- SQLite3 (existing), Django session backend (006-ldap-auth)
- Python 3.11+ + Django 4.2 LTS, django-import-export (CSV import/export in admin) (007-unified-student-data)
- SQLite3 (database.sqlite via Django ORM) (007-unified-student-data)

- Python 3.11+ + Django 4.2 LTS, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+, Pillow (005-django-refactor)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 007-unified-student-data: Added Python 3.11+ + Django 4.2 LTS, django-import-export (CSV import/export in admin)
- 006-ldap-auth: Added Python 3.11+ + Django 4.2 LTS, python-ldap (for LDAPS connectivity)
- 006-google-auth: Added Python 3.11+ (existing project standard) + Django 4.2 LTS, google-auth 2.x, google-auth-oauthlib 1.x, google-auth-httplib2 0.x


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
