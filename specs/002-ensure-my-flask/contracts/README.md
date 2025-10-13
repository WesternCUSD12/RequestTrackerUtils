# Module Interface Contracts

This directory defines the interface contracts and standards for Flask application components.

## Contents

- **docstring_standard.md** - Google-style docstring format and examples
- **blueprint_interface.md** - Blueprint structure and registration contract
- **utility_module_interface.md** - Utility module structure and export contract
- **error_handling_contract.md** - Error handling patterns and standards
- **logging_contract.md** - Logging format and level guidelines

## Purpose

These contracts ensure consistency across all modules and provide clear guidelines for:

- How to document code (docstrings, inline comments)
- How to structure modules (exports, dependencies)
- How to handle errors (try/catch, status codes)
- How to log operations (format, levels, context)

## Usage

When creating or modifying Flask application code:

1. Reference the appropriate contract for guidance
2. Follow examples provided in each contract
3. Validate against success criteria in spec.md
4. Use static analysis tools to verify compliance

## Validation Tools

- `pydocstyle` - Docstring style validation
- `pylint` / `flake8` - PEP 8 and import organization
- `import-linter` - Circular dependency detection
- Custom scripts in `.specify/scripts/` for contract validation
