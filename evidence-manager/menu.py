#!/usr/bin/env python3
"""
Interactive CLI Menu for Paramify Evidence Manager
"""

import sys
from pathlib import Path

from paramify_client import (
    ParamifyClient,
    ProgressBar,
    ProgressInfo,
    ValidationError,
    APIError,
    read_evidence_file,
    normalize_keys,
    success,
    error,
    warning,
    info,
    bold
)

# Determine the directory where this script lives
SCRIPT_DIR = Path(__file__).parent.resolve()

# Initialize global client
client: ParamifyClient = None


def clear_screen():
    """Clear the terminal screen."""
    print("\033[H\033[J", end="")


def print_header():
    """Print the application header."""
    print(bold("=" * 60))
    print(bold("  PARAMIFY EVIDENCE MANAGER"))
    print(bold("=" * 60))
    if client:
        if client.workspace_name:
            print(f"  Workspace: {bold(client.workspace_name)}")
        if client.api_url:
            print(f"  API: {info(client.api_url)}")
    print(bold("=" * 60))
    print()


def print_menu():
    """Print the main menu options."""
    print("\nMain Menu:")
    print("  1. List All Evidence")
    print("  2. Create Evidence (Bulk from File)")
    print("  3. Create Evidence (Single Entry)")
    print("  4. Search Evidence")
    print("  5. View Evidence Details")
    print("  6. Edit Evidence")
    print("  7. Delete Evidence")
    print("  8. Export Evidence")
    print("  9. Settings")
    print("  0. Exit")
    print()


def list_evidence():
    """List all evidence records."""
    print("\n" + bold("=" * 100))
    print(bold("LISTING ALL EVIDENCE"))
    print(bold("=" * 100))

    try:
        evidences = client.get_all_evidence()

        if not evidences:
            print(warning("\nNo evidence records found."))
            return

        print(f"\nTotal: {bold(str(len(evidences)))} evidence record(s)\n")
        print(f"{'#':<5} {'Evidence ID':<38} {'Reference ID':<15} {'Name':<40}")
        print("-" * 100)

        for idx, e in enumerate(evidences, 1):
            ev_id = e.get("id") or "N/A"
            ref_id = e.get("referenceId") or "N/A"
            name = e.get("name") or "N/A"
            name = name[:37] + "..." if len(name) > 40 else name
            print(f"{idx:<5} {ev_id:<38} {ref_id:<15} {name:<40}")

        print("\n" + "=" * 100)
        print(f"Total: {bold(str(len(evidences)))} evidence record(s)")
        print("=" * 100)

    except APIError as e:
        print(error(f"\nError: {e}"))


def create_evidence_bulk():
    """Create evidence from a file."""
    print("\n" + bold("=" * 60))
    print(bold("CREATE EVIDENCE (BULK)"))
    print(bold("=" * 60))

    file_path = input("\nEnter file path (CSV, JSON, or Excel): ").strip()

    if not file_path:
        print(warning("Cancelled."))
        return

    try:
        evidence_list = read_evidence_file(file_path)
        print(f"\nFound {bold(str(len(evidence_list)))} evidence request(s)")

        # Ask for confirmation
        confirm = input("\nProceed with creation? (y/n): ").strip().lower()
        if confirm != 'y':
            print(warning("Cancelled."))
            return

        # Check duplicates option
        check_dupes = input("Check for duplicates? (y/n, default=y): ").strip().lower()
        check_dupes = check_dupes != 'n'

        # Progress bar
        progress_bar = ProgressBar(len(evidence_list), prefix="Creating")

        def progress_callback(prog_info: ProgressInfo):
            progress_bar.update(prog_info)

        # Process
        results = client.create_evidence_bulk(
            evidence_list,
            check_duplicates=check_dupes,
            allow_duplicates=False,
            progress_callback=progress_callback
        )

        # Summary
        print("\n" + bold("=" * 60))
        print(f"Created: {success(str(results['created']))} | "
              f"Skipped: {warning(str(results['skipped']))} | "
              f"Failed: {error(str(results['failed']))}")
        print(bold("=" * 60))

    except FileNotFoundError as e:
        print(error(f"\nFile not found: {e}"))
    except Exception as e:
        print(error(f"\nError: {e}"))


