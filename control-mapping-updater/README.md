# Control Mapping Updater

A Python script that syncs Suggested Mappings from a Master Solution Capabilities CSV file to target CSV files.

## What It Does

- Compares Solution Capabilities between a master file and a target file
- Adds any missing control mappings from the master to the target
- **Never removes or modifies existing mappings** in the target file
- Only updates the "Suggested Mappings" column - all other data remains unchanged

## Requirements

- macOS (uses native file dialogs)
- Python 3.x

## Setup

1. Place the script (`update_control_mapping.py`) in a folder
2. Place your `Master Solution Capabilities.csv` file in the same folder as the script

## Usage

1. Run the script:
   ```bash
   python3 update_control_mapping.py
   ```

2. An instructions popup will appear - click **Continue**

3. A file browser will open - select the CSV file you want to update

4. The script will:
   - Compare Solution Capabilities between your file and the master
   - Add any missing mappings
   - Display a summary of changes

## Example Output

```
=== Control Mapping Updater ===
Master file: Master Solution Capabilities.csv

Loading master file: /path/to/Master Solution Capabilities.csv
Found 284 unique Solution Capabilities in master file.

Loading target file: /path/to/target-file.csv
  Updated 'Multifactor Authentication for Non-Privileged Users': added 3 mapping(s)
  Updated 'Post-deployment Check': added 1 mapping(s)

--- Summary ---
Solution Capabilities updated: 2
Total mappings added: 4
File saved: /path/to/target-file.csv

--- Not in Master (5) ---
The following Solution Capabilities in the target file were not found in the master:
  - Custom Capability 1
  - Custom Capability 2
```

## Notes

- Solution Capability names are matched with normalization (trailing colons and whitespace are ignored for comparison)
- If a Solution Capability in the target file doesn't exist in the master, it will be listed in the "Not in Master" section but left unchanged
- The master file must be named exactly `Master Solution Capabilities.csv`
