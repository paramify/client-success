# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Control Mapping Updater is a macOS-only tool that syncs "Suggested Mappings" from a master CSV file to target CSV files. It matches rows by "Solution Capability" name and adds any missing control mappings to the target file. The tool is additive-only — it never removes or modifies existing mappings.

## Running the Tool

```bash
# Preview changes without modifying files
python3 update_control_mapping.py --dry-run

# Apply changes (creates backup first)
python3 update_control_mapping.py
```

The `.command` file provides a menu-driven interface for double-click execution.

## Architecture

**Single-script design**: All logic is in `update_control_mapping.py` (~250 lines).

**Key flow**:
1. Show instructions via macOS AppleScript dialog
2. User selects target CSV via native file picker (AppleScript)
3. Load master CSV, build lookup: `{normalized_capability_name: set(mappings)}`
4. For each target row: find missing mappings, merge them (sorted, newline-separated)
5. Create timestamped backup, save updated target

**Important functions**:
- `normalize_capability_name()`: Strips whitespace and trailing colons for matching
- `parse_mappings()`: Splits newline-separated mapping strings into sets
- `build_master_lookup()`: Creates the capability→mappings dictionary

**CSV structure**: Expects columns "Solution Capability" and "Suggested Mappings" in both master and target files. Mappings are stored as newline-separated strings within cells.

## Platform Constraints

macOS only — uses `osascript` for:
- File picker dialog (`choose file`)
- Confirmation dialogs (`display dialog`)
