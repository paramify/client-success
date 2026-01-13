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
    bold,
    read_csv_file
)


def resolve_evidence_id(client, search_term: str) -> tuple:
    """
    Resolve an evidence name or ID to an actual evidence ID.

    Args:
        client: ParamifyClient instance
        search_term: Either an evidence ID (UUID) or evidence name

    Returns:
        Tuple of (evidence_id, evidence_name) or (None, None) if not found
    """
    # Check if it looks like a UUID (evidence ID)
    is_uuid = len(search_term) == 36 and search_term.count('-') == 4

    if is_uuid:
        # Try to fetch directly by ID
        try:
            evidence = client.get_evidence(search_term)
            return evidence.get('id'), evidence.get('name')
        except APIError:
            return None, None

    # Otherwise, search by name
    try:
        all_evidence = client.get_all_evidence()
    except APIError:
        return None, None

    # Exact match first (case-insensitive)
    for ev in all_evidence:
        if ev.get('name', '').lower() == search_term.lower():
            return ev.get('id'), ev.get('name')

    # Partial match (case-insensitive) - only if exactly one match
    matches = []
    for ev in all_evidence:
        if search_term.lower() in ev.get('name', '').lower():
            matches.append(ev)

    if len(matches) == 1:
        return matches[0].get('id'), matches[0].get('name')

    return None, None


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

  # Associate evidence with a single control implementation (by ID or name)
  python main.py --associate <evidence-id-or-name> --subject-id <control-impl-id>

  # Associate evidence with multiple control implementations
  python main.py --associate "User Access Review" --subject-id <id1> <id2> <id3>

  # Associate evidence with multiple solution capabilities
  python main.py --associate <evidence-id> --subject-id <id1> <id2> --subject-type SOLUTION_CAPABILITY

  # Bulk associate from CSV file (columns: evidence_id or evidence_name, subject_id, subject_type)
  python main.py --associate-file associations.csv
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

    # Associate evidence
    parser.add_argument(
        "--associate",
        type=str,
        metavar="EVIDENCE",
        help="Associate evidence with subject(s) - can be ID or name (use with --subject-id and --subject-type)"
    )
    parser.add_argument(
        "--subject-id",
        type=str,
        nargs='+',
        help="ID(s) of the subject(s) to associate with (space-separated for multiple)"
    )
    parser.add_argument(
        "--subject-type",
        type=str,
        choices=["CONTROL_IMPLEMENTATION", "SOLUTION_CAPABILITY"],
        default="CONTROL_IMPLEMENTATION",
        help="Type of subject (default: CONTROL_IMPLEMENTATION)"
    )
    parser.add_argument(
        "--associate-file",
        type=str,
        help="CSV file with associations (columns: evidence_id or evidence_name, subject_id, subject_type)"
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

    # Handle single/multiple association
    if args.associate:
        if not args.subject_id:
            print(error("Error: --subject-id is required when using --associate"), file=sys.stderr)
            sys.exit(1)

        # Resolve evidence ID (supports both ID and name)
        print(info(f"Looking up evidence: {args.associate}..."))
        evidence_id, evidence_name = resolve_evidence_id(client, args.associate)

        if not evidence_id:
            print(error(f"Evidence not found: {args.associate}"), file=sys.stderr)
            sys.exit(1)

        print(success(f"Found evidence: {evidence_name} (ID: {evidence_id[:8]}...)"))

        subject_ids = args.subject_id  # Already a list due to nargs='+'
        total = len(subject_ids)

        print(info(f"Associating with {total} {args.subject_type}(s)..."))

        if args.dry_run:
            print(warning("\n[DRY RUN MODE - No changes will be made]\n"))
            for idx, subject_id in enumerate(subject_ids, 1):
                print(f"  [{idx}/{total}] Would associate: {evidence_name} -> {args.subject_type} {subject_id}")
            print(f"\n{bold('Summary:')} {total} association(s) would be created")
            sys.exit(0)

        created = 0
        failed = 0
        failed_items = []

        for idx, subject_id in enumerate(subject_ids, 1):
            try:
                result = client.associate_evidence(
                    evidence_id=evidence_id,
                    subject_id=subject_id,
                    subject_type=args.subject_type
                )
                created += 1
                if args.verbose:
                    print(success(f"  [{idx}/{total}] Associated: {evidence_name} -> {args.subject_type} {subject_id}"))
            except (ValidationError, APIError) as e:
                failed += 1
                failed_items.append({"subject_id": subject_id, "error": str(e)})
                if args.verbose:
                    print(error(f"  [{idx}/{total}] Failed: {subject_id} - {e}"))

        # Summary
        if total > 1 or failed > 0:
            print()
            print(bold("=" * 50))
            print(bold("Association Summary:"))
            print(f"  Total:   {total}")
            print(f"  Created: {success(str(created))}")
            if failed > 0:
                print(f"  Failed:  {error(str(failed))}")
            print(bold("=" * 50))

            if failed_items:
                print(error("\nFailed items:"))
                for item in failed_items:
                    print(f"  - {item['subject_id']}: {item['error']}")
        else:
            print(success(f"Successfully associated evidence!"))

        sys.exit(0 if failed == 0 else 1)

    # Handle bulk associations from file
    if args.associate_file:
        print(info(f"Reading associations from: {args.associate_file}"))

        try:
            associations = read_csv_file(Path(args.associate_file))
            print(f"Found {bold(str(len(associations)))} association(s) to process")
        except Exception as e:
            print(error(f"Error reading file: {e}"), file=sys.stderr)
            sys.exit(1)

        if not associations:
            print(warning("No associations to process"))
            sys.exit(0)

        # Pre-fetch all evidence for name lookups
        print(info("Fetching evidence records for name lookups..."))
        try:
            all_evidence = client.get_all_evidence()
            evidence_by_name = {ev.get('name', '').lower(): ev for ev in all_evidence}
            evidence_by_id = {ev.get('id'): ev for ev in all_evidence}
            print(f"Found {len(all_evidence)} evidence record(s)")
        except APIError as e:
            print(error(f"Failed to fetch evidence: {e}"), file=sys.stderr)
            sys.exit(1)

        # Dry run for associations
        if args.dry_run:
            print(warning("\n[DRY RUN MODE - No changes will be made]\n"))
            for idx, assoc in enumerate(associations, 1):
                ev_id = assoc.get("evidence_id", assoc.get("evidenceid"))
                ev_name = assoc.get("evidence_name", assoc.get("evidencename"))
                subject_id = assoc.get("subject_id", assoc.get("subjectid", "N/A"))
                subject_type = assoc.get("subject_type", assoc.get("subjecttype", "CONTROL_IMPLEMENTATION"))
                display = ev_name or ev_id or "N/A"
                print(f"  [{idx}/{len(associations)}] Would associate: {display} -> {subject_type} {subject_id}")
            print(f"\n{bold('Summary:')} {len(associations)} association(s) would be processed")
            sys.exit(0)

        # Process associations
        created = 0
        failed = 0
        failed_items = []

        for idx, assoc in enumerate(associations, 1):
            # Support both evidence_id and evidence_name columns
            evidence_id = assoc.get("evidence_id", assoc.get("evidenceid"))
            evidence_name = assoc.get("evidence_name", assoc.get("evidencename"))
            subject_id = assoc.get("subject_id", assoc.get("subjectid"))
            subject_type = assoc.get("subject_type", assoc.get("subjecttype", "CONTROL_IMPLEMENTATION"))

            # Resolve evidence name to ID if needed
            if not evidence_id and evidence_name:
                # Look up by name
                ev = evidence_by_name.get(evidence_name.lower())
                if ev:
                    evidence_id = ev.get('id')
                else:
                    # Try partial match
                    for name, ev in evidence_by_name.items():
                        if evidence_name.lower() in name:
                            evidence_id = ev.get('id')
                            break
            elif evidence_id and evidence_id not in evidence_by_id:
                # Check if evidence_id is actually a name
                ev = evidence_by_name.get(evidence_id.lower())
                if ev:
                    evidence_id = ev.get('id')

            if not evidence_id or not subject_id:
                failed += 1
                failed_items.append({"row": idx, "error": "Missing or invalid evidence_id/evidence_name or subject_id"})
                if args.verbose:
                    print(error(f"  [{idx}/{len(associations)}] Failed: Missing or invalid IDs"))
                continue

            try:
                client.associate_evidence(
                    evidence_id=evidence_id,
                    subject_id=subject_id,
                    subject_type=subject_type.upper()
                )
                created += 1
                if args.verbose:
                    print(success(f"  [{idx}/{len(associations)}] Associated: {evidence_id[:8]}... -> {subject_type} {subject_id}"))
            except (ValidationError, APIError) as e:
                failed += 1
                failed_items.append({"row": idx, "evidence_id": evidence_id, "error": str(e)})
                if args.verbose:
                    print(error(f"  [{idx}/{len(associations)}] Failed: {evidence_id[:8]}... - {e}"))

        # Summary
        print()
        print(bold("=" * 50))
        print(bold("Association Summary:"))
        print(f"  Total:   {len(associations)}")
        print(f"  Created: {success(str(created))}")
        if failed > 0:
            print(f"  Failed:  {error(str(failed))}")
        print(bold("=" * 50))

        if args.verbose and failed_items:
            print(error("\nFailed items:"))
            for item in failed_items:
                print(f"  - Row {item.get('row')}: {item.get('error')}")

        sys.exit(0 if failed == 0 else 1)

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