def create_evidence_single():
    """Create a single evidence record interactively."""
    print("\n" + bold("=" * 60))
    print(bold("CREATE EVIDENCE (SINGLE)"))
    print(bold("=" * 60))

    print("\nEnter evidence details (press Enter to skip optional fields):")

    name = input("  Name (required): ").strip()
    if not name:
        print(error("Error: Name is required."))
        return

    reference_id = input("  Reference ID: ").strip()
    description = input("  Description: ").strip()
    instructions = input("  Instructions: ").strip()
    remarks = input("  Remarks: ").strip()

    automated = input("  Automated? (y/n): ").strip().lower()
    automated_bool = None
    if automated == 'y':
        automated_bool = True
    elif automated == 'n':
        automated_bool = False

    # Build evidence data
    evidence_data = {"name": name}
    if reference_id:
        evidence_data["referenceId"] = reference_id
    if description:
        evidence_data["description"] = description
    if instructions:
        evidence_data["instructions"] = instructions
    if remarks:
        evidence_data["remarks"] = remarks
    if automated_bool is not None:
        evidence_data["automated"] = automated_bool

    # Confirm
    print(info("\nEvidence to create:"))
    for key, value in evidence_data.items():
        print(f"  {key}: {value}")

    confirm = input("\nCreate this evidence? (y/n): ").strip().lower()
    if confirm != 'y':
        print(warning("Cancelled."))
        return

    try:
        result = client.create_evidence(normalize_keys(evidence_data))
        print(success(f"\nSuccess! Created: {result['name']}"))
        print(f"  ID: {result['id']}")
        if result.get('referenceId'):
            print(f"  Reference ID: {result['referenceId']}")
    except (ValidationError, APIError) as e:
        print(error(f"\nError: {e}"))


def search_evidence():
    """Search for evidence by name or reference ID."""
    print("\n" + bold("=" * 60))
    print(bold("SEARCH EVIDENCE"))
    print(bold("=" * 60))

    search_term = input("\nEnter search term (name or reference ID): ").strip().lower()

    if not search_term:
        print(warning("Cancelled."))
        return

    try:
        evidences = client.get_all_evidence()

        # Filter evidence
        results = []
        for e in evidences:
            name = (e.get("name") or "").lower()
            ref_id = (e.get("referenceId") or "").lower()

            if search_term in name or search_term in ref_id:
                results.append(e)

        if not results:
            print(warning(f"\nNo evidence found matching '{search_term}'"))
            return

        print(f"\nFound {bold(str(len(results)))} result(s):\n")
        print(f"{'#':<5} {'Reference ID':<15} {'Name':<40}")
        print("-" * 60)

        for idx, e in enumerate(results, 1):
            ref_id = e.get("referenceId") or "N/A"
            name = e.get("name") or "N/A"
            name = name[:37] + "..." if len(name) > 40 else name
            print(f"{idx:<5} {ref_id:<15} {name:<40}")

    except APIError as e:
        print(error(f"\nError: {e}"))


def view_evidence_details():
    """View detailed information about a specific evidence record."""
    print("\n" + bold("=" * 60))
    print(bold("VIEW EVIDENCE DETAILS"))
    print(bold("=" * 60))

    evidence_id = input("\nEnter evidence ID: ").strip()

    if not evidence_id:
        print(warning("Cancelled."))
        return

    try:
        evidence = client.get_evidence(evidence_id)

        print("\n" + "-" * 60)
        print(f"ID:           {evidence.get('id', 'N/A')}")
        print(f"Reference ID: {evidence.get('referenceId', 'N/A')}")
        print(f"Name:         {bold(evidence.get('name', 'N/A'))}")
        print(f"Description:  {evidence.get('description', 'N/A')}")
        print(f"Instructions: {evidence.get('instructions', 'N/A')}")
        print(f"Remarks:      {evidence.get('remarks', 'N/A')}")
        print(f"Automated:    {evidence.get('automated', 'N/A')}")
        print(f"Artifacts:    {len(evidence.get('artifacts', []))} artifact(s)")
        print("-" * 60)

    except APIError as e:
        if e.status_code == 404:
            print(warning(f"\nEvidence not found: {evidence_id}"))
        else:
            print(error(f"\nError: {e}"))


