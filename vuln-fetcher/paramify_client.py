"""
Paramify API Client for managing assessments and intake uploads.
"""
import requests
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class ParamifyClient:
    """Client for interacting with Paramify API."""

    def __init__(self, api_key: str, base_url: str = "https://stage.paramify.com/api/v0"):
        """
        Initialize Paramify client.

        Args:
            api_key: Paramify API key (Bearer token)
            base_url: Paramify API base URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Paramify API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        # Merge headers, allowing custom headers to override defaults
        headers = self.headers.copy()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        kwargs['headers'] = headers

        logger.debug(f"Making {method} request to {url}")
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def list_assessments(self, params: Optional[Dict] = None) -> List[Dict]:
        """
        Get assessments with optional filtering.

        Args:
            params: Optional query parameters for filtering

        Returns:
            List of assessment dictionaries
        """
        logger.info("Fetching list of assessments from Paramify")
        response = self._make_request('GET', '/assessment', params=params)
        data = response.json()
        # The API returns assessments in an 'assessments' key
        return data.get('assessments', [])

    def get_assessment(self, assessment_id: str) -> Dict:
        """
        Get single assessment by ID.

        Args:
            assessment_id: Assessment UUID

        Returns:
            Assessment details dictionary
        """
        logger.info(f"Fetching assessment: {assessment_id}")
        response = self._make_request('GET', f'/assessment/{assessment_id}')
        return response.json()

    def upload_intake(
        self,
        assessment_id: str,
        file_content: bytes,
        filename: str,
        artifact_metadata: Optional[Dict] = None,
        effective_date: Optional[str] = None
    ) -> Dict:
        """
        Submit intake data for an assessment.

        Uploads a CSV, XML, JSON, or Nessus file as an artifact and attaches it
        to the intake on a vulnerability or configuration assessment.

        Args:
            assessment_id: Assessment UUID
            file_content: File content as bytes
            filename: Original filename (will be preserved)
            artifact_metadata: Optional metadata for creating the artifact
            effective_date: Optional effective date (format: YYYY-MM-DD)

        Returns:
            Response data from the API
        """
        logger.info(f"Uploading intake file '{filename}' to assessment: {assessment_id}")

        import json
        import io

        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if filename.lower().endswith('.csv'):
            content_type = 'text/csv'
        elif filename.lower().endswith('.json'):
            content_type = 'application/json'
        elif filename.lower().endswith('.xml'):
            content_type = 'application/xml'
        elif filename.lower().endswith('.nessus'):
            content_type = 'application/xml'  # .nessus files are XML

        # Prepare artifact metadata with effectiveDate
        artifact_data = artifact_metadata if artifact_metadata else {}
        if effective_date:
            artifact_data['effectiveDate'] = effective_date

        # Prepare multipart form data
        # The 'artifact' must be sent as a file-like part with application/json content-type
        artifact_json = json.dumps(artifact_data)
        files = {
            'file': (filename, file_content, content_type),
            'artifact': ('artifact.json', io.BytesIO(artifact_json.encode('utf-8')), 'application/json')
        }

        data = {}

        # Build custom headers for multipart/form-data
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }

        url = f"{self.base_url}/assessment/{assessment_id}/intake"
        logger.debug(f"Making POST request to {url}")
        logger.debug(f"Files: file={filename}, artifact={artifact_data}")
        logger.debug(f"Data: {data}")

        response = requests.post(url, files=files, data=data, headers=headers)

        # Log response details for debugging
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response body: {response.text}")

        response.raise_for_status()

        logger.info(f"Successfully uploaded intake file to assessment: {assessment_id}")
        return response.json()
