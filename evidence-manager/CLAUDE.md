# CLAUDE.md - AI Assistant Context

This file provides context for AI assistants (like Claude) working with this codebase.

## Project Overview

**Paramify Evidence Manager** is a Python CLI tool for managing evidence records in the Paramify compliance/audit management platform. It provides multiple interfaces (CLI, interactive menu, utility scripts) for creating, listing, searching, editing, exporting, and deleting evidence records.

## Tech Stack

- **Language**: Python 3.10+
- **HTTP Client**: `requests` library with retry logic
- **Data Processing**: `pandas` for Excel/CSV handling
- **Configuration**: `python-dotenv` for environment variables
- **Excel Support**: `openpyxl`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
├──────────────┬───────────────────┬──────────────────────────┤
│   main.py    │     menu.py       │    get_evidence.py       │
│  (CLI args)  │ (Interactive)     │    (List utility)        │
├──────────────┴───────────────────┴──────────────────────────┤
│                  paramify_client.py                          │
│            (Shared API Client & Utilities)                   │
├─────────────────────────────────────────────────────────────┤
│                    Paramify Cloud API                        │
│              /api/v0/evidence endpoints                      │
└─────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `paramify_client.py` | **Core module** - API client, utilities, colored output, progress bar |
| `main.py` | CLI tool - bulk import, single create, export |
| `menu.py` | Interactive menu - full CRUD + export operations |
| `get_evidence.py` | Simple utility to list all evidence records |
| `menu.command` | Bash launcher with auto-setup (venv, deps, API key prompt) |

## ParamifyClient Class

The `paramify_client.py` module contains the `ParamifyClient` class with these key methods:

```python
# Connection & Config
client.validate_config()     # Raises ValidationError if not configured
client.test_connection()     # Tests API connectivity

# CRUD Operations
client.get_all_evidence()    # List all evidence
client.get_evidence(id)      # Get single evidence
client.create_evidence(data) # Create new evidence
client.update_evidence(id, data)  # Update existing (PATCH)
client.delete_evidence(id)   # Delete evidence

# Bulk Operations
client.create_evidence_bulk(list, check_duplicates=True, progress_callback=fn)

# Export
client.export_to_csv(path)   # Export to CSV
client.export_to_json(path)  # Export to JSON

# Utilities
client.check_duplicate(data, existing)  # Check for duplicates
client.clear_cache()         # Clear evidence cache
```

## Utility Functions (paramify_client.py)

```python
# Colored output
success(msg)   # Green text
error(msg)     # Red text
warning(msg)   # Yellow text
info(msg)      # Cyan text
bold(msg)      # Bold text

# Data handling
normalize_keys(dict)         # Lowercase all keys
get_reference_id(data)       # Extract referenceId
get_field_value(data, *keys) # Get first non-empty value

# File reading
read_evidence_file(path)     # Auto-detect format (CSV/JSON/Excel)
read_csv_file(path)
read_json_file(path)
read_excel_file(path)

# Progress tracking
ProgressBar(total, prefix)   # Progress bar for bulk ops
```

## Custom Exceptions

```python
APIError(message, status_code, response_text)  # API failures
ValidationError(message)                        # Validation failures
DuplicateError(message, existing_evidence)      # Duplicate detection
```

## API Integration

**Base URL**: Configured via `PARAMIFY_API_URL` in `.env`

**Authentication**: Bearer token via `PARAMIFY_API_KEY`

**Endpoints Used**:
- `GET /evidence` - List all evidence
- `POST /evidence` - Create evidence record
- `GET /evidence/{id}` - Get single evidence
- `PATCH /evidence/{id}` - Update evidence record
- `DELETE /evidence/{id}` - Delete evidence

**Features**:
- Automatic retry with exponential backoff (3 retries)
- 30-second timeout
- Connection validation on startup

## Common Development Tasks

### Running the Project

```bash
# Activate virtual environment
source venv/bin/activate

# Interactive menu
python menu.py

# CLI with file
python main.py --file data.csv

# Export evidence
python main.py --export backup.json

# List all evidence
python get_evidence.py
```

### Testing Changes

```bash
# Dry run to test without creating records
python main.py --file example.csv --dry-run --verbose
```

### Adding New Features

1. Add API method to `ParamifyClient` class in `paramify_client.py`
2. Update CLI args in `main.py` if needed
3. Add menu option in `menu.py` if needed
4. Update documentation

## Code Patterns

### Using the Client

```python
from paramify_client import ParamifyClient, APIError, ValidationError

client = ParamifyClient()

try:
    client.validate_config()
    client.test_connection()
    evidence = client.get_all_evidence()
except ValidationError as e:
    print(f"Config error: {e}")
except APIError as e:
    print(f"API error: {e}")
```

### Colored Output

```python
from paramify_client import success, error, warning, info, bold

print(success("Operation completed!"))  # Green
print(error("Something went wrong"))    # Red
print(warning("Skipped duplicate"))     # Yellow
print(info("Processing..."))            # Cyan
print(bold("Important"))                # Bold
```

### Progress Bar

```python
from paramify_client import ProgressBar, ProgressInfo

progress = ProgressBar(total=100, prefix="Creating")

def callback(info: ProgressInfo):
    progress.update(info)

client.create_evidence_bulk(items, progress_callback=callback)
```

## Environment Configuration

Required `.env` variables:
```env
PARAMIFY_API_URL=https://app.paramify.com/api/v0
PARAMIFY_API_KEY=<your-api-key>
```

## Menu Options (menu.py)

1. List All Evidence
2. Create Evidence (Bulk from File)
3. Create Evidence (Single Entry)
4. Search Evidence
5. View Evidence Details
6. **Edit Evidence** (NEW)
7. Delete Evidence
8. **Export Evidence** (NEW)
9. Settings

## CLI Flags (main.py)

```
--file, -f          Input file path (CSV/JSON/Excel)
--export, -e        Export to file (CSV/JSON)
--name, -n          Evidence name
--reference-id, -r  Reference ID
--description, -d   Description
--instructions, -i  Instructions
--remarks           Remarks/notes
--automated, -a     Automated flag
--dry-run           Preview mode
--verbose, -v       Verbose output
--no-duplicate-check  Skip duplicate detection
--allow-duplicates    Allow creating duplicates
--no-progress       Disable progress bar
```

## Recent Improvements

1. **Shared API Module**: All API logic centralized in `paramify_client.py`
2. **Connection Validation**: Validates credentials on startup
3. **Progress Bar**: Visual progress for bulk operations
4. **Colored Output**: Success/error/warning messages are color-coded
5. **Export Functionality**: Export evidence to CSV or JSON
6. **Edit Evidence**: Update existing records via menu or API
7. **Retry Logic**: Automatic retry with backoff for transient failures
8. **Custom Exceptions**: `APIError`, `ValidationError`, `DuplicateError`
