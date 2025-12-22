#!/usr/bin/env python3
"""
Evidence Set Creator for Paramify
Creates evidence records from CSV, JSON, or Excel files.
"""

import argparse
import json
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


def create_evidence_from_cli(args) -> dict:
    """Create evidence from command-line arguments."""
    evidence_data = {}

    if args.name:
        evidence_data["name"] = args.name
    if args.reference_id:
        evidence_data["referenceId"] = args.reference_id
    if args.description:
        evidence_data["description"] = args.description
    if args.instructions:
        evidence_data["instructions"] = args.instructions
    if args.remarks:
        evidence_data["remarks"] = args.remarks
    if args.automated is not None:
        evidence_data["automated"] = args.automated

    return normalize_keys(evidence_data)


def main():
    parser = argparse.ArgumentParser(
        description="Create evidence records in Paramify from various input sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create from a CSV file
  python main.py --file evidence_requests.csv

  # Create from a JSON file
  python main.py --file evidence_requests.json

  # Create from an Excel file
  python main.py --file evidence_requests.xlsx

  # Create a single evidence from command line
  python main.py --name "User Access Review" --description "Q1 2024 review" --automated

  # Dry run (don't actually create)
  python main.py --file evidence_requests.csv --dry-run

  # Export all evidence to CSV
  python main.py --export evidence_backup.csv

  # Export all evidence to JSON
  python main.py --export evidence_backup.json
        """
    )

    # File input
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to input file (CSV, JSON, or Excel)"
    )

    # Export
    parser.add_argument(
        "--export", "-e",
        type=str,
        help="Export all evidence to file (CSV or JSON based on extension)"
    )

    # Command-line input
    parser.add_argument(
        "--name", "-n",
        type=str,
        help="Name of the evidence (required if not using --file)"
    )
    parser.add_argument(
        "--reference-id", "-r",
        type=str,
        help="Custom reference ID for the evidence"
    )
    parser.add_argument(
        "--description", "-d",
        type=str,
        help="Description of the evidence"
    )
    parser.add_argument(
        "--instructions", "-i",
        type=str,
        help="Instructions for the evidence"
    )
    parser.add_argument(
        "--remarks",
        type=str,
        help="Additional remarks or notes"
    )
    parser.add_argument(
        "--automated",
        action="store_true",
        default=None,
        help="Mark evidence as automated"
    )

    # Options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow creating duplicate evidence (by default, duplicates are skipped)"
    )
    parser.add_argument(
        "--no-duplicate-check",
        action="store_true",
        help="Disable duplicate checking entirely (faster, but may create duplicates)"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar"
    )

    args = parser.parse_args()

    # Initialize client
    client = ParamifyClient()

    # Validate API configuration
    try:
        client.validate_config()
    except ValidationError as e:
        print(error(f"Error: {e}"), file=sys.stderr)
        sys.exit(1)

    # Test connection
    try:
        print(info("Validating API connection..."))
        client.test_connection()
        print(success("Connection successful!"))
        print()
    except APIError as e:
        print(error(f"Connection failed: {e}"), file=sys.stderr)
        sys.exit(1)

    # Handle export
    if args.export:
        export_path = Path(args.export)
        suffix = export_path.suffix.lower()

        print(info(f"Exporting evidence to {args.export}..."))

        try:
            if suffix == '.csv':
                count = client.export_to_csv(args.export)
            elif suffix == '.json':
                count = client.export_to_json(args.export)
            else:
                print(error(f"Unsupported export format: {suffix}. Use .csv or .json"), file=sys.stderr)
                sys.exit(1)

            print(success(f"Exported {count} evidence record(s) to {args.export}"))
            sys.exit(0)

        except Exception as e:
            print(error(f"Export failed: {e}"), file=sys.stderr)
            sys.exit(1)

    # Determine input source
    evidence_list = []

    if args.file:
        print(info(f"Reading evidence requests from: {args.file}"))
        try:
            evidence_list = read_evidence_file(args.file)
            print(f"Found {bold(str(len(evidence_list)))} evidence request(s)")
        except Exception as e:
            print(error(f"Error reading file: {e}"), file=sys.stderr)
            sys.exit(1)
    elif args.name:
        evidence_list = [create_evidence_from_cli(args)]
    else:
        parser.print_help()
        print(error("\nError: Either --file, --name, or --export is required"), file=sys.stderr)
        sys.exit(1)

    if not evidence_list:
        print(warning("No evidence requests to process"))
        sys.exit(0)

    # Dry run mode
    if args.dry_run:
        print(warning("\n[DRY RUN MODE - No changes will be made]\n"))

        # Fetch existing for duplicate detection preview
        existing_evidence = []
        if not args.no_duplicate_check:
            try:
                existing_evidence = client.get_all_evidence()
            except APIError:
                pass

        for idx, evidence_data in enumerate(evidence_list, 1):
            name = evidence_data.get("name", "N/A")
            duplicate = None

            if existing_evidence:
                duplicate = client.check_duplicate(evidence_data, existing_evidence)

            if duplicate and not args.allow_duplicates:
                print(warning(f"  [{idx}/{len(evidence_list)}] Would skip (duplicate): {name}"))
            else:
                print(success(f"  [{idx}/{len(evidence_list)}] Would create: {name}"))

            if args.verbose:
                print(f"      Data: {json.dumps(evidence_data, indent=2)}")

        print(f"\n{bold('Summary:')} {len(evidence_list)} record(s) would be processed")
        sys.exit(0)

    # Progress callback
    progress_bar = None
    if not args.no_progress and len(evidence_list) > 1:
        progress_bar = ProgressBar(len(evidence_list), prefix="Creating")

    def progress_callback(info: ProgressInfo):
        if progress_bar:
            progress_bar.update(info)
        elif args.verbose:
            status_symbol = {
                "success": success("+"),
                "skipped": warning("~"),
                "failed": error("x"),
                "processing": info("...")
            }.get(info.status, "?")
            print(f"  {status_symbol} [{info.current}/{info.total}] {info.item_name}")

    # Fetch existing evidence for duplicate checking
    existing_evidence = []
    if not args.no_duplicate_check:
        try:
            print(info("Fetching existing evidence for duplicate checking..."))
            existing_evidence = client.get_all_evidence()
            print(f"Found {len(existing_evidence)} existing record(s)")
        except APIError as e:
            print(warning(f"Warning: Could not fetch existing evidence: {e}"))
            print(warning("Continuing without duplicate checking..."))

    print()

    # Process evidence
    results = client.create_evidence_bulk(
        evidence_list,
        check_duplicates=not args.no_duplicate_check,
        allow_duplicates=args.allow_duplicates,
        progress_callback=progress_callback
    )

    # Summary
    print()
    print(bold("=" * 50))
    print(bold("Summary:"))
    print(f"  Total:   {results['total']}")
    print(f"  Created: {success(str(results['created']))}")
    if results['skipped'] > 0:
        print(f"  Skipped: {warning(str(results['skipped']))} (duplicates)")
    if results['failed'] > 0:
        print(f"  Failed:  {error(str(results['failed']))}")
    print(bold("=" * 50))

    # Show failures if verbose
    if args.verbose and results['failed_items']:
        print(error("\nFailed items:"))
        for item in results['failed_items']:
            print(f"  - {item['name']}: {item['error']}")

    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()