def edit_evidence():
    """Edit an existing evidence record."""
    print("\n" + bold("=" * 60))
    print(bold("EDIT EVIDENCE"))
    print(bold("=" * 60))

    evidence_id = input("\nEnter evidence ID to edit: ").strip()

    if not evidence_id:
        print(warning("Cancelled."))
        return

    try:
        # Fetch current evidence
        evidence = client.get_evidence(evidence_id)

        print(info("\nCurrent values (press Enter to keep, or type new value):"))
        print("-" * 60)

        # Get updated values
        current_name = evidence.get('name', '')
        new_name = input(f"  Name [{current_name}]: ").strip()
        if not new_name:
            new_name = current_name

        current_ref = evidence.get('referenceId', '')
        new_ref = input(f"  Reference ID [{current_ref}]: ").strip()
        if not new_ref:
            new_ref = current_ref

        current_desc = evidence.get('description', '')
        new_desc = input(f"  Description [{current_desc[:50] + '...' if len(current_desc) > 50 else current_desc}]: ").strip()
        if not new_desc:
            new_desc = current_desc

        current_inst = evidence.get('instructions', '')
        new_inst = input(f"  Instructions [{current_inst[:50] + '...' if len(current_inst) > 50 else current_inst}]: ").strip()
        if not new_inst:
            new_inst = current_inst

        current_remarks = evidence.get('remarks', '')
        new_remarks = input(f"  Remarks [{current_remarks[:50] + '...' if len(current_remarks) > 50 else current_remarks}]: ").strip()
        if not new_remarks:
            new_remarks = current_remarks

        current_auto = evidence.get('automated', False)
        auto_input = input(f"  Automated? (y/n) [{('y' if current_auto else 'n')}]: ").strip().lower()
        if auto_input == 'y':
            new_auto = True
        elif auto_input == 'n':
            new_auto = False
        else:
            new_auto = current_auto

        # Build update data
        update_data = {
            "name": new_name,
            "referenceId": new_ref if new_ref else None,
            "description": new_desc if new_desc else None,
            "instructions": new_inst if new_inst else None,
            "remarks": new_remarks if new_remarks else None,
            "automated": new_auto
        }

        # Show changes
        print(info("\nChanges to apply:"))
        changes = False
        if new_name != current_name:
            print(f"  Name: {current_name} -> {bold(new_name)}")
            changes = True
        if new_ref != current_ref:
            print(f"  Reference ID: {current_ref} -> {bold(new_ref)}")
            changes = True
        if new_desc != current_desc:
            print(f"  Description: (updated)")
            changes = True
        if new_inst != current_inst:
            print(f"  Instructions: (updated)")
            changes = True
        if new_remarks != current_remarks:
            print(f"  Remarks: (updated)")
            changes = True
        if new_auto != current_auto:
            print(f"  Automated: {current_auto} -> {bold(str(new_auto))}")
            changes = True

        if not changes:
            print(warning("  No changes detected."))
            return

        confirm = input("\nApply these changes? (y/n): ").strip().lower()
        if confirm != 'y':
            print(warning("Cancelled."))
            return

        # Update
        result = client.update_evidence(evidence_id, update_data)
        print(success(f"\nSuccess! Updated: {result.get('name', evidence_id)}"))

    except APIError as e:
        if e.status_code == 404:
            print(warning(f"\nEvidence not found: {evidence_id}"))
        else:
            print(error(f"\nError: {e}"))


def delete_evidence():
    """Delete an evidence record."""
    print("\n" + bold("=" * 60))
    print(bold("DELETE EVIDENCE"))
    print(bold("=" * 60))
    print(error("\nWARNING: This action cannot be undone!"))

    evidence_id = input("\nEnter evidence ID to delete: ").strip()

    if not evidence_id:
        print(warning("Cancelled."))
        return

    try:
        # Fetch evidence details first
        evidence = client.get_evidence(evidence_id)

        print(f"\nEvidence to delete:")
        print(f"  Name: {bold(evidence.get('name', 'N/A'))}")
        print(f"  Reference ID: {evidence.get('referenceId', 'N/A')}")

        confirm = input(error("\nAre you sure? Type 'DELETE' to confirm: ")).strip()

        if confirm != 'DELETE':
            print(warning("Cancelled."))
            return

        # Delete
        client.delete_evidence(evidence_id)
        print(success(f"\nDeleted: {evidence.get('name', evidence_id)}"))

    except APIError as e:
        if e.status_code == 404:
            print(warning(f"\nEvidence not found: {evidence_id}"))
        else:
            print(error(f"\nError: {e}"))


def export_evidence():
    """Export evidence to CSV or JSON."""
    print("\n" + bold("=" * 60))
    print(bold("EXPORT EVIDENCE"))
    print(bold("=" * 60))

    print("\nExport options:")
    print("  1. Export to CSV")
    print("  2. Export to JSON")
    print("  0. Cancel")

    choice = input("\nSelect format: ").strip()

    if choice == '0':
        print(warning("Cancelled."))
        return

    if choice not in ['1', '2']:
        print(error("Invalid option."))
        return

    # Get filename
    default_ext = '.csv' if choice == '1' else '.json'
    default_name = f"evidence_export{default_ext}"

    filename = input(f"\nEnter filename [{default_name}]: ").strip()
    if not filename:
        filename = default_name

    # Ensure correct extension
    if choice == '1' and not filename.endswith('.csv'):
        filename += '.csv'
    elif choice == '2' and not filename.endswith('.json'):
        filename += '.json'

    try:
        print(info(f"\nExporting to {filename}..."))

        if choice == '1':
            count = client.export_to_csv(filename)
        else:
            count = client.export_to_json(filename)

        print(success(f"\nExported {count} evidence record(s) to {filename}"))

    except APIError as e:
        print(error(f"\nError fetching evidence: {e}"))
    except Exception as e:
        print(error(f"\nError writing file: {e}"))


