# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Run Commands
```bash

# Run the application
nix run

# Development environment
devenv shell
# OR
nix develop
```

## Lint/Test Commands
No formal linting or testing configuration has been established.

## Code Style Guidelines
- **Naming**: Use snake_case for all variables, functions, and modules
- **Imports**: Order by stdlib → third-party → local imports, grouped by source
- **Flask Patterns**: Use Blueprint pattern for routes organization
- **Error Handling**: Try/except blocks with descriptive error messages
- **API Responses**: Return proper HTTP status codes (400/500) and JSON responses
- **Documentation**: Use docstrings for functions with parameters and returns
- **Configuration**: Use environment variables with sensible defaults via python-dotenv

## Project Structure
RequestTrackerUtils is a Flask application for managing RT (Request Tracker) asset tags and labels with PDF generation capabilities. The codebase follows modular organization with routes, utils, and templates directories.
