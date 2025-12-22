#!/usr/bin/env python3
"""
Control Mapping Updater
Syncs Suggested Mappings from a Master Solution Capabilities CSV to target CSV files.
Only adds missing mappings - never removes or alters existing ones.
"""

import csv
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SCRIPT_DIR = Path(__file__).parent
MASTER_CSV = SCRIPT_DIR / "Master Solution Capabilities.csv"
BACKUP_DIR = SCRIPT_DIR / "backups"


def show_instructions(dry_run: bool = False) -> bool:
    """Show instructions popup. Returns True if user clicks Continue."""
    mode = "DRY RUN MODE - " if dry_run else ""
    backup_note = "A backup will be created before making changes." if not dry_run else "No changes will be saved."

    instructions = f"""{mode}Control Mapping Updater

This tool syncs Suggested Mappings from the Master Solution Capabilities file to a target CSV file.

How it works:
1. You will select a CSV file to update
2. The tool compares Solution Capabilities between your file and the Master
3. Any missing control mappings are added to your file
4. Existing mappings are never removed or modified

{backup_note}"""

    script = f'''
    display dialog "{instructions}" with title "Instructions" buttons {{"Cancel", "Continue"}} default button "Continue"
    return button returned of result
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or "Cancel" in result.stdout:
            return False
        return True
    except Exception:
        return True


def select_target_file() -> Path:
    """Open a native macOS file browser dialog to select a CSV file."""
    script = f'''
    set defaultFolder to POSIX file "{SCRIPT_DIR}" as alias
    set selectedFile to choose file with prompt "Select CSV file to update" of type {{"csv", "public.comma-separated-values-text"}} default location defaultFolder
    return POSIX path of selectedFile
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("No file selected. Exiting.")
            sys.exit(0)

        return Path(result.stdout.strip())

    except Exception as e:
        print(f"Error opening file dialog: {e}")
        sys.exit(1)


def create_backup(file_path: Path) -> Path:
    """Create a backup of the file before modification."""
    BACKUP_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}.csv"
    backup_path = BACKUP_DIR / backup_name

    shutil.copy2(file_path, backup_path)
    return backup_path


def load_csv(file_path: Path) -> tuple[list[str], list[list[str]]]:
    """Load CSV file and return headers and rows."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)
    return headers, rows


def save_csv(file_path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """Save headers and rows back to CSV file."""
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def find_column_index(headers: list[str], column_name: str) -> int:
    """Find the index of a column by name."""
    try:
        return headers.index(column_name)
    except ValueError:
        print(f"Error: '{column_name}' column not found in CSV.")
        sys.exit(1)


def parse_mappings(mapping_str: str) -> set[str]:
    """Parse the Suggested Mappings string into a set of individual controls."""
    if not mapping_str or not mapping_str.strip():
        return set()
    return {m.strip() for m in mapping_str.split('\n') if m.strip()}


def normalize_capability_name(name: str) -> str:
    """Normalize a capability name for comparison."""
    return name.strip().rstrip(':').strip()


def build_master_lookup(rows: list[list[str]], cap_idx: int, mapping_idx: int) -> dict[str, set[str]]:
    """Build a lookup dictionary from Solution Capability name to its mappings."""
    lookup = {}
    for row in rows:
        if len(row) > cap_idx:
            cap_name = normalize_capability_name(row[cap_idx])
            if cap_name:
                mappings = parse_mappings(row[mapping_idx] if len(row) > mapping_idx else "")
                if cap_name in lookup:
                    lookup[cap_name].update(mappings)
                else:
                    lookup[cap_name] = mappings
    return lookup


def main(dry_run: bool = False):
    """Main function."""
    # Show instructions
    if not show_instructions(dry_run=dry_run):
        print("Cancelled.")
        sys.exit(0)

    # Check master file exists
    if not MASTER_CSV.exists():
        print(f"Error: Master file not found at '{MASTER_CSV}'")
        sys.exit(1)

    mode = "[DRY RUN] " if dry_run else ""
    print(f"=== {mode}Control Mapping Updater ===")
    print(f"Master file: {MASTER_CSV.name}")

    # Select target file
    target_path = select_target_file()

    # Load master CSV
    print(f"\nLoading master file: {MASTER_CSV}")
    master_headers, master_rows = load_csv(MASTER_CSV)
    master_cap_idx = find_column_index(master_headers, 'Solution Capability')
    master_mapping_idx = find_column_index(master_headers, 'Suggested Mappings')

    # Build master lookup
    master_lookup = build_master_lookup(master_rows, master_cap_idx, master_mapping_idx)
    print(f"Found {len(master_lookup)} unique Solution Capabilities in master file.")

    # Load target CSV
    print(f"\nLoading target file: {target_path}")
    target_headers, target_rows = load_csv(target_path)
    target_cap_idx = find_column_index(target_headers, 'Solution Capability')
    target_mapping_idx = find_column_index(target_headers, 'Suggested Mappings')

    # Track statistics
    capabilities_updated = 0
    mappings_added = 0
    capabilities_not_in_master = []

    # Process each row in target
    for row in target_rows:
        if len(row) <= target_cap_idx:
            continue

        cap_name_raw = row[target_cap_idx].strip()
        if not cap_name_raw:
            continue

        cap_name = normalize_capability_name(cap_name_raw)

        if cap_name not in master_lookup:
            if cap_name not in capabilities_not_in_master:
                capabilities_not_in_master.append(cap_name)
            continue

        current_mappings = parse_mappings(row[target_mapping_idx] if len(row) > target_mapping_idx else "")
        master_mappings = master_lookup[cap_name]
        missing_mappings = master_mappings - current_mappings

        if missing_mappings:
            while len(row) <= target_mapping_idx:
                row.append("")

            all_mappings = current_mappings | missing_mappings
            row[target_mapping_idx] = '\n'.join(sorted(all_mappings))

            capabilities_updated += 1
            mappings_added += len(missing_mappings)

            print(f"  {'Would update' if dry_run else 'Updated'} '{cap_name}': +{len(missing_mappings)} mapping(s)")

    # Save updated CSV (unless dry run)
    if capabilities_updated > 0:
        if dry_run:
            print(f"\n--- Dry Run Summary ---")
            print(f"Would update {capabilities_updated} Solution Capabilities")
            print(f"Would add {mappings_added} mappings")
            print(f"\nNo changes were made. Run without --dry-run to apply changes.")
        else:
            # Create backup first
            backup_path = create_backup(target_path)
            print(f"\nBackup created: {backup_path}")

            save_csv(target_path, target_headers, target_rows)
            print(f"\n--- Summary ---")
            print(f"Solution Capabilities updated: {capabilities_updated}")
            print(f"Total mappings added: {mappings_added}")
            print(f"File saved: {target_path}")
    else:
        print(f"\nNo updates needed - all mappings are already in sync.")

    # Report capabilities not found in master
    if capabilities_not_in_master:
        print(f"\n--- Not in Master ({len(capabilities_not_in_master)}) ---")
        print("The following Solution Capabilities in the target file were not found in the master:")
        for cap in capabilities_not_in_master[:20]:
            print(f"  - {cap}")
        if len(capabilities_not_in_master) > 20:
            print(f"  ... and {len(capabilities_not_in_master) - 20} more")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    main(dry_run=dry_run)