def settings():
    """View and update API settings."""
    global client

    print("\n" + bold("=" * 60))
    print(bold("SETTINGS"))
    print(bold("=" * 60))

    # Show current settings (mask API key)
    api_key = client.api_key or ""
    masked_key = api_key[:10] + "..." + api_key[-5:] if len(api_key) > 15 else "Not set"

    print(f"\nCurrent Settings:")
    print(f"  Workspace:    {bold(client.workspace_name or 'Not set')}")
    print(f"  API Base URL: {info(client.api_url or 'Not set')}")
    print(f"  API Key:      {masked_key}")

    print("\nOptions:")
    print("  1. Update Workspace Name")
    print("  2. Update API Base URL")
    print("  3. Update API Key")
    print("  4. Test Connection")
    print("  5. Save to .env file")
    print("  0. Back to Main Menu")

    choice = input("\nSelect an option: ").strip()

    if choice == '1':
        new_name = input(f"\nEnter workspace name [{client.workspace_name or ''}]: ").strip()
        if new_name:
            client.workspace_name = new_name
            print(success(f"Workspace name updated to: {new_name}"))

    elif choice == '2':
        new_url = input("\nEnter new API Base URL: ").strip()
        if new_url:
            client.api_url = new_url
            print(success(f"API Base URL updated to: {new_url}"))

    elif choice == '3':
        new_key = input("\nEnter new API Key: ").strip()
        if new_key:
            client.api_key = new_key
            print(success("API Key updated successfully"))

    elif choice == '4':
        try:
            print(info("\nTesting connection..."))
            client.test_connection()
            print(success("Connection successful!"))
        except (ValidationError, APIError) as e:
            print(error(f"Connection failed: {e}"))

    elif choice == '5':
        # Save to .env file
        try:
            env_path = SCRIPT_DIR / ".env"

            # Read current .env file
            env_lines = []
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()

            # Update or add the API settings
            updated_url = False
            updated_key = False
            updated_name = False
            new_lines = []

            for line in env_lines:
                if line.strip().startswith('PARAMIFY_API_URL='):
                    new_lines.append(f'PARAMIFY_API_URL={client.api_url}\n')
                    updated_url = True
                elif line.strip().startswith('PARAMIFY_API_KEY='):
                    new_lines.append(f'PARAMIFY_API_KEY={client.api_key}\n')
                    updated_key = True
                elif line.strip().startswith('PARAMIFY_WORKSPACE_NAME='):
                    new_lines.append(f'PARAMIFY_WORKSPACE_NAME={client.workspace_name or ""}\n')
                    updated_name = True
                else:
                    new_lines.append(line)

            # If not found, append them
            if not updated_name and client.workspace_name:
                new_lines.insert(0, f'PARAMIFY_WORKSPACE_NAME={client.workspace_name}\n')
            if not updated_url:
                new_lines.append(f'PARAMIFY_API_URL={client.api_url}\n')
            if not updated_key:
                new_lines.append(f'PARAMIFY_API_KEY={client.api_key}\n')

            # Write back to .env file
            with open(env_path, 'w') as f:
                f.writelines(new_lines)

            print(success(f"\nSettings saved to {env_path}"))

        except Exception as e:
            print(error(f"\nError saving to .env file: {e}"))

    elif choice == '0':
        return


def main_loop():
    """Main interactive loop."""
    global client

    # Initialize client
    client = ParamifyClient()

    # Validate configuration
    try:
        client.validate_config()
    except ValidationError as e:
        print(error(f"Error: {e}"))
        sys.exit(1)

    # Test connection on startup
    print(info("Validating API connection..."))
    try:
        client.test_connection()
        print(success("Connection successful!"))
    except APIError as e:
        print(error(f"Connection failed: {e}"))
        print(warning("\nYou can update your settings from the menu."))
        input("Press Enter to continue...")

    while True:
        clear_screen()
        print_header()
        print_menu()

        choice = input("Select an option: ").strip()

        if choice == '1':
            list_evidence()
        elif choice == '2':
            create_evidence_bulk()
        elif choice == '3':
            create_evidence_single()
        elif choice == '4':
            search_evidence()
        elif choice == '5':
            view_evidence_details()
        elif choice == '6':
            edit_evidence()
        elif choice == '7':
            delete_evidence()
        elif choice == '8':
            export_evidence()
        elif choice == '9':
            settings()
        elif choice == '0':
            print(success("\nGoodbye!"))
            break
        else:
            print(error("\nInvalid option. Please try again."))
            continue

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print(success("\n\nGoodbye!"))
        sys.exit(0)
