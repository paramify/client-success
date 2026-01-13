#!/usr/bin/env python3
"""
Interactive CLI Menu for Paramify Evidence Manager
"""

import sys
import subprocess
import platform
from pathlib import Path

from paramify_client import (
    ParamifyClient,
    ProgressBar,
    ProgressInfo,
    ValidationError,
    APIError,
    read_evidence_file,
    read_csv_file,
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


def pick_file(title: str = "Select a file", file_types: list = None) -> str:
    """
    Open a native file picker dialog using AppleScript on macOS.

    Args:
        title: Dialog window title
        file_types: List of file extensions like ["csv", "txt"] (without dots)

    Returns:
        Selected file path as string, or empty string if cancelled
    """
    if platform.system() != "Darwin":
        return ""

    # Build the AppleScript command
    script = f'tell application "System Events" to activate\n'
    script += f'set theFile to choose file with prompt "{title}"'

    # Add file type filter if specified
    if file_types:
        types_str = ", ".join([f'"{t}"' for t in file_types])
        script += f' of type {{{types_str}}}'

    script += f' default location (POSIX file "{SCRIPT_DIR}")\n'
    script += 'return POSIX path of theFile'

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except (subprocess.TimeoutExpired, Exception):
        return ""


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
    print("  9. Associate Evidence")
    print("  10. Settings")
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


def find_evidence_by_name_or_id(search_term: str) -> dict:
    """
    Find evidence by name or ID.

    Args:
        search_term: Either an evidence ID (UUID format) or evidence name

    Returns:
        The evidence record if found, None otherwise
    """
    # Check if it looks like a UUID (evidence ID)
    is_uuid = len(search_term) == 36 and search_term.count('-') == 4

    if is_uuid:
        # Try to fetch directly by ID
        try:
            return client.get_evidence(search_term)
        except APIError as e:
            if e.status_code == 404:
                return None
            raise

    # Otherwise, search by name
    try:
        all_evidence = client.get_all_evidence()
    except APIError:
        return None

    # Exact match first (case-insensitive)
    for ev in all_evidence:
        if ev.get('name', '').lower() == search_term.lower():
            return ev

    # Partial match (case-insensitive)
    matches = []
    for ev in all_evidence:
        if search_term.lower() in ev.get('name', '').lower():
            matches.append(ev)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches - let user choose
        print(warning(f"\nMultiple evidence records match '{search_term}':"))
        for idx, ev in enumerate(matches[:10], 1):  # Show max 10
            print(f"  {idx}. {ev.get('name')} (ID: {ev.get('id')[:8]}...)")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more")

        try:
            choice = input("\nSelect number (or 0 to cancel): ").strip()
            if choice == '0':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
        except (ValueError, IndexError):
            pass
        return None

    return None


def find_project_by_name(search_term: str, projects: list) -> dict:
    """
    Find a project by name.

    Args:
        search_term: Project/program name to search for
        projects: List of projects from API

    Returns:
        The project record if found, None otherwise
    """
    # Exact match first (case-insensitive)
    for proj in projects:
        if proj.get('name', '').lower() == search_term.lower():
            return proj

    # Partial match
    matches = []
    for proj in projects:
        if search_term.lower() in proj.get('name', '').lower():
            matches.append(proj)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches - let user choose
        print(warning(f"\nMultiple programs match '{search_term}':"))
        for idx, proj in enumerate(matches[:10], 1):
            print(f"  {idx}. {proj.get('name')} ({proj.get('type', 'N/A')})")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more")

        try:
            choice = input("\nSelect number (or 0 to cancel): ").strip()
            if choice == '0':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
        except (ValueError, IndexError):
            pass
        return None

    return None


def find_control_implementation(control_name: str, control_impls: list) -> dict:
    """
    Find a control implementation by control ID (e.g., "AC-1").

    Args:
        control_name: Control ID like "AC-1" or "AC-1 Part a1"
        control_impls: List of control implementations from API

    Returns:
        The control implementation record if found, None otherwise
    """
    control_name_lower = control_name.lower().strip()

    # First, try exact match on control field
    for ci in control_impls:
        if ci.get('control', '').lower() == control_name_lower:
            return ci

    # Try matching control + requirement (e.g., "AC-1 Part a1")
    for ci in control_impls:
        control = ci.get('control', '').lower()
        requirement = ci.get('requirement', '').lower()
        full_name = f"{control} {requirement}".strip()
        if full_name == control_name_lower:
            return ci

    # Partial match on control
    matches = []
    for ci in control_impls:
        control = ci.get('control', '').lower()
        if control_name_lower in control or control in control_name_lower:
            matches.append(ci)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches - let user choose
        print(warning(f"\nMultiple control implementations match '{control_name}':"))
        for idx, ci in enumerate(matches[:10], 1):
            ctrl = ci.get('control', 'N/A')
            req = ci.get('requirement', '')
            name = ci.get('name', 'N/A')
            display = f"{ctrl} {req}".strip() if req else ctrl
            print(f"  {idx}. {display} - {name[:40]}...")
        if len(matches) > 10:
            print(f"  ... and {len(matches) - 10} more")

        try:
            choice = input("\nSelect number (or 0 to cancel): ").strip()
            if choice == '0':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
        except (ValueError, IndexError):
            pass
        return None

    return None


def associate_evidence_interactive():
    """Associate evidence with control implementations using simplified workflow."""
    print("\n" + bold("=" * 60))
    print(bold("ASSOCIATE EVIDENCE"))
    print(bold("=" * 60))

    print("\nAssociation options:")
    print("  1. Associate Single Evidence (by program, control, evidence name)")
    print("  2. Associate from CSV File (program_name, control, evidence_name)")
    print("  3. Associate by IDs (manual entry)")
    print("  0. Cancel")

    choice = input("\nSelect an option: ").strip()

    if choice == '0':
        print(warning("Cancelled."))
        return

    if choice == '1':
        # Single association mode - simplified workflow
        print("\n" + bold("-" * 60))
        print(bold("SINGLE EVIDENCE ASSOCIATION"))
        print("-" * 60)

        # Step 1: Select program
        print(info("\nFetching programs..."))
        try:
            projects = client.get_projects()
        except APIError as e:
            print(error(f"Failed to fetch programs: {e}"))
            return

        if not projects:
            print(warning("No programs found in your workspace."))
            return

        print(f"\nAvailable Programs ({len(projects)}):")
        for idx, proj in enumerate(projects, 1):
            print(f"  {idx}. {proj.get('name')} ({proj.get('type', 'N/A')})")

        prog_input = input("\nEnter program name or number: ").strip()
        if not prog_input:
            print(warning("Cancelled."))
            return

        # Check if user entered a number
        try:
            prog_idx = int(prog_input) - 1
            if 0 <= prog_idx < len(projects):
                selected_project = projects[prog_idx]
            else:
                print(error("Invalid selection."))
                return
        except ValueError:
            # Search by name
            selected_project = find_project_by_name(prog_input, projects)

        if not selected_project:
            print(error(f"Program not found: {prog_input}"))
            return

        project_id = selected_project.get('id')
        print(success(f"Selected program: {selected_project.get('name')}"))

        # Step 2: Select control implementation
        print(info("\nFetching control implementations..."))
        try:
            control_impls = client.get_control_implementations(project_id)
        except APIError as e:
            print(error(f"Failed to fetch control implementations: {e}"))
            return

        if not control_impls:
            print(warning("No control implementations found for this program."))
            return

        print(f"\nFound {len(control_impls)} control implementation(s).")
        print("Enter a control ID (e.g., 'AC-1') or browse:")
        print("  Type 'list' to see all controls")

        control_input = input("\nEnter control ID: ").strip()
        if not control_input:
            print(warning("Cancelled."))
            return

        if control_input.lower() == 'list':
            # List all controls
            print(f"\nControl Implementations ({len(control_impls)}):")
            for idx, ci in enumerate(control_impls[:50], 1):  # Limit to 50
                ctrl = ci.get('control', 'N/A')
                req = ci.get('requirement', '')
                name = ci.get('name', 'N/A')
                display = f"{ctrl} {req}".strip() if req else ctrl
                print(f"  {idx}. {display} - {name[:40]}...")
            if len(control_impls) > 50:
                print(f"  ... and {len(control_impls) - 50} more")

            control_input = input("\nEnter control ID or number: ").strip()
            if not control_input:
                print(warning("Cancelled."))
                return

            # Check if number
            try:
                ci_idx = int(control_input) - 1
                if 0 <= ci_idx < len(control_impls):
                    selected_control = control_impls[ci_idx]
                else:
                    print(error("Invalid selection."))
                    return
            except ValueError:
                selected_control = find_control_implementation(control_input, control_impls)
        else:
            selected_control = find_control_implementation(control_input, control_impls)

        if not selected_control:
            print(error(f"Control implementation not found: {control_input}"))
            return

        control_impl_id = selected_control.get('id')
        ctrl_display = f"{selected_control.get('control', '')} {selected_control.get('requirement', '')}".strip()
        print(success(f"Selected control: {ctrl_display} - {selected_control.get('name', 'N/A')[:40]}"))

        # Step 3: Select evidence
        print(info("\nSearching for evidence..."))
        evidence_input = input("\nEnter evidence name: ").strip()
        if not evidence_input:
            print(warning("Cancelled."))
            return

        evidence = find_evidence_by_name_or_id(evidence_input)
        if not evidence:
            print(error(f"Evidence not found: {evidence_input}"))
            return

        evidence_id = evidence.get('id')
        print(success(f"Found evidence: {evidence.get('name')}"))

        # Confirm
        print(info("\n" + "-" * 60))
        print(bold("Association Summary:"))
        print(f"  Program:  {selected_project.get('name')}")
        print(f"  Control:  {ctrl_display}")
        print(f"  Evidence: {evidence.get('name')}")
        print("-" * 60)

        confirm = input("\nCreate this association? (y/n): ").strip().lower()
        if confirm != 'y':
            print(warning("Cancelled."))
            return

        # Create association
        try:
            client.associate_evidence(
                evidence_id=evidence_id,
                subject_id=control_impl_id,
                subject_type="CONTROL_IMPLEMENTATION"
            )
            print(success("\nAssociation created successfully!"))
        except (ValidationError, APIError) as e:
            print(error(f"\nFailed to create association: {e}"))

    elif choice == '2':
        # Bulk association from CSV - simplified format
        print("\n" + bold("-" * 60))
        print(bold("BULK ASSOCIATION FROM CSV"))
        print("-" * 60)

        print("\nCSV file format (columns):")
        print("  program_name  - Name of the program (e.g., 'FedRAMP Rev 5')")
        print("  evidence_name - Name of the evidence")
        print("  control       - Control ID (e.g., 'AC-1')")
        print("\nExample:")
        print("  program_name,evidence_name,control")
        print("  FedRAMP Rev 5,User Access Review,AC-1")
        print("  FedRAMP Rev 5,Account Management Policy,AC-2")

        # Use file picker on macOS, otherwise fall back to manual entry
        if platform.system() == "Darwin":
            print(info("\nOpening file picker..."))
            file_path = pick_file(
                title="Select CSV File for Bulk Association",
                file_types=["csv"]
            )
            if file_path:
                print(f"Selected: {file_path}")
        else:
            file_path = input("\nEnter CSV file path: ").strip()

        if not file_path:
            print(warning("Cancelled."))
            return

        try:
            associations = read_csv_file(Path(file_path))

            if not associations:
                print(warning("No associations found in file."))
                return

            print(f"\nFound {bold(str(len(associations)))} association(s) to process")

            # Preview first few
            print("\nPreview:")
            for idx, assoc in enumerate(associations[:3], 1):
                prog = assoc.get("program_name", assoc.get("programname", "N/A"))
                ctrl = assoc.get("control", "N/A")
                ev = assoc.get("evidence_name", assoc.get("evidencename", "N/A"))
                print(f"  {idx}. {prog} / {ctrl} / {ev}")
            if len(associations) > 3:
                print(f"  ... and {len(associations) - 3} more")

            confirm = input("\nProceed with associations? (y/n): ").strip().lower()
            if confirm != 'y':
                print(warning("Cancelled."))
                return

            # Pre-fetch data for lookups
            print(info("\nFetching data for lookups..."))

            # Fetch all evidence
            try:
                all_evidence = client.get_all_evidence()
                evidence_by_name = {}
                for ev in all_evidence:
                    name = ev.get('name', '').lower()
                    if name:
                        evidence_by_name[name] = ev
                print(f"  Loaded {len(all_evidence)} evidence record(s)")
            except APIError as e:
                print(error(f"Failed to fetch evidence: {e}"))
                return

            # Fetch all projects
            try:
                projects = client.get_projects()
                projects_by_name = {}
                for proj in projects:
                    name = proj.get('name', '').lower()
                    if name:
                        projects_by_name[name] = proj
                print(f"  Loaded {len(projects)} program(s)")
            except APIError as e:
                print(error(f"Failed to fetch programs: {e}"))
                return

            # Cache for control implementations by project
            control_impls_cache = {}

            # Process associations
            created = 0
            failed = 0
            failed_items = []

            for idx, assoc in enumerate(associations, 1):
                program_name = assoc.get("program_name", assoc.get("programname", ""))
                control_name = assoc.get("control", "")
                evidence_name = assoc.get("evidence_name", assoc.get("evidencename", ""))

                row_label = f"[{idx}/{len(associations)}]"

                # Resolve program
                project = projects_by_name.get(program_name.lower())
                if not project:
                    # Try partial match
                    for name, proj in projects_by_name.items():
                        if program_name.lower() in name:
                            project = proj
                            break

                if not project:
                    failed += 1
                    failed_items.append({"row": idx, "error": f"Program not found: {program_name}"})
                    print(error(f"  {row_label} Failed: Program not found: {program_name}"))
                    continue

                project_id = project.get('id')

                # Get control implementations for this project (cache)
                if project_id not in control_impls_cache:
                    try:
                        control_impls_cache[project_id] = client.get_control_implementations(project_id)
                    except APIError as e:
                        failed += 1
                        failed_items.append({"row": idx, "error": f"Failed to fetch controls: {e}"})
                        print(error(f"  {row_label} Failed: Could not fetch controls for {program_name}"))
                        continue

                control_impls = control_impls_cache[project_id]

                # Resolve control
                control_impl = None
                control_name_lower = control_name.lower().strip()

                for ci in control_impls:
                    # Match on control field
                    if ci.get('control', '').lower() == control_name_lower:
                        control_impl = ci
                        break
                    # Match on control + requirement
                    full_name = f"{ci.get('control', '')} {ci.get('requirement', '')}".lower().strip()
                    if full_name == control_name_lower:
                        control_impl = ci
                        break

                if not control_impl:
                    # Try partial match
                    for ci in control_impls:
                        if control_name_lower in ci.get('control', '').lower():
                            control_impl = ci
                            break

                if not control_impl:
                    failed += 1
                    failed_items.append({"row": idx, "error": f"Control not found: {control_name}"})
                    print(error(f"  {row_label} Failed: Control not found: {control_name}"))
                    continue

                control_impl_id = control_impl.get('id')

                # Resolve evidence
                evidence = evidence_by_name.get(evidence_name.lower())
                if not evidence:
                    # Try partial match
                    for name, ev in evidence_by_name.items():
                        if evidence_name.lower() in name:
                            evidence = ev
                            break

                if not evidence:
                    failed += 1
                    failed_items.append({"row": idx, "error": f"Evidence not found: {evidence_name}"})
                    print(error(f"  {row_label} Failed: Evidence not found: {evidence_name}"))
                    continue

                evidence_id = evidence.get('id')

                # Create association
                try:
                    client.associate_evidence(
                        evidence_id=evidence_id,
                        subject_id=control_impl_id,
                        subject_type="CONTROL_IMPLEMENTATION"
                    )
                    created += 1
                    ctrl_display = control_impl.get('control', control_name)
                    print(success(f"  {row_label} Associated: {evidence_name[:20]}... -> {ctrl_display}"))
                except (ValidationError, APIError) as e:
                    failed += 1
                    failed_items.append({"row": idx, "error": str(e)})
                    print(error(f"  {row_label} Failed: {e}"))

            # Summary
            print("\n" + bold("=" * 60))
            print(bold("Association Summary:"))
            print(f"  Total:   {len(associations)}")
            print(f"  Created: {success(str(created))}")
            if failed > 0:
                print(f"  Failed:  {error(str(failed))}")
            print(bold("=" * 60))

        except FileNotFoundError:
            print(error(f"\nFile not found: {file_path}"))
        except Exception as e:
            print(error(f"\nError: {e}"))

    elif choice == '3':
        # Manual ID entry mode (original functionality)
        print("\n" + bold("-" * 60))
        print(bold("ASSOCIATE BY IDs"))
        print("-" * 60)

        # Get evidence ID or name
        print("\nYou can enter either an Evidence ID or Evidence Name.")
        search_term = input("Enter Evidence ID or Name: ").strip()
        if not search_term:
            print(warning("Cancelled."))
            return

        # Find evidence by name or ID
        print(info("Searching for evidence..."))
        evidence = find_evidence_by_name_or_id(search_term)

        if not evidence:
            print(error(f"Evidence not found: {search_term}"))
            return

        evidence_id = evidence.get('id')
        print(success(f"Found evidence: {evidence.get('name')} (ID: {evidence_id[:8]}...)"))

        # Get subject type
        print("\nSubject Type:")
        print("  1. Control Implementation (default)")
        print("  2. Solution Capability")

        type_choice = input("\nSelect subject type [1]: ").strip()
        if type_choice == '2':
            subject_type = "SOLUTION_CAPABILITY"
        else:
            subject_type = "CONTROL_IMPLEMENTATION"

        # Get subject IDs
        print(f"\nEnter {subject_type} ID(s) to associate with.")
        print("You can enter multiple IDs separated by spaces or commas.")
        subject_input = input("\nSubject ID(s): ").strip()

        if not subject_input:
            print(warning("Cancelled."))
            return

        # Parse subject IDs (split by space or comma)
        subject_ids = [s.strip() for s in subject_input.replace(',', ' ').split() if s.strip()]

        if not subject_ids:
            print(warning("No valid subject IDs provided."))
            return

        # Confirm
        print(info(f"\nWill associate evidence '{evidence.get('name', evidence_id)}' with:"))
        print(f"  Subject Type: {subject_type}")
        print(f"  Subject IDs:  {len(subject_ids)} ID(s)")
        for sid in subject_ids[:5]:  # Show first 5
            print(f"    - {sid}")
        if len(subject_ids) > 5:
            print(f"    ... and {len(subject_ids) - 5} more")

        confirm = input("\nProceed with association? (y/n): ").strip().lower()
        if confirm != 'y':
            print(warning("Cancelled."))
            return

        # Process associations
        created = 0
        failed = 0
        failed_items = []

        for idx, subject_id in enumerate(subject_ids, 1):
            try:
                client.associate_evidence(
                    evidence_id=evidence_id,
                    subject_id=subject_id,
                    subject_type=subject_type
                )
                created += 1
                print(success(f"  [{idx}/{len(subject_ids)}] Associated: {subject_id}"))
            except (ValidationError, APIError) as e:
                failed += 1
                failed_items.append({"subject_id": subject_id, "error": str(e)})
                print(error(f"  [{idx}/{len(subject_ids)}] Failed: {subject_id} - {e}"))

        # Summary
        print("\n" + bold("=" * 60))
        print(bold("Association Summary:"))
        print(f"  Total:   {len(subject_ids)}")
        print(f"  Created: {success(str(created))}")
        if failed > 0:
            print(f"  Failed:  {error(str(failed))}")
        print(bold("=" * 60))

    else:
        print(error("Invalid option."))


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
            associate_evidence_interactive()
        elif choice == '10':
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
