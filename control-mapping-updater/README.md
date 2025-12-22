# Control Mapping Updater

Syncs Suggested Mappings from a Master Solution Capabilities CSV to target CSV files.

## What It Does

- Adds missing control mappings from the master to target files
- **Never removes or modifies** existing mappings
- Creates automatic backups before making changes

## Requirements

- macOS
- Python 3.x

## Usage

### Option 1: Double-click Menu

1. Double-click `Control Mapping Updater.command`
2. Choose **Dry Run** first to preview changes
3. Choose **Update File** to apply changes

### Option 2: Command Line

```bash
# Preview changes (no modifications)
python3 update_control_mapping.py --dry-run

# Apply changes
python3 update_control_mapping.py
```

## Files

- `Control Mapping Updater.command` - Double-click menu
- `update_control_mapping.py` - Main script
- `Master Solution Capabilities.csv` - Source of truth (required)
- `backups/` - Automatic backups (created when updating)

## Notes

- Master file must be named exactly `Master Solution Capabilities.csv`
- Backups are timestamped and kept in the `backups/` folder
