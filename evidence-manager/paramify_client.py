#!/usr/bin/env python3
"""
Paramify API Client
Shared module for interacting with the Paramify API.
"""

import csv
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import requests
from dotenv import dotenv_values

# Determine the directory where this module lives
MODULE_DIR = Path(__file__).parent.resolve()


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY output)."""
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.BOLD = ''
        cls.RESET = ''


# Check if stdout is a TTY
if not sys.stdout.isatty():
    Colors.disable()


def success(msg: str) -> str:
    """Format a success message."""
    return f"{Colors.GREEN}{msg}{Colors.RESET}"


def error(msg: str) -> str:
    """Format an error message."""
    return f"{Colors.RED}{msg}{Colors.RESET}"


def warning(msg: str) -> str:
    """Format a warning message."""
    return f"{Colors.YELLOW}{msg}{Colors.RESET}"


def info(msg: str) -> str:
    """Format an info message."""
    return f"{Colors.CYAN}{msg}{Colors.RESET}"


def bold(msg: str) -> str:
    """Format a bold message."""
    return f"{Colors.BOLD}{msg}{Colors.RESET}"


class APIError(Exception):
    """Exception raised for API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class DuplicateError(Exception):
    """Exception raised when duplicate evidence is detected."""
    def __init__(self, message: str, existing_evidence: Dict[str, Any]):
        self.message = message
        self.existing_evidence = existing_evidence
        super().__init__(self.message)


@dataclass
class ProgressInfo:
    """Information about bulk operation progress."""
    current: int
    total: int
    item_name: str
    status: str  # 'processing', 'success', 'skipped', 'failed'


