#!/usr/bin/env python3
"""
Nessus to Paramify Integration CLI
Imports Nessus scan results into Paramify assessments.
"""
import sys
import logging
import argparse
from typing import Optional, List, Dict
from config import Config
from integration import NessusParamifyIntegration
from github_client import GitHubClient
from paramify_client import ParamifyClient


def setup_logging(log_level: int = logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def format_scan_table(scans: List[Dict]) -> None:
    """Display scans in a formatted table."""
    if not scans:
        print("No scans found.")
        return

    print(f"{'#':<4} {'ID':<8} {'Name':<40} {'Status':<12}")
    print("-" * 70)

    for idx, scan in enumerate(scans, 1):
        scan_id = scan.get('id', 'N/A')
        name = scan.get('name', 'Unknown')[:38]
        status = scan.get('status', 'unknown')

        status_icon = "✓" if status == "completed" else "●"
        print(f"{idx:<4} {scan_id:<8} {name:<40} {status_icon} {status}")


def list_scans(integration: NessusParamifyIntegration, return_scans: bool = False):
    """List all available Nessus scans."""
    try:
        scans = integration.list_nessus_scans()
    except Exception as e:
        print(f"\n✗ Error fetching scans: {e}")
        sys.exit(1)

    if return_scans:
        return scans

    print("\n" + "=" * 70)
    print("  NESSUS SCANS")
    print("=" * 70 + "\n")

    format_scan_table(scans)
    print()


def format_assessment_table(assessments: List[Dict]) -> None:
    """Display assessments in a formatted table."""
    if not assessments:
        print("No assessments found.")
        return

    print(f"{'#':<4} {'Name':<30} {'Type':<16} {'Assessment ID'}")
    print("-" * 90)

    for idx, assessment in enumerate(assessments, 1):
        name = assessment.get('name', 'Unknown')[:28]
        assessment_type = assessment.get('type', 'UNKNOWN')
        type_display = assessment_type.replace('_', ' ').title()[:14]
        assessment_id = assessment.get('id', 'N/A')

        print(f"{idx:<4} {name:<30} {type_display:<16} {assessment_id}")


def list_assessments(integration: NessusParamifyIntegration, return_assessments: bool = False):
    """List all available Paramify assessments."""
    try:
        assessments = integration.list_paramify_assessments()
    except Exception as e:
        print(f"\n✗ Error fetching assessments: {e}")
        sys.exit(1)

    if return_assessments:
        return assessments

    print("\n" + "=" * 90)
    print("  PARAMIFY ASSESSMENTS")
    print("=" * 90 + "\n")

    format_assessment_table(assessments)
    print()


def import_scan_interactive(integration: NessusParamifyIntegration):
    """Interactive import with guided prompts."""
    print("\n" + "=" * 70)
    print("  IMPORT NESSUS SCAN TO PARAMIFY")
    print("=" * 70 + "\n")

    # Get available scans
    scans = list_scans(integration, return_scans=True)
    if not scans:
        print("✗ No scans available to import.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  SELECT NESSUS SCAN")
    print("=" * 70 + "\n")
    format_scan_table(scans)

    # Let user select scan
    while True:
        try:
            choice = input("\nEnter the # or ID of the scan to import (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            # Try as list number first
            if choice.isdigit() and 1 <= int(choice) <= len(scans):
                scan_id = scans[int(choice) - 1]['id']
                selected_scan = scans[int(choice) - 1]
                break
            # Try as scan ID
            elif choice.isdigit():
                scan_id = int(choice)
                selected_scan = next((s for s in scans if s['id'] == scan_id), None)
                if selected_scan:
                    break
                else:
                    print(f"✗ Scan ID {scan_id} not found. Please try again.")
            else:
                print("✗ Invalid input. Please enter a number.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)

    # Get available assessments
    assessments = list_assessments(integration, return_assessments=True)
    if not assessments:
        print("✗ No assessments available.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  SELECT PARAMIFY ASSESSMENT")
    print("=" * 70 + "\n")
    format_assessment_table(assessments)

    # Let user select assessment
    while True:
        try:
            choice = input("\nEnter the # of the assessment (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            if choice.isdigit() and 1 <= int(choice) <= len(assessments):
                assessment_id = assessments[int(choice) - 1]['id']
                selected_assessment = assessments[int(choice) - 1]
                break
            else:
                print(f"✗ Invalid choice. Please enter a number between 1 and {len(assessments)}.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)

    # Ask for effective date
    date_input = input("\nEffective date (YYYY-MM-DD) [press Enter for today]: ").strip()
    effective_date = date_input if date_input else None

    # Show summary
    print("\n" + "=" * 70)
    print("  IMPORT SUMMARY")
    print("=" * 70)
    print(f"\n  Scan:       {selected_scan.get('name')} (ID: {scan_id})")
    print(f"  Assessment: {selected_assessment.get('name')}")
    print(f"  Date:       {effective_date if effective_date else 'Today'}\n")

    # Confirm
    confirm = input("Proceed with import? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)

    print("\n⏳ Importing scan...")

    try:
        result = integration.import_scan_to_assessment(
            scan_id=scan_id,
            assessment_id=assessment_id,
            effective_date=effective_date
        )

        print("\n" + "=" * 70)
        print("  ✓ IMPORT SUCCESSFUL")
        print("=" * 70)

        if result.get('artifacts'):
            artifact = result['artifacts'][0]
            print(f"\n  Artifact ID:   {artifact.get('id')}")
            print(f"  File:          {artifact.get('originalFileName')}")
            print(f"  Effective:     {artifact.get('effectiveDate', 'N/A')[:10]}")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("  ✗ IMPORT FAILED")
        print("=" * 70)
        print(f"\n  Error: {e}\n")
        sys.exit(1)


def import_from_local_file_interactive():
    """Interactive local file import."""
    print("\n" + "=" * 70)
    print("  IMPORT FROM LOCAL FILE")
    print("=" * 70 + "\n")

    # Use macOS file picker if available, otherwise prompt for path
    file_path = None

    try:
        import subprocess
        script = '''
        set fileTypes to {"nessus", "csv", "public.comma-separated-values-text"}
        set selectedFile to choose file with prompt "Select a scan file (.nessus or .csv)" of type fileTypes
        return POSIX path of selectedFile
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            file_path = result.stdout.strip()
    except Exception:
        pass  # Fall back to manual input

    if not file_path:
        file_path = input("Enter the path to the scan file (.nessus or .csv): ").strip()
        # Handle drag-and-drop paths with escaped spaces
        file_path = file_path.replace("\\ ", " ").strip("'\"")

    if not file_path:
        print("✗ No file specified.")
        sys.exit(1)

    # Validate file exists and has correct extension
    from pathlib import Path
    path = Path(file_path)

    if not path.exists():
        print(f"✗ File not found: {file_path}")
        sys.exit(1)

    if path.suffix.lower() not in ['.nessus', '.csv']:
        print(f"✗ Invalid file type: {path.suffix}")
        print("  Supported formats: .nessus, .csv")
        sys.exit(1)

    file_size = path.stat().st_size
    print(f"\n✓ Selected: {path.name} ({file_size / 1024:.1f} KB)")

    # Get available assessments
    paramify_client = ParamifyClient(
        api_key=Config.PARAMIFY_API_KEY,
        base_url=Config.PARAMIFY_BASE_URL
    )

    try:
        assessments = paramify_client.list_assessments()
    except Exception as e:
        print(f"\n✗ Error fetching assessments: {e}")
        sys.exit(1)

    if not assessments:
        print("✗ No assessments available.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  SELECT PARAMIFY ASSESSMENT")
    print("=" * 70 + "\n")
    format_assessment_table(assessments)

    # Let user select assessment
    while True:
        try:
            choice = input("\nEnter the # of the assessment (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            if choice.isdigit() and 1 <= int(choice) <= len(assessments):
                assessment_id = assessments[int(choice) - 1]['id']
                selected_assessment = assessments[int(choice) - 1]
                break
            else:
                print(f"✗ Invalid choice. Please enter a number between 1 and {len(assessments)}.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)

    # Ask for effective date
    date_input = input("\nEffective date (YYYY-MM-DD) [press Enter for today]: ").strip()
    effective_date = date_input if date_input else None

    # Show summary
    print("\n" + "=" * 70)
    print("  IMPORT SUMMARY")
    print("=" * 70)
    print(f"\n  File:       {path.name}")
    print(f"  Size:       {file_size / 1024:.1f} KB")
    print(f"  Assessment: {selected_assessment.get('name')}")
    print(f"  Date:       {effective_date if effective_date else 'Today'}\n")

    # Confirm
    confirm = input("Proceed with import? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)

    print("\n⏳ Uploading to Paramify...")

    try:
        # Read file content
        with open(path, 'rb') as f:
            file_content = f.read()

        # Upload to Paramify
        result = paramify_client.upload_intake(
            assessment_id=assessment_id,
            file_content=file_content,
            filename=path.name,
            effective_date=effective_date
        )

        print("\n" + "=" * 70)
        print("  ✓ IMPORT SUCCESSFUL")
        print("=" * 70)

        if result.get('artifacts'):
            artifact = result['artifacts'][0]
            print(f"\n  Artifact ID:   {artifact.get('id')}")
            print(f"  File:          {artifact.get('originalFileName')}")
            print(f"  Effective:     {artifact.get('effectiveDate', 'N/A')[:10]}")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("  ✗ IMPORT FAILED")
        print("=" * 70)
        print(f"\n  Error: {e}\n")
        sys.exit(1)


def import_from_github_interactive():
    """Interactive GitHub file import."""
    print("\n" + "=" * 70)
    print("  IMPORT FROM GITHUB REPOSITORY")
    print("=" * 70 + "\n")

    # Get GitHub repo URL or details
    print("Enter GitHub repository information:")
    repo_input = input("  Repository (owner/repo or full URL): ").strip()

    if not repo_input:
        print("✗ Repository is required.")
        sys.exit(1)

    # Parse input
    try:
        if '/' in repo_input and 'github.com' not in repo_input:
            # Format: owner/repo
            parts = repo_input.split('/')
            owner, repo = parts[0], parts[1]
            ref = 'main'
            path = ''
        else:
            # Full URL
            import urllib.parse
            parsed = GitHubClient.parse_github_url(repo_input)
            owner = parsed['owner']
            repo = parsed['repo']
            ref = parsed['ref']
            # Decode URL-encoded path (e.g., %20 -> space)
            path = urllib.parse.unquote(parsed['path']) if parsed['path'] else ''
    except Exception as e:
        print(f"✗ Invalid repository format: {e}")
        sys.exit(1)

    # Optional: GitHub token for private repos
    token_input = input("  GitHub token (optional, press Enter to skip): ").strip()
    token = token_input if token_input else None

    # Optional: branch/ref
    if not path:
        ref_input = input(f"  Branch/tag (default: {ref}): ").strip()
        if ref_input:
            ref = ref_input

    github_client = GitHubClient(token=token)

    print(f"\n⏳ Searching for scan files (.nessus, .csv) in {owner}/{repo}...")

    try:
        scan_files = github_client.find_scan_files(owner, repo, path, ref)
    except Exception as e:
        print(f"\n✗ Error accessing repository: {e}")
        sys.exit(1)

    if not scan_files:
        print(f"✗ No scan files (.nessus or .csv) found in {owner}/{repo}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  SELECT SCAN FILE")
    print("=" * 70 + "\n")

    print(f"{'#':<4} {'File':<45} {'Type':<8} {'Size':<10}")
    print("-" * 70)

    for idx, file in enumerate(scan_files, 1):
        name = file['path'][-43:] if len(file['path']) > 43 else file['path']
        size_kb = file['size'] / 1024
        file_type = file.get('type', 'unknown').upper()
        print(f"{idx:<4} {name:<45} {file_type:<8} {size_kb:>6.1f} KB")

    # Let user select file
    while True:
        try:
            choice = input("\nEnter the # of the file to import (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            if choice.isdigit() and 1 <= int(choice) <= len(scan_files):
                selected_file = scan_files[int(choice) - 1]
                break
            else:
                print(f"✗ Invalid choice. Please enter a number between 1 and {len(scan_files)}.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)

    # Get available assessments
    paramify_client = ParamifyClient(
        api_key=Config.PARAMIFY_API_KEY,
        base_url=Config.PARAMIFY_BASE_URL
    )

    try:
        assessments = paramify_client.list_assessments()
    except Exception as e:
        print(f"\n✗ Error fetching assessments: {e}")
        sys.exit(1)

    if not assessments:
        print("✗ No assessments available.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  SELECT PARAMIFY ASSESSMENT")
    print("=" * 70 + "\n")
    format_assessment_table(assessments)

    # Let user select assessment
    while True:
        try:
            choice = input("\nEnter the # of the assessment (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                sys.exit(0)

            if choice.isdigit() and 1 <= int(choice) <= len(assessments):
                assessment_id = assessments[int(choice) - 1]['id']
                selected_assessment = assessments[int(choice) - 1]
                break
            else:
                print(f"✗ Invalid choice. Please enter a number between 1 and {len(assessments)}.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)

    # Ask for effective date
    date_input = input("\nEffective date (YYYY-MM-DD) [press Enter for today]: ").strip()
    effective_date = date_input if date_input else None

    # Show summary
    print("\n" + "=" * 70)
    print("  IMPORT SUMMARY")
    print("=" * 70)
    print(f"\n  File:       {selected_file['path']}")
    print(f"  From:       {owner}/{repo}@{ref}")
    print(f"  Assessment: {selected_assessment.get('name')}")
    print(f"  Date:       {effective_date if effective_date else 'Today'}\n")

    # Confirm
    confirm = input("Proceed with import? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        sys.exit(0)

    print("\n⏳ Downloading file from GitHub...")

    try:
        # Download file from GitHub
        file_content = github_client.get_file_content(owner, repo, selected_file['path'], ref)
        filename = selected_file['name']

        print(f"✓ Downloaded {len(file_content)} bytes")
        print("⏳ Uploading to Paramify...")

        # Upload to Paramify
        result = paramify_client.upload_intake(
            assessment_id=assessment_id,
            file_content=file_content,
            filename=filename,
            effective_date=effective_date
        )

        print("\n" + "=" * 70)
        print("  ✓ IMPORT SUCCESSFUL")
        print("=" * 70)

        if result.get('artifacts'):
            artifact = result['artifacts'][0]
            print(f"\n  Artifact ID:   {artifact.get('id')}")
            print(f"  File:          {artifact.get('originalFileName')}")
            print(f"  Effective:     {artifact.get('effectiveDate', 'N/A')[:10]}")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("  ✗ IMPORT FAILED")
        print("=" * 70)
        print(f"\n  Error: {e}\n")
        sys.exit(1)


def update_settings_interactive():
    """Interactive settings update."""
    print("\n" + "=" * 70)
    print("  UPDATE API SETTINGS")
    print("=" * 70 + "\n")

    # Show current settings (masked)
    def mask_key(key: str) -> str:
        if not key:
            return "(not set)"
        if len(key) <= 8:
            return "*" * len(key)
        return key[:4] + "*" * (len(key) - 8) + key[-4:]

    print("Current settings:")
    print(f"  1. Paramify API Key:    {mask_key(Config.PARAMIFY_API_KEY)}")
    print(f"  2. Paramify Base URL:   {Config.PARAMIFY_BASE_URL}")
    print(f"  3. Nessus URL:          {Config.NESSUS_URL}")
    print(f"  4. Nessus Access Key:   {mask_key(Config.NESSUS_ACCESS_KEY)}")
    print(f"  5. Nessus Secret Key:   {mask_key(Config.NESSUS_SECRET_KEY)}")
    print()
    print("  6. Back to main menu")
    print()

    while True:
        try:
            choice = input("Select setting to update (1-6): ").strip()

            if choice == '1':
                current = "(not set)" if not Config.PARAMIFY_API_KEY else "current value exists"
                new_value = input(f"Enter new Paramify API Key ({current}): ").strip()
                if new_value:
                    Config.save_to_env(PARAMIFY_API_KEY=new_value)
                    print("✓ Paramify API Key updated")
                else:
                    print("✗ No change (empty input)")

            elif choice == '2':
                print("\nSelect Paramify environment:")
                print("  1. Production  (app.paramify.com)")
                print("  2. Demo        (demo.paramify.com)")
                print("  3. Staging     (stage.paramify.com)")
                print("  4. Cancel")
                env_choice = input("\nEnter choice (1-4): ").strip()

                url_map = {
                    '1': 'https://app.paramify.com/api/v0',
                    '2': 'https://demo.paramify.com/api/v0',
                    '3': 'https://stage.paramify.com/api/v0'
                }

                if env_choice in url_map:
                    Config.save_to_env(PARAMIFY_BASE_URL=url_map[env_choice])
                    print(f"✓ Paramify Base URL updated to {url_map[env_choice]}")
                elif env_choice == '4':
                    print("Cancelled")
                else:
                    print("✗ Invalid choice")

            elif choice == '3':
                new_value = input(f"Enter new Nessus URL [{Config.NESSUS_URL}]: ").strip()
                if new_value:
                    Config.save_to_env(NESSUS_URL=new_value)
                    print("✓ Nessus URL updated")
                else:
                    print("✗ No change (empty input)")

            elif choice == '4':
                current = "(not set)" if not Config.NESSUS_ACCESS_KEY else "current value exists"
                new_value = input(f"Enter new Nessus Access Key ({current}): ").strip()
                if new_value:
                    Config.save_to_env(NESSUS_ACCESS_KEY=new_value)
                    print("✓ Nessus Access Key updated")
                else:
                    print("✗ No change (empty input)")

            elif choice == '5':
                current = "(not set)" if not Config.NESSUS_SECRET_KEY else "current value exists"
                new_value = input(f"Enter new Nessus Secret Key ({current}): ").strip()
                if new_value:
                    Config.save_to_env(NESSUS_SECRET_KEY=new_value)
                    print("✓ Nessus Secret Key updated")
                else:
                    print("✗ No change (empty input)")

            elif choice == '6':
                return

            else:
                print("✗ Invalid choice. Please enter a number between 1 and 6.")
                continue

            # After updating, show menu again
            print()
            update_settings_interactive()
            return

        except (KeyboardInterrupt, EOFError):
            print("\n")
            return


def unified_menu():
    """Unified menu for all import options."""
    print("\n" + "=" * 70)
    print("  PARAMIFY ASSESSMENTS INTEGRATION")
    print("=" * 70 + "\n")

    print("What would you like to do?\n")
    print("  1. Import from Nessus (live scan from your Nessus instance)")
    print("  2. Import from GitHub (scan files stored in a repository)")
    print("  3. Import from Local File (scan file on your computer)")
    print("  4. List Nessus scans")
    print("  5. List Paramify assessments")
    print("  6. Update API settings")
    print("  7. Exit")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-7): ").strip()

            if choice == '1':
                # Validate Paramify and Nessus configuration
                is_valid, missing = Config.validate()
                if not is_valid:
                    print(f"\n✗ Configuration error: Missing required Paramify credentials: {', '.join(missing)}")
                    print("\nPlease set PARAMIFY_API_KEY in your .env file")
                    sys.exit(1)

                is_valid_nessus, missing_nessus = Config.validate_nessus()
                if not is_valid_nessus:
                    print(f"\n✗ Configuration error: Missing Nessus credentials: {', '.join(missing_nessus)}")
                    print("\nPlease set the following in your .env file:")
                    for key in missing_nessus:
                        print(f"  - {key}")
                    sys.exit(1)

                integration = NessusParamifyIntegration(
                    nessus_url=Config.NESSUS_URL,
                    nessus_access_key=Config.NESSUS_ACCESS_KEY,
                    nessus_secret_key=Config.NESSUS_SECRET_KEY,
                    paramify_api_key=Config.PARAMIFY_API_KEY,
                    paramify_base_url=Config.PARAMIFY_BASE_URL
                )
                import_scan_interactive(integration)
                break

            elif choice == '2':
                # Only need Paramify credentials for GitHub import
                if not Config.PARAMIFY_API_KEY:
                    print("✗ Configuration error: PARAMIFY_API_KEY is required")
                    sys.exit(1)
                import_from_github_interactive()
                break

            elif choice == '3':
                # Only need Paramify credentials for local file import
                if not Config.PARAMIFY_API_KEY:
                    print("✗ Configuration error: PARAMIFY_API_KEY is required")
                    sys.exit(1)
                import_from_local_file_interactive()
                break

            elif choice == '4':
                is_valid_nessus, missing_nessus = Config.validate_nessus()
                if not is_valid_nessus:
                    print(f"\n✗ Configuration error: Missing Nessus credentials: {', '.join(missing_nessus)}")
                    print("\nPlease set the following in your .env file:")
                    for key in missing_nessus:
                        print(f"  - {key}")
                    sys.exit(1)

                integration = NessusParamifyIntegration(
                    nessus_url=Config.NESSUS_URL,
                    nessus_access_key=Config.NESSUS_ACCESS_KEY,
                    nessus_secret_key=Config.NESSUS_SECRET_KEY,
                    paramify_api_key=Config.PARAMIFY_API_KEY,
                    paramify_base_url=Config.PARAMIFY_BASE_URL
                )
                list_scans(integration)
                # Return to menu after listing
                input("\nPress Enter to return to the main menu...")
                unified_menu()
                return

            elif choice == '5':
                is_valid, missing = Config.validate()
                if not is_valid:
                    print(f"\n✗ Configuration error: Missing Paramify credentials: {', '.join(missing)}")
                    print("\nPlease set PARAMIFY_API_KEY in your .env file")
                    sys.exit(1)

                integration = NessusParamifyIntegration(
                    nessus_url=Config.NESSUS_URL,
                    nessus_access_key=Config.NESSUS_ACCESS_KEY,
                    nessus_secret_key=Config.NESSUS_SECRET_KEY,
                    paramify_api_key=Config.PARAMIFY_API_KEY,
                    paramify_base_url=Config.PARAMIFY_BASE_URL
                )
                list_assessments(integration)
                # Return to menu after listing
                input("\nPress Enter to return to the main menu...")
                unified_menu()
                return

            elif choice == '6':
                update_settings_interactive()
                # Return to menu after updating settings
                unified_menu()
                return

            elif choice == '7':
                print("\nGoodbye!")
                sys.exit(0)

            else:
                print("✗ Invalid choice. Please enter a number between 1 and 7.")

        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            sys.exit(0)


def import_scan(
    integration: NessusParamifyIntegration,
    scan_id: int,
    assessment_id: str,
    effective_date: Optional[str] = None
):
    """Import a Nessus scan into a Paramify assessment (non-interactive)."""
    print("\n⏳ Importing scan...")

    try:
        result = integration.import_scan_to_assessment(
            scan_id=scan_id,
            assessment_id=assessment_id,
            effective_date=effective_date
        )

        print("\n" + "=" * 70)
        print("  ✓ IMPORT SUCCESSFUL")
        print("=" * 70)

        if result.get('artifacts'):
            artifact = result['artifacts'][0]
            print(f"\n  Artifact ID:   {artifact.get('id')}")
            print(f"  File:          {artifact.get('originalFileName')}")
            print(f"  Effective:     {artifact.get('effectiveDate', 'N/A')[:10]}")
        print()

    except Exception as e:
        print("\n" + "=" * 70)
        print("  ✗ IMPORT FAILED")
        print("=" * 70)
        print(f"\n  Error: {e}\n")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Import Nessus scan results into Paramify assessments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (easiest!)
  python main.py import

  # Import from GitHub repository
  python main.py import-github

  # List all Nessus scans
  python main.py list-scans

  # List all Paramify assessments
  python main.py list-assessments

  # Import with specific IDs
  python main.py import --scan-id 123 --assessment-id abc-123-def

  # Import with an effective date
  python main.py import --scan-id 123 --assessment-id abc-123-def --effective-date 2025-01-15
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List scans command
    subparsers.add_parser('list-scans', help='List all available Nessus scans')

    # List assessments command
    subparsers.add_parser('list-assessments', help='List all available Paramify assessments')

    # Import command (can be interactive or with arguments)
    import_parser = subparsers.add_parser('import', help='Import a Nessus scan into a Paramify assessment')
    import_parser.add_argument('--scan-id', type=int, help='Nessus scan ID (interactive if not provided)')
    import_parser.add_argument('--assessment-id', type=str, help='Paramify assessment UUID (interactive if not provided)')
    import_parser.add_argument('--effective-date', type=str, help='Effective date (YYYY-MM-DD format)')

    # Import from GitHub command
    subparsers.add_parser('import-github', help='Import a .nessus or .csv file from a GitHub repository')

    # Import from local file command
    subparsers.add_parser('import-file', help='Import a .nessus or .csv file from your computer')

    # Settings command
    subparsers.add_parser('settings', help='Update API keys and URLs')

    args = parser.parse_args()

    # Setup logging (hide it for cleaner output)
    setup_logging(logging.WARNING)

    # If no command specified, show unified menu
    if args.command is None:
        unified_menu()
        return

    # Execute command
    if args.command == 'import-github':
        # Validate that we have Paramify credentials
        if not Config.PARAMIFY_API_KEY:
            print("✗ Configuration error: PARAMIFY_API_KEY is required")
            sys.exit(1)
        import_from_github_interactive()
    elif args.command == 'import-file':
        # Validate that we have Paramify credentials
        if not Config.PARAMIFY_API_KEY:
            print("✗ Configuration error: PARAMIFY_API_KEY is required")
            sys.exit(1)
        import_from_local_file_interactive()
    elif args.command == 'settings':
        update_settings_interactive()
    else:
        # Validate Paramify configuration (required for all commands)
        is_valid, missing = Config.validate()
        if not is_valid:
            print(f"✗ Configuration error: Missing required Paramify credentials: {', '.join(missing)}")
            print("\nPlease set PARAMIFY_API_KEY in your .env file")
            sys.exit(1)

        # Validate Nessus configuration for Nessus-specific commands
        if args.command in ['list-scans', 'import']:
            is_valid_nessus, missing_nessus = Config.validate_nessus()
            if not is_valid_nessus:
                print(f"✗ Configuration error: Missing Nessus credentials: {', '.join(missing_nessus)}")
                print("\nPlease set the following in your .env file:")
                for key in missing_nessus:
                    print(f"  - {key}")
                sys.exit(1)

        # Initialize integration
        integration = NessusParamifyIntegration(
            nessus_url=Config.NESSUS_URL,
            nessus_access_key=Config.NESSUS_ACCESS_KEY,
            nessus_secret_key=Config.NESSUS_SECRET_KEY,
            paramify_api_key=Config.PARAMIFY_API_KEY,
            paramify_base_url=Config.PARAMIFY_BASE_URL
        )

        # Execute Nessus-based commands
        if args.command == 'list-scans':
            list_scans(integration)
        elif args.command == 'list-assessments':
            list_assessments(integration)
        elif args.command == 'import':
            # Use interactive mode if no scan-id or assessment-id provided
            if args.scan_id is None or args.assessment_id is None:
                import_scan_interactive(integration)
            else:
                import_scan(
                    integration,
                    args.scan_id,
                    args.assessment_id,
                    args.effective_date
                )


if __name__ == '__main__':
    main()
