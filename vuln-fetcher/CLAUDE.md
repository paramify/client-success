# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python CLI tool that imports vulnerability scan results into Paramify assessments from two sources:
1. **Live Nessus scans** - Direct API connection to Nessus instance
2. **GitHub repositories** - Searches for .nessus or .csv files in repos

Designed for user-friendliness with interactive menus and numbered selection (not requiring users to know IDs).

## Quick Commands

### Running the Tool
```bash
# Interactive menu (recommended)
./run.sh

# Direct commands
./run.sh import              # Import from Nessus
./run.sh import-github       # Import from GitHub
./run.sh list-scans          # List Nessus scans
./run.sh list-assessments    # List Paramify assessments
```

### Development Setup
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with actual credentials
```

### Testing Connections
```bash
source venv/bin/activate
python main.py list-scans
python main.py list-assessments
```

## Architecture

### Client-Based Design

Modular separation of concerns with dedicated API clients:

```
main.py                  # CLI interface with unified menu
├── integration.py       # Orchestrates workflows
│   ├── nessus_client.py    # Nessus API interactions
│   ├── paramify_client.py  # Paramify API interactions
│   └── github_client.py    # GitHub API interactions
└── config.py            # Environment-based configuration
```

### Key Classes

**NessusClient** ([nessus_client.py](nessus_client.py))
- Authenticates with `X-ApiKeys` header (accessKey + secretKey)
- Handles async scan export workflow: request → poll status → download
- Disables SSL verification for self-signed certs
- Key method: `get_scan_export(scan_id)` - full export workflow

**ParamifyClient** ([paramify_client.py](paramify_client.py))
- Authenticates with Bearer token
- Lists assessments and uploads intake files
- **Critical**: Sets proper MIME types based on file extension
- Key method: `upload_intake(assessment_id, file_content, filename, artifact_data)`

**GitHubClient** ([github_client.py](github_client.py))
- Works with public and private repos (optional token)
- Recursively searches for .nessus and .csv files
- Parses GitHub URLs with encoded paths (demo%20evidence)
- Key method: `find_scan_files(owner, repo, path, ref)`

**NessusParamifyIntegration** ([integration.py](integration.py))
- Orchestrates complete import workflow
- Combines Nessus and Paramify clients
- Pipeline: fetch → export → download → upload

## Critical Implementation Details

### MIME Type Handling (DO NOT CHANGE!)

The Paramify API **requires** proper MIME types or uploads fail with 400 errors:

```python
# paramify_client.py:88-96
content_type = 'application/octet-stream'
if filename.lower().endswith('.csv'):
    content_type = 'text/csv'          # Required for CSV
elif filename.lower().endswith('.json'):
    content_type = 'application/json'
elif filename.lower().endswith('.xml'):
    content_type = 'application/xml'
elif filename.lower().endswith('.nessus'):
    content_type = 'application/xml'   # .nessus files are XML
```

**Never remove this logic** - API rejects files without proper content-type.

### Effective Date Handling (CRITICAL!)

The `effectiveDate` **must** be inside the artifact JSON object, NOT as form data:

```python
# CORRECT - Inside artifact JSON
artifact_data = {}
if effective_date:
    artifact_data['effectiveDate'] = effective_date

files = {
    'file': (filename, file_content, content_type),
    'artifact': ('artifact.json', artifact_json_bytes, 'application/json')
}
```

If passed as separate form data, the API silently ignores it and uses today's date.

### Multipart Upload Format

Paramify intake endpoint requires multipart/form-data with two parts:
- `file`: The scan file with proper MIME type
- `artifact`: JSON metadata (application/json) containing effectiveDate

Both parts are required.

### Authentication Methods

- **Paramify**: Bearer token in Authorization header
- **Nessus**: X-ApiKeys header with `accessKey=XXX; secretKey=YYY`
- **GitHub**: Optional Bearer token (private repos or higher rate limits)

### Nessus Export Workflow

Exporting is asynchronous:
1. POST `/scans/{id}/export` with format
2. Poll GET `/scans/{id}/export/{file_id}/status` until ready
3. GET `/scans/{id}/export/{file_id}/download`

The [nessus_client.py](nessus_client.py):101 `get_scan_export()` handles this automatically.

### GitHub URL Parsing

Supports multiple formats:
- `owner/repo` - searches entire repo
- `https://github.com/owner/repo`
- `https://github.com/owner/repo/tree/branch/path` - specific path

URL decoding handles spaces: `demo%20evidence` → `demo evidence`

## Design Patterns

### Interactive CLI with Numbered Selection

Users select by row number, not IDs:

```python
# Example from main.py:156
print(f"{idx + 1:<4} {scan['id']:<8} {scan_name:<40} {status_display}")
# User enters 1, 2, 3... not the actual scan ID
```

Used throughout for:
- Selecting Nessus scans
- Selecting Paramify assessments
- Selecting GitHub files