class ParamifyClient:
    """Client for interacting with the Paramify API."""

    DEFAULT_TIMEOUT = 30
    CONNECTION_TEST_TIMEOUT = 10  # Shorter timeout for connection test
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None, env_path: Optional[Path] = None):
        """
        Initialize the Paramify client.

        Args:
            api_url: API base URL (overrides .env)
            api_key: API key (overrides .env)
            env_path: Path to .env file (defaults to module directory)
        """
        # Load from .env if not provided
        env_file = env_path or (MODULE_DIR / ".env")
        config = dotenv_values(env_file) if env_file.exists() else {}

        self.api_url = api_url or config.get("PARAMIFY_API_URL")
        self.api_key = api_key or config.get("PARAMIFY_API_KEY")
        self.workspace_name = config.get("PARAMIFY_WORKSPACE_NAME")
        self.timeout = self.DEFAULT_TIMEOUT

        # Cache for existing evidence (used for duplicate checking)
        self._evidence_cache: Optional[List[Dict[str, Any]]] = None

    @property
    def headers(self) -> Dict[str, str]:
        """Get the headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def validate_config(self) -> bool:
        """
        Validate that the API configuration is set.

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If configuration is missing or invalid
        """
        if not self.api_key:
            raise ValidationError("PARAMIFY_API_KEY is not set. Add it to your .env file.")
        if not self.api_url:
            raise ValidationError("PARAMIFY_API_URL is not set. Add it to your .env file.")
        return True

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection and validate credentials.

        Returns:
            Dictionary with connection status and info

        Raises:
            APIError: If connection fails
        """
        self.validate_config()

        # Use shorter timeout for connection test
        original_timeout = self.timeout
        self.timeout = self.CONNECTION_TEST_TIMEOUT

        try:
            # Quick GET request with limit=1 to validate auth without fetching all data
            url = f"{self.api_url}/evidence"
            response = requests.get(url, headers=self.headers, timeout=self.timeout, params={"limit": 1})
            response.raise_for_status()

            return {
                "success": True,
                "message": "Connection successful",
                "api_url": self.api_url
            }
        except requests.exceptions.Timeout:
            raise APIError(f"Connection timed out after {self.timeout}s. Check your network or API URL.")
        except requests.exceptions.ConnectionError:
            raise APIError(f"Could not connect to {self.api_url}. Check your network or API URL.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise APIError("Invalid API key. Please check your credentials.", 401)
            elif e.response.status_code == 403:
                raise APIError("Access forbidden. Your API key may not have the required permissions.", 403)
            raise APIError(f"Connection failed: {e}", e.response.status_code)
        finally:
            self.timeout = original_timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests

        Returns:
            Response JSON data

        Raises:
            APIError: If the request fails after retries
        """
        url = f"{self.api_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("headers", self.headers)

        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json() if response.text else {}

            except requests.exceptions.HTTPError as e:
                last_error = APIError(
                    f"API request failed: {e}",
                    status_code=e.response.status_code if e.response else None,
                    response_text=e.response.text if e.response else None
                )
                # Don't retry client errors (4xx)
                if e.response and 400 <= e.response.status_code < 500:
                    raise last_error

            except requests.exceptions.ConnectionError as e:
                last_error = APIError(f"Connection error: {e}")

            except requests.exceptions.Timeout as e:
                last_error = APIError(f"Request timed out after {self.timeout}s")

            except requests.exceptions.RequestException as e:
                last_error = APIError(f"Request failed: {e}")

            # Wait before retry
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.RETRY_DELAY * (attempt + 1))

        raise last_error

    # =========================================================================
    # Evidence CRUD Operations
    # =========================================================================

    def get_all_evidence(self, use_cache: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch all evidence records.

        Args:
            use_cache: If True, return cached results if available

        Returns:
            List of evidence records
        """
        if use_cache and self._evidence_cache is not None:
            return self._evidence_cache

        data = self._request("GET", "/evidence")
        self._evidence_cache = data.get("evidences", [])
        return self._evidence_cache

    def get_evidence(self, evidence_id: str) -> Dict[str, Any]:
        """
        Get a single evidence record by ID.

        Args:
            evidence_id: The evidence ID

        Returns:
            Evidence record data

        Raises:
            APIError: If evidence not found or request fails
        """
        return self._request("GET", f"/evidence/{evidence_id}")

    def create_evidence(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new evidence record.

        Args:
            evidence_data: Evidence data dictionary

        Returns:
            Created evidence record

        Raises:
            ValidationError: If required fields are missing
            APIError: If creation fails
        """
        payload = self._build_evidence_payload(evidence_data)

        if "name" not in payload:
            raise ValidationError("Evidence record must have a 'name' field")

        return self._request("POST", "/evidence", json=payload)

    def update_evidence(self, evidence_id: str, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing evidence record.

        Args:
            evidence_id: The evidence ID to update
            evidence_data: Updated evidence data

        Returns:
            Updated evidence record

        Raises:
            APIError: If update fails
        """
        payload = self._build_evidence_payload(evidence_data)
        return self._request("PATCH", f"/evidence/{evidence_id}", json=payload)

    def delete_evidence(self, evidence_id: str) -> bool:
        """
        Delete an evidence record.

        Args:
            evidence_id: The evidence ID to delete

        Returns:
            True if deleted successfully

        Raises:
            APIError: If deletion fails
        """
        self._request("DELETE", f"/evidence/{evidence_id}")
        # Invalidate cache
        self._evidence_cache = None
        return True

    def associate_evidence(
        self,
        evidence_id: str,
        subject_id: str,
        subject_type: str = "CONTROL_IMPLEMENTATION",
        association_type: str = "CONNECT"
    ) -> Dict[str, Any]:
        """
        Associate evidence with a subject (control implementation or solution capability).

        Args:
            evidence_id: The evidence ID to associate
            subject_id: The ID of the subject to associate with
            subject_type: Type of subject - "CONTROL_IMPLEMENTATION" or "SOLUTION_CAPABILITY"
            association_type: Type of association - typically "CONNECT"

        Returns:
            API response data

        Raises:
            APIError: If association fails
            ValidationError: If invalid subject_type provided
        """
        valid_subject_types = ["CONTROL_IMPLEMENTATION", "SOLUTION_CAPABILITY"]
        if subject_type.upper() not in valid_subject_types:
            raise ValidationError(f"Invalid subject_type: {subject_type}. Must be one of: {valid_subject_types}")

        payload = {
            "associationType": association_type.upper(),
            "subjectType": subject_type.upper(),
            "subjectId": subject_id
        }

        return self._request("POST", f"/evidence/{evidence_id}/associate", json=payload)

    # =========================================================================
    # Projects and Control Implementations
    # =========================================================================

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Fetch all projects (programs).

        Returns:
            List of project records with id, name, type, etc.
        """
        data = self._request("GET", "/projects")
        return data.get("projects", [])

    def get_control_implementations(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all control implementations for a project.

        Args:
            project_id: The project/program ID

        Returns:
            List of control implementation records with id, name, control, requirement, etc.
        """
        data = self._request("GET", f"/projects/{project_id}/control-implementations")
        return data.get("controlImplementations", [])

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def create_evidence_bulk(
        self,
        evidence_list: List[Dict[str, Any]],
        check_duplicates: bool = True,
        allow_duplicates: bool = False,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None
    ) -> Dict[str, Any]:
        """
        Create multiple evidence records with progress tracking.

        Args:
            evidence_list: List of evidence data dictionaries
            check_duplicates: Whether to check for duplicates
            allow_duplicates: Whether to allow creating duplicates
            progress_callback: Optional callback for progress updates

        Returns:
            Summary dictionary with created, skipped, failed counts and details
        """
        results = {
            "total": len(evidence_list),
            "created": 0,
            "skipped": 0,
            "failed": 0,
            "created_items": [],
            "skipped_items": [],
            "failed_items": []
        }

        # Fetch existing evidence for duplicate checking
        existing_evidence = []
        if check_duplicates:
            try:
                existing_evidence = self.get_all_evidence()
            except APIError:
                pass  # Continue without duplicate checking

        for idx, evidence_data in enumerate(evidence_list, 1):
            name = evidence_data.get("name", "N/A")

            # Notify progress
            if progress_callback:
                progress_callback(ProgressInfo(idx, len(evidence_list), name, "processing"))

            try:
                # Check for duplicates
                if existing_evidence:
                    duplicate = self.check_duplicate(evidence_data, existing_evidence)
                    if duplicate and not allow_duplicates:
                        results["skipped"] += 1
                        results["skipped_items"].append({
                            "name": name,
                            "reason": "duplicate",
                            "existing_id": duplicate.get("id")
                        })
                        if progress_callback:
                            progress_callback(ProgressInfo(idx, len(evidence_list), name, "skipped"))
                        continue

                # Create evidence
                result = self.create_evidence(evidence_data)
                results["created"] += 1
                results["created_items"].append(result)

                if progress_callback:
                    progress_callback(ProgressInfo(idx, len(evidence_list), name, "success"))

            except (ValidationError, APIError) as e:
                results["failed"] += 1
                results["failed_items"].append({
                    "name": name,
                    "error": str(e)
                })
                if progress_callback:
                    progress_callback(ProgressInfo(idx, len(evidence_list), name, "failed"))

        return results

    # =========================================================================
    # Export Operations
    # =========================================================================

    def export_to_csv(self, file_path: str, evidence_list: Optional[List[Dict[str, Any]]] = None) -> int:
        """
        Export evidence records to a CSV file.

        Args:
            file_path: Path to output CSV file
            evidence_list: List of evidence to export (fetches all if None)

        Returns:
            Number of records exported
        """
        if evidence_list is None:
            evidence_list = self.get_all_evidence()

        if not evidence_list:
            return 0

        fieldnames = ["name", "referenceId", "description", "instructions", "remarks", "automated", "id"]

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for evidence in evidence_list:
                writer.writerow(evidence)

        return len(evidence_list)

    def export_to_json(self, file_path: str, evidence_list: Optional[List[Dict[str, Any]]] = None, indent: int = 2) -> int:
        """
        Export evidence records to a JSON file.

        Args:
            file_path: Path to output JSON file
            evidence_list: List of evidence to export (fetches all if None)
            indent: JSON indentation level

        Returns:
            Number of records exported
        """
        if evidence_list is None:
            evidence_list = self.get_all_evidence()

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(evidence_list, f, indent=indent)

        return len(evidence_list)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def check_duplicate(self, evidence_data: Dict[str, Any], existing_evidence: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """
        Check if evidence already exists based on name or referenceId.

        Args:
            evidence_data: The evidence to check
            existing_evidence: List of existing evidence (fetches if None)

        Returns:
            The existing evidence record if duplicate found, None otherwise
        """
        if existing_evidence is None:
            existing_evidence = self.get_all_evidence(use_cache=True)

        normalized = normalize_keys(evidence_data)
        name = normalized.get("name", "").lower().strip()
        reference_id = get_reference_id(normalized)

        for existing in existing_evidence:
            # Check by referenceId first (if provided)
            if reference_id and existing.get("referenceId"):
                if str(existing["referenceId"]).strip() == reference_id:
                    return existing

            # Check by name (case-insensitive)
            if existing.get("name", "").lower().strip() == name:
                return existing

        return None

    def clear_cache(self):
        """Clear the evidence cache."""
        self._evidence_cache = None

    def _build_evidence_payload(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a clean payload for API requests."""
        normalized = normalize_keys(evidence_data)
        payload = {}

        # Map fields
        name = get_field_value(normalized, "name")
        if name:
            payload["name"] = name

        reference_id = get_reference_id(normalized)
        if reference_id:
            payload["referenceId"] = reference_id

        description = get_field_value(normalized, "description")
        if description:
            payload["description"] = description

        instructions = get_field_value(normalized, "instructions")
        if instructions:
            payload["instructions"] = instructions

        remarks = get_field_value(normalized, "remarks", "notes")
        if remarks:
            payload["remarks"] = remarks

        # Handle automated field
        if "automated" in normalized:
            automated_val = normalized["automated"]
            if isinstance(automated_val, bool):
                payload["automated"] = automated_val
            elif str(automated_val).lower() in ["true", "yes", "1"]:
                payload["automated"] = True
            elif str(automated_val).lower() in ["false", "no", "0"]:
                payload["automated"] = False

        return payload


# =============================================================================
# Utility Functions (used by multiple modules)
# =============================================================================

def normalize_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize dictionary keys to lowercase for case-insensitive matching."""
    return {k.lower().strip(): v for k, v in data.items()}


def get_reference_id(evidence_data: Dict[str, Any]) -> Optional[str]:
    """Extract referenceId from evidence data, checking various possible field names."""
    for key in ["referenceid", "reference_id", "id"]:
        if key in evidence_data and evidence_data[key]:
            return str(evidence_data[key]).strip()
    return None


def get_field_value(evidence_data: Dict[str, Any], *keys: str) -> Optional[str]:
    """Get the first non-empty value from evidence data for the given keys."""
    for key in keys:
        if key in evidence_data and evidence_data[key]:
            return str(evidence_data[key])
    return None


# =============================================================================
# File Reading Functions
# =============================================================================

def read_csv_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read evidence requests from a CSV file."""
    evidence_list = []

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any(row.values()):
                continue
            evidence_list.append(normalize_keys(row))

    return evidence_list


def read_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read evidence requests from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        return [normalize_keys(data)]
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        raise ValueError("JSON file must contain an object or array of objects")


def read_excel_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read evidence requests from an Excel file."""
    try:
        import pandas as pd
    except ImportError:
        print(error("Error: pandas is required to read Excel files."))
        print("Install it with: pip install pandas openpyxl")
        sys.exit(1)

    df = pd.read_excel(file_path, sheet_name=0)
    evidence_list = []

    for _, row in df.iterrows():
        if row.isna().all():
            continue
        row_dict = row.to_dict()
        row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
        evidence_list.append(normalize_keys(row_dict))

    return evidence_list


def read_evidence_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Read evidence requests from a file (CSV, JSON, or Excel).

    Args:
        file_path: Path to the input file

    Returns:
        List of evidence data dictionaries
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == '.csv':
        return read_csv_file(path)
    elif suffix == '.json':
        return read_json_file(path)
    elif suffix in ['.xlsx', '.xls']:
        return read_excel_file(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: .csv, .json, .xlsx, .xls")


# =============================================================================
# Progress Bar
# =============================================================================

class ProgressBar:
    """Simple progress bar for bulk operations."""

    def __init__(self, total: int, width: int = 40, prefix: str = "Progress"):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.created = 0
        self.skipped = 0
        self.failed = 0

    def update(self, progress_info: ProgressInfo):
        """Update the progress bar."""
        self.current = progress_info.current

        if progress_info.status == "success":
            self.created += 1
        elif progress_info.status == "skipped":
            self.skipped += 1
        elif progress_info.status == "failed":
            self.failed += 1

        self._render()

    def _render(self):
        """Render the progress bar."""
        percent = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * percent)
        bar = '=' * filled + '-' * (self.width - filled)

        status_parts = []
        if self.created > 0:
            status_parts.append(success(f"+{self.created}"))
        if self.skipped > 0:
            status_parts.append(warning(f"~{self.skipped}"))
        if self.failed > 0:
            status_parts.append(error(f"x{self.failed}"))

        status_str = " ".join(status_parts) if status_parts else ""

        sys.stdout.write(f"\r{self.prefix}: [{bar}] {self.current}/{self.total} {status_str}")
        sys.stdout.flush()

        if self.current >= self.total:
            print()  # New line when done

    def finish(self):
        """Complete the progress bar."""
        if self.current < self.total:
            self.current = self.total
            self._render()
