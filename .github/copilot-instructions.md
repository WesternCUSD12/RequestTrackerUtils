# rtutils Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-05

## Development Environment
**Setup**: Python 3.11+ via devenv (NixOS flake-based environment)  
**Package Manager**: uv (fast Python package installer)  
**Shell**: Fish shell (not bash/zsh)
**Command Prefix**: ALL Python commands must use `uv run python ...`

⚠️ IMPORTANT: Running Python directly will fail with ModuleNotFoundError. Always prefix with `uv run python`.

**Fish Shell Notes**: 
- Use `&&` to chain commands (same as bash)
- **CRITICAL: NEVER use heredocs** (`<< 'EOF'`, `<< EOF`) - they do NOT work in Fish and will always fail
  - Use `printf`, `echo`, or pipes instead
  - For multi-line Python: use `uv run python -c "..."` with proper escaping, or write to temp file
  - For shell scripts: chain commands with `&&` or write to script file
- Variable syntax: `$var` (automatic, arrays default to multi-element)

## Active Technologies
- Python 3.11+ + Django 4.2 LTS, django-import-export 4.3.14, requests, SQLite3 (007-unified-student-data)
- Python 3.11+ + Flask 2.2+, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+ (001-i-need-to)
- Python 3.11+ + Flask 2.2+, ReportLab 3.6+ (PDF generation), qrcode 7.3+, python-barcode 0.13+, Pillow (image manipulation) (003-rtutils-should-offer)
- File-based templates and CSS; existing SQLite database for asset metadata (no schema changes required) (003-rtutils-should-offer)

## Project Structure
```
apps/                    # Django apps (students, audit, devices, etc.)
tests/                   # Test suite (unit/ and integration/)
templates/               # Django templates
specs/                   # Feature specifications (007-unified-student-data, etc.)
rtutils/                 # Django project settings
```

## Commands
- **Django Management**: `uv run python manage.py [command]`
- **Run Tests**: `uv run pytest` or `uv run pytest tests/unit/`
- **Run Development Server**: `uv run python manage.py runserver`
- **Lint Code**: `uv run ruff check .`
- **Format Code**: `uv run ruff format .`
- **Create Migrations**: `uv run python manage.py makemigrations`
- **Apply Migrations**: `uv run python manage.py migrate`
- **Django Shell**: `uv run python manage.py shell`

## Code Style
- Python 3.11+: Follow standard conventions
- Use type hints where practical
- Follow Django conventions (models in models.py, views in views.py, etc.)
- Run `uv run ruff check .` before committing

## Recent Changes
- 003-rtutils-should-offer: Added Python 3.11+ + Flask 2.2+, ReportLab 3.6+ (PDF generation), qrcode 7.3+, python-barcode 0.13+, Pillow (image manipulation)
- 001-i-need-to: Added Python 3.11+ + Flask 2.2+, requests 2.28+, reportlab 3.6+, qrcode 7.3+, python-barcode 0.13+

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
