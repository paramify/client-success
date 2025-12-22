# Paramify Evidence Manager

A Python CLI tool for managing evidence records in the Paramify compliance and audit management system. Supports bulk imports from CSV, JSON, and Excel files, as well as interactive menu-driven operations.

## Features

- **Multiple Input Formats**: Import evidence from CSV, JSON, or Excel (.xlsx/.xls) files
- **Interactive Menu**: Full-featured CLI menu for all evidence operations
- **Bulk Operations**: Create multiple evidence records with progress tracking
- **Edit Evidence**: Update existing evidence records
- **Export Data**: Export all evidence to CSV or JSON for backup/migration
- **Duplicate Detection**: Automatic detection of duplicate evidence by name or reference ID
- **Dry Run Mode**: Preview operations before committing changes
- **Connection Validation**: Validates API credentials on startup
- **Colored Output**: Clear visual feedback with colored success/error messages
- **Progress Bar**: Visual progress indicator for bulk operations

## Prerequisites

- Python 3.10+
- Access to Paramify API
- Valid API credentials (API key)

## Quick Start

1. **Run the menu**:
   ```bash
   ./menu.command
   ```
   The script will automatically:
   - Create a virtual environment if needed
   - Install all dependencies
   - Prompt for your API key if not configured

2. **That's it!** The tool validates your connection and you're ready to go.

## Manual Installation (Optional)

If you prefer to set up manually:

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   Create a `.env` file in the project root:
   ```env
   PARAMIFY_API_URL=https://app.paramify.com/api/v0
   PARAMIFY_API_KEY=your_api_key_here
   ```

## Usage

### Interactive Menu

The interactive menu provides a user-friendly interface for all operations:

```bash
./menu.command
# or
python menu.py
```

**Menu Options:**
1. List All Evidence - Display all evidence records
2. Create Evidence (Bulk) - Import from CSV/JSON/Excel file with progress bar
3. Create Evidence (Single) - Create one record interactively
4. Search Evidence - Search by name or reference ID
5. View Evidence Details - View detailed information
6. **Edit Evidence** - Update existing evidence records
7. Delete Evidence - Remove an evidence record
8. **Export Evidence** - Export to CSV or JSON
9. Settings - Manage API configuration & test connection

### Command-Line Interface

#### Import from File

```bash
# CSV file
python main.py --file evidence.csv

# JSON file
python main.py --file evidence.json

# Excel file
python main.py --file evidence.xlsx

# Dry run (preview without creating)
python main.py --file evidence.csv --dry-run

# Verbose output
python main.py --file evidence.csv --verbose

# Skip duplicate checking (faster for large imports)
python main.py --file evidence.csv --no-duplicate-check

# Allow duplicates to be created
python main.py --file evidence.csv --allow-duplicates

# Disable progress bar
python main.py --file evidence.csv --no-progress
```

#### Export Evidence

```bash
# Export to CSV
python main.py --export backup.csv

# Export to JSON
python main.py --export backup.json
```

#### Create Single Record

```bash
# Basic creation
python main.py --name "User Access Review" --description "Quarterly access review"

# With all fields
python main.py \
  --name "User Access Review" \
  --referenceId "EVD-001" \
  --description "Quarterly user access review for Q1 2024" \
  --instructions "Export user list from IAM system" \
  --remarks "Review completed by Security Team" \
  --automated

# Short flags
python main.py -n "Evidence Name" -r "REF-001" -d "Description" -i "Instructions"
```

#### List All Evidence

```bash
python get_evidence.py
```

### CLI Options

| Flag | Short | Description |
|------|-------|-------------|
| `--file` | `-f` | Path to CSV, JSON, or Excel file |
| `--export` | `-e` | Export all evidence to file (CSV or JSON) |
| `--name` | `-n` | Evidence name (required for single record) |
| `--reference-id` | `-r` | Custom reference identifier |
| `--description` | `-d` | Evidence description |
| `--instructions` | `-i` | Instructions for gathering evidence |
| `--remarks` | | Additional remarks/notes |
| `--automated` | `-a` | Mark as automated evidence |
| `--dry-run` | | Preview without creating records |
| `--verbose` | `-v` | Enable verbose output |
| `--no-duplicate-check` | | Skip duplicate detection |
| `--allow-duplicates` | | Create records even if duplicates exist |
| `--no-progress` | | Disable progress bar |

## File Formats

### CSV Format

```csv
name,referenceId,description,instructions,remarks,automated
User Access Review,EVD-001,Quarterly review,Export from IAM,Security Team,true
Security Policy Update,EVD-002,Annual policy review,Review documentation,Compliance Team,false
```

### JSON Format

Single object or array of objects:

```json
[
  {
    "name": "User Access Review",
    "referenceId": "EVD-001",
    "description": "Quarterly user access review",
    "instructions": "Export user list from IAM system",
    "remarks": "Reviewed by Security Team",
    "automated": true
  },
  {
    "name": "Security Policy Update",
    "referenceId": "EVD-002",
    "description": "Annual security policy review",
    "instructions": "Review and update security documentation",
    "automated": false
  }
]
```

### Excel Format

Same column structure as CSV. Supports `.xlsx` and `.xls` formats.

## Evidence Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the evidence record |
| `referenceId` | No | Custom reference identifier for tracking |
| `description` | No | Detailed description of the evidence |
| `instructions` | No | Instructions for gathering or reviewing evidence |
| `remarks`/`notes` | No | Additional remarks or notes |
| `automated` | No | Boolean flag indicating automated evidence collection |

## API Configuration

The tool connects to the Paramify API using credentials stored in the `.env` file:

- **PARAMIFY_API_URL**: Base URL for the Paramify API (e.g., `https://app.paramify.com/api/v0`)
- **PARAMIFY_API_KEY**: Your API authentication key

You can also update these settings through the interactive menu (Option 9: Settings).

## Project Structure

```
evidence-manager/
├── paramify_client.py   # Shared API client module
├── main.py              # CLI tool for bulk operations & export
├── menu.py              # Interactive CLI menu interface
├── get_evidence.py      # Simple utility to list all evidence
├── menu.command         # Bash script to launch the menu (auto-setup)
├── requirements.txt     # Python dependencies
├── .env                 # Environment configuration (API credentials)
├── .gitignore           # Git ignore configuration
├── example.json         # Sample JSON evidence data
├── example.csv          # Sample CSV evidence data
├── README.md            # This file
└── CLAUDE.md            # AI assistant context file
```

## Dependencies

- `requests>=2.31.0` - HTTP client for API calls
- `pandas>=2.0.0` - Data manipulation and Excel file support
- `openpyxl>=3.1.0` - Excel file reading
- `python-dotenv>=1.0.0` - Environment variable management

## Error Handling

The tool provides detailed error messages with colored output:

- **Green**: Success messages
- **Yellow**: Warnings (e.g., skipped duplicates)
- **Red**: Errors

Common issues:
- **Connection failed**: Check your API key and network connectivity
- **Invalid file format**: Ensure file extension matches content type
- **Duplicate evidence**: Use `--allow-duplicates` to override

## Examples

Example data files are included to help you get started:

- `example.csv` - Sample CSV format with 4 evidence records
- `example.json` - Sample JSON format with 3 evidence records

Test with dry run:
```bash
python main.py --file example.csv --dry-run --verbose
```

Export your evidence for backup:
```bash
python main.py --export evidence_backup.json
```

## License

Internal tool for Paramify evidence management.