### Configuration via .env

All credentials in `.env` (not committed):

```
PARAMIFY_API_KEY=...
PARAMIFY_BASE_URL=https://stage.paramify.com/api/v0
NESSUS_URL=https://localhost:8834
NESSUS_ACCESS_KEY=...
NESSUS_SECRET_KEY=...
GITHUB_TOKEN=...  # Optional
```

[config.py](config.py) validates required fields on startup.

## Common Issues

### SSL Certificate Verification Failed
Already handled - SSL verification disabled in [nessus_client.py](nessus_client.py):30 for self-signed certs.

### 400 Bad Request on CSV Upload
**Cause**: Missing/incorrect MIME type
**Solution**: Already fixed in [paramify_client.py](paramify_client.py):88 - **DO NOT REMOVE**

### Paramify API Response Format
API returns `{'assessments': [...]}` not direct list.
Already handled in [paramify_client.py](paramify_client.py):60

### Effective Date Not Applied
**Cause**: effectiveDate as form data instead of in artifact JSON
**Solution**: Already fixed in [paramify_client.py](paramify_client.py):127-130 - **DO NOT CHANGE**

### GitHub Files Not Found
Check:
1. Repository is public (or GITHUB_TOKEN provided)
2. Branch name correct (default: 'main')
3. Path is correct
4. File extensions case-insensitive

## Testing

### Test Nessus Connection
```bash
./run.sh list-scans
```
Should show list of scans.

### Test Paramify Connection
```bash
./run.sh list-assessments
```
Should show assessments.

### Test GitHub Import (Public Repo)
```bash
./run.sh import-github
# Enter: https://github.com/paramify/demo/tree/main/demo%20evidence
# Select file, assessment, confirm
```
Expected: Success message with artifact ID

### Test Full Nessus Import
```bash
./run.sh import
# Select scan, assessment, set date, confirm
```
Expected: Success message with artifact ID and filename

## Extension Points

### Adding New Import Sources
1. Create new client file (e.g., `s3_client.py`)
2. Add option to [main.py](main.py):334 `unified_menu()`
3. Add interactive function (follow `import_from_github_interactive()` pattern)

### Adding New File Types
1. [github_client.py](github_client.py):129 - modify `file_types` list
2. [paramify_client.py](paramify_client.py):88 - add MIME type detection

### Modifying API Endpoints
- Nessus: [nessus_client.py](nessus_client.py):19 `base_url`
- Paramify: [paramify_client.py](paramify_client.py):15 `base_url` (from config)
- GitHub: [github_client.py](github_client.py):23 `base_url`

## Environment Variables

**Required:**
- `PARAMIFY_API_KEY` - Paramify API token
- `PARAMIFY_BASE_URL` - Usually https://stage.paramify.com/api/v0
- `NESSUS_URL` - Nessus instance URL
- `NESSUS_ACCESS_KEY` - Nessus API access key
- `NESSUS_SECRET_KEY` - Nessus API secret key

**Optional:**
- `GITHUB_TOKEN` - GitHub PAT (for private repos)

## Dependencies

From [requirements.txt](requirements.txt):
- `requests` - HTTP client for all API interactions
- `python-dotenv` - Load environment from .env
- `urllib3` - HTTP library (SSL warning suppression)

## Workflow Diagrams

### Nessus Import
```
User selects scan → NessusClient.get_scan_export()
  ↓
Request export → Poll for ready → Download file
  ↓
ParamifyClient.upload_intake() → Success/Error
```

### GitHub Import
```
User enters repo URL → GitHubClient.parse_github_url()
  ↓
GitHubClient.find_scan_files() → User selects file
  ↓
GitHubClient.download_file_direct() → ParamifyClient.upload_intake()
```

## Critical Rules for Development

1. **Preserve MIME type detection** - Critical for Paramify uploads
2. **Never move effectiveDate to form data** - Must stay in artifact JSON
3. **Follow numbered selection pattern** - Users select by number, not ID
4. **Keep clients separate** - Don't mix API concerns
5. **Validate config early** - Use `Config.validate()` on startup

## Security

- `.env` excluded from git (in `.gitignore`)
- SSL verification disabled for Nessus (self-signed certs)
- GitHub token optional but recommended for private repos
- All API keys should be rotated regularly

## Success Criteria

A working import must:
1. Connect to source without errors
2. Display selectable list of scans/files
3. Show confirmation summary before import
4. Upload successfully to Paramify
5. Return artifact ID on success
6. Display clear error messages on failure

## Documentation Structure

- **[README.md](README.md)** - User documentation (installation, usage, troubleshooting)
- **[CLAUDE.md](CLAUDE.md)** - Developer documentation (this file)

## External Resources

- Nessus API: https://developer.tenable.com/docs/nessus-api
- GitHub API: https://docs.github.com/en/rest
