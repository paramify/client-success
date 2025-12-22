# Paramify Assessment Integration

A Python CLI tool that imports Nessus vulnerability scan results into Paramify assessments from multiple sources: live Nessus instances or GitHub repositories.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Getting API Credentials](#getting-api-credentials)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Security Notes](#security-notes)
- [Developer Documentation](#developer-documentation)

## Overview

This tool allows you to:
- **Import from Nessus**: Connect directly to Nessus to export and import scan results
- **Import from GitHub**: Pull `.nessus` or `.csv` files from GitHub repositories
- **List Resources**: View available scans (Nessus) and assessments (Paramify)
- **Set Effective Dates**: Specify when the scan data should be effective in Paramify
- **Automate Workflows**: Streamline vulnerability assessment processes

## Features

- **Interactive CLI**: User-friendly menu system with numbered selections
- **Multiple Import Sources**: Nessus API or GitHub repositories
- **Flexible File Support**: `.nessus` and `.csv` file formats
- **Public & Private Repos**: Works with both public and private GitHub repositories
- **Effective Date Control**: Set custom effective dates for imported data
- **Comprehensive Error Handling**: Clear error messages and validation
- **Environment-Based Config**: Secure credential management via `.env` file

## Prerequisites

### Required Software
- **Python 3.7 or higher**
  ```bash
  python3 --version  # Check your version
  ```

### Required Services
- **Paramify** account
  - API access with upload permissions

### Optional Services (depending on your use case)
- **Nessus** (Essentials or Professional) - Only needed for importing from Nessus
  - Running instance with web access
  - API access enabled
- **GitHub** - Only needed for importing from private repositories

### Required Credentials
- **Paramify API key** (required for all operations)

### Optional Credentials (depending on features you use)
- **Nessus API keys** (access key + secret key) - Only for Nessus import
- **GitHub token** - Only for private repository access

## Installation

### Quick Install (Recommended)

**macOS (Super Easy):**
1. Download/clone the repository
2. Navigate to `demo/vuln-fetcher` in Finder
3. Double-click `install.command`
4. Follow the prompts

**macOS/Linux (Command Line):**
```bash
git clone https://github.com/paramify/demo.git
cd demo/vuln-fetcher
chmod +x install.sh
./install.sh
```

The installation script will:
1. Check for Python 3
2. Create a virtual environment
3. Install all dependencies
4. Guide you through entering your API credentials
5. Test your connections

That's it! After installation completes:
- **macOS**: Double-click `run.command`
- **Command Line**: Run `./run.sh`

---

### Manual Installation

If you prefer to set up manually or the automatic installer doesn't work:

#### Step 1: Download the Code

```bash
git clone https://github.com/paramify/demo.git
cd demo/vuln-fetcher
```

#### Step 2: Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows PowerShell:**
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```bash
python -m venv venv
venv\Scripts\activate.bat
```

#### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 4: Configure Credentials

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Paramify Configuration
PARAMIFY_API_KEY=your_paramify_api_key_here
PARAMIFY_BASE_URL=https://demo.paramify.com/api/v0

# Nessus Configuration
NESSUS_URL=https://localhost:8834
NESSUS_ACCESS_KEY=your_nessus_access_key_here
NESSUS_SECRET_KEY=your_nessus_secret_key_here

# GitHub Configuration (Optional)
GITHUB_TOKEN=your_github_token_here
```

**Important:**
- Don't add quotes around values
- Don't add spaces around `=`
- Paste API keys exactly as provided

#### Step 5: Make Scripts Executable (macOS/Linux)

```bash
chmod +x run.sh install.sh
```

#### Step 6: Test Your Setup

```bash
./run.sh list-scans
./run.sh list-assessments
```

If both commands show data, you're ready to go! 🎉

## Getting API Credentials

### Paramify API Key

1. Log in to Paramify
2. Navigate to **Settings** → **API Settings**
3. Generate or copy your API key
4. The key starts with `/` and contains alphanumeric characters
5. Copy the entire key including the `/`

### Nessus API Keys

1. Log in to Nessus (typically https://localhost:8834)
2. Click your **username** (top right)
3. Select **My Account** → **API Keys**
4. Click **Generate** new keys
5. Copy both:
   - **Access Key**: 64-character hex string
   - **Secret Key**: 64-character hex string
6. ⚠️ Secret key is only shown once - save it securely!

### GitHub Token (Optional)

Only needed for private repositories.

1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Name: "Paramify Integration"
4. Scopes: Select `repo` (or `public_repo` for public only)
5. Click **Generate token**
6. Copy the token (starts with `ghp_`)
7. ⚠️ Only shown once - save it securely!

## Quick Start

### Daily Usage

**macOS (Easiest):**
Simply double-click the `run.command` file in Finder!

The tool will automatically:
- Check your setup
- Activate the virtual environment
- Launch the interactive menu
- Keep the Terminal window open until you're done

**macOS/Linux (Command Line):**
```bash
cd demo/vuln-fetcher
./run.sh
```

**Windows:**
```bash
cd demo\vuln-fetcher
.\venv\Scripts\Activate.ps1
python main.py
```

### Main Menu

You'll see:
```
======================================================================
  PARAMIFY ASSESSMENTS INTEGRATION
======================================================================

What would you like to do?

  1. Import from Nessus (live scan from your Nessus instance)
  2. Import from GitHub (scan files stored in a repository)
  3. List Nessus scans
  4. List Paramify assessments
  5. Exit

Enter your choice (1-5):
```

Just pick a number and follow the prompts!

**Note**: Options 3 and 4 will show you the available resources and then return you to the main menu.

### When You're Done

Exit the virtual environment:
```bash
deactivate
```

## Usage Examples

### Example 1: Import from Nessus

```bash
./run.sh import
```

**Interactive prompts:**
1. Select a scan by number
2. Select an assessment by number
3. Enter effective date (or press Enter for today)
4. Confirm and import

**Output:**
```
======================================================================
  ✓ IMPORT SUCCESSFUL
======================================================================

  Artifact ID:   745c0d65-6498-4978-9e6a-867c9a5db911
  File:          My Basic Network Scan.nessus
  Effective:     2025-02-02
```

### Example 2: Import from GitHub (Public Repo)

```bash
./run.sh import-github
```

**Enter repository:**
```
Repository: paramify/demo
```

Or full URL:
```
Repository: https://github.com/paramify/demo/tree/main/demo%20evidence
```

**Then:**
1. Skip GitHub token (press Enter)
2. Select a file by number
3. Select an assessment by number
4. Set effective date
5. Confirm and import

### Example 3: Import from GitHub (Private Repo)

Same as above, but provide your GitHub token when prompted.

### Example 4: List Available Scans

```bash
./run.sh list-scans
```

**Output:**
```
======================================================================
  NESSUS SCANS
======================================================================

#    ID       Name                                     Status
----------------------------------------------------------------------
1    8        My Basic Network Scan                    ✓ completed
2    5        My Host Discovery Scan                   ✓ completed
```

### Example 5: List Paramify Assessments

```bash
./run.sh list-assessments
```

**Output:**
```
======================================================================
  PARAMIFY ASSESSMENTS
======================================================================

#    Name                                Type
----------------------------------------------------------------------
1    Q1 Vulnerability Assessment         Vulnerability
2    Q2 Configuration Review             Configuration
```

### Advanced: Command Line Arguments

**Import with specific IDs:**
```bash
./run.sh import --scan-id 8 --assessment-id 5b724986-d2ae-4b7b-b7c8-b597d76e65bc
```

**With effective date:**
```bash
./run.sh import --scan-id 8 --assessment-id 5b724986-d2ae-4b7b-b7c8-b597d76e65bc --effective-date 2025-02-15
```

## Project Structure

```
demo/vuln-fetcher/
├── main.py                 # CLI entry point
├── integration.py          # Workflow orchestration
├── nessus_client.py        # Nessus API client
├── paramify_client.py      # Paramify API client
├── github_client.py        # GitHub API client
├── config.py               # Configuration management
├── run.command             # Double-click launcher (macOS)
├── run.sh                  # Command-line wrapper
├── install.command         # Double-click installer (macOS)
├── install.sh              # Command-line installer
├── requirements.txt        # Python dependencies
├── .env                    # Your credentials (not in git)
├── .env.example            # Template for credentials
├── README.md               # This file (user guide)
├── QUICKSTART.md           # Quick reference guide
└── CLAUDE.md               # Developer documentation
```

## How It Works

### Nessus Import Flow

1. **Authentication**: Connects to Nessus using API keys
2. **Scan Selection**: User selects a completed scan
3. **Export Request**: Requests export in `.nessus` format
4. **Status Polling**: Waits for export to complete (automatic)
5. **Download**: Downloads the exported file
6. **Upload**: Uploads to Paramify assessment intake endpoint
7. **Confirmation**: Returns artifact ID and effective date

### GitHub Import Flow

1. **Repository Access**: Connects to GitHub (public or with token)
2. **File Search**: Recursively searches for `.nessus` and `.csv` files
3. **File Selection**: User selects a file
4. **Download**: Downloads file content from GitHub
5. **Upload**: Uploads to Paramify assessment intake endpoint
6. **Confirmation**: Returns artifact ID and effective date

### API Endpoints Used

**Nessus:**
- `GET /scans` - List all scans
- `POST /scans/{scan_id}/export` - Request export
- `GET /scans/{scan_id}/export/{file_id}/status` - Check status
- `GET /scans/{scan_id}/export/{file_id}/download` - Download

**Paramify:**
- `GET /assessment` - List assessments
- `POST /assessment/{assessmentId}/intake` - Upload artifact

**GitHub:**
- `GET /repos/{owner}/{repo}/contents/{path}` - List files
- `GET /repos/{owner}/{repo}/git/blobs/{sha}` - Download file

## Troubleshooting

### Installation Issues

**"Command not found: python3"**
- Try `python` instead of `python3`

**"ModuleNotFoundError: No module named 'requests'"**
- Make sure virtual environment is activated (you should see `(venv)`)
- Run `pip install -r requirements.txt` again

**"Permission denied: ./run.sh"** (macOS/Linux)
- Run `chmod +x run.sh`
- Or use `python main.py` instead

**Virtual environment won't activate** (Windows)
- PowerShell may block scripts
- Run once: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Configuration Issues

**"Configuration error: Missing required environment variables"**
1. Verify `.env` file exists: `ls -la .env`
2. Check all required fields are filled (except GITHUB_TOKEN)
3. Remove any extra spaces or quotes
4. Run from the project directory

### Connection Issues

**"SSL Certificate Verification Failed"** (Nessus)
- Normal for self-signed certificates (already handled)
- Verify NESSUS_URL is correct (usually `https://localhost:8834`)
- Ensure Nessus is running

**"401 Unauthorized"** (Nessus)
- Verify API keys are correct
- Regenerate keys in Nessus if needed
- Copy full access key and secret key

**"401 Unauthorized"** (Paramify)
- Verify API key is correct
- Ensure you copied the full key including `/` at start
- Check API key has upload permissions

**"Connection refused"**
- Nessus: Make sure Nessus is running
- Paramify: Check network connectivity
- Verify firewall isn't blocking connections

### Import Issues

**"No scans available"**
- Ensure you have scans in Nessus
- Check API credentials have permission to view scans

**"No assessments available"**
- Create at least one assessment in Paramify
- Verify API key has permission to view assessments

**"File must be one of the following types"**
- Already fixed in latest version
- Ensure you're using `.nessus` or `.csv` files
- Check file isn't corrupted

**"Effective date not being applied"**
- Already fixed in latest version
- Date must be in YYYY-MM-DD format
- Leave blank to use today's date

### GitHub Issues

**"No scan files found"**
- Verify repository exists and is accessible
- For private repos, provide GitHub token
- Check you're searching the correct branch/path
- Ensure files have `.nessus` or `.csv` extension

**"API rate limit exceeded"**
- Provide GitHub token (increases rate limit)
- Wait an hour for rate limit to reset

## Security Notes

### Credentials Management
- ✅ `.env` file is excluded from git (in `.gitignore`)
- ✅ Never commit API keys to version control
- ✅ Store API keys securely
- ✅ Rotate API keys regularly
- ✅ Use minimal permissions for GitHub tokens

### SSL/TLS
- Nessus SSL verification is disabled (common for self-signed certs)
- Paramify and GitHub use standard HTTPS

### Best Practices
- Don't share your `.env` file
- Don't post API keys in public forums
- Use environment variables in production
- Encrypt backups containing `.env` file
- Review API key permissions regularly

## Developer Documentation

For developers working on this codebase, see **[CLAUDE.md](CLAUDE.md)** for:
- Architecture overview
- Code structure and patterns
- API client implementations
- Critical technical details (MIME types, effectiveDate handling)
- Common issues and solutions
- Testing procedures
- Future enhancement ideas

## Support

**Issue Order:**
1. Check this README's Troubleshooting section
2. Review error messages carefully
3. Verify API credentials are valid
4. Test connections individually (list-scans, list-assessments)
5. Check CLAUDE.md for developer details

## Contributing

This is a defensive security tool. Contributions should focus on:
- Bug fixes
- Performance improvements
- Documentation enhancements
- Additional defensive security features

## License

This tool is provided as-is for defensive security purposes only.

---

**Quick Reference:**
- Start tool: `./run.sh` or `python main.py`
- Activate venv: `source venv/bin/activate` (macOS/Linux) or `.\venv\Scripts\Activate.ps1` (Windows)
- Deactivate venv: `deactivate`
- Test Nessus: `./run.sh list-scans`
- Test Paramify: `./run.sh list-assessments`
- Help: `./run.sh --help`
