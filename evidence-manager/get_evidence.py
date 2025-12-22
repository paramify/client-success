#!/usr/bin/env python3
"""
Get Evidence from Paramify
Lists all evidence records from the configured workspace.
"""

import sys

from paramify_client import (
    ParamifyClient,
    ValidationError,
    APIError,
    success,
    error,
    info,
    bold
)


def main():
    """Fetch and display all evidence records."""
    # Initialize client
    client = ParamifyClient()

    # Validate configuration
    try:
        client.validate_config()
    except ValidationError as e:
        print(error(f"Error: {e}"), file=sys.stderr)
        sys.exit(1)

    # Test connection
    try:
        print(info(f"API URL: {client.api_url}"))
        print(info("Validating connection..."))
        client.test_connection()
        print(success("Connected!"))
        print()
    except APIError as e:
        print(error(f"Connection failed: {e}"), file=sys.stderr)
        sys.exit(1)

    # Fetch evidence
    try:
        evidences = client.get_all_evidence()

        print(f"Total evidence records: {bold(str(len(evidences)))}")
        print()
        print(f"{'Reference ID':<15} | {'Name'}")
        print("-" * 60)

        for e in evidences:
            ref_id = e.get("referenceId") or "N/A"
            name = e.get("name") or "N/A"
            print(f"{ref_id:<15} | {name}")

    except APIError as e:
        print(error(f"Error fetching evidence: {e}"), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
