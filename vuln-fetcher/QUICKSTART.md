# Quick Start Guide

Get up and running in 2 minutes!

## Installation

**Option 1 (macOS - Easiest):**
1. Clone/download the repo
2. Open `demo/vuln-fetcher` in Finder
3. Double-click `install.command`

**Option 2 (Command Line):**
```bash
git clone https://github.com/paramify/demo.git
cd demo/vuln-fetcher
chmod +x install.sh
./install.sh
```

Follow the prompts to enter your API credentials.

## Usage

**Option 1 (Easiest):**
Double-click `run.command` in Finder!

**Option 2 (Command Line):**
```bash
./run.sh
```

That's it! The interactive menu will guide you through importing scans.

**Tip**: When you list scans or assessments (options 3-4), you'll return to the main menu afterward.

## Need Help?

- **Full documentation**: See [README.md](README.md)
- **Developer docs**: See [CLAUDE.md](CLAUDE.md)
- **Troubleshooting**: Check README.md "Troubleshooting" section

## Common Commands

```bash
./run.sh                    # Interactive menu
./run.sh import             # Import from Nessus
./run.sh import-github      # Import from GitHub
./run.sh list-scans         # List Nessus scans
./run.sh list-assessments   # List Paramify assessments
./run.sh --help             # Show all options
```
