"""
Nessus API Client for retrieving scan results.
"""
import requests
import urllib3
import logging
from typing import Optional, Dict, List

# Disable SSL warnings for self-signed certificates (common with Nessus)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class NessusClient:
    """Client for interacting with Nessus API."""

    def __init__(self, url: str, access_key: str, secret_key: str, verify_ssl: bool = False):
        """
        Initialize Nessus client.

        Args:
            url: Nessus server URL (e.g., https://localhost:8834)
            access_key: Nessus API access key
            secret_key: Nessus API secret key
            verify_ssl: Whether to verify SSL certificates (default False for self-signed certs)
        """
        self.url = url.rstrip('/')
        self.access_key = access_key
        self.secret_key = secret_key
        self.verify_ssl = verify_ssl
        self.headers = {
            'X-ApiKeys': f'accessKey={access_key}; secretKey={secret_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to Nessus API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.url}{endpoint}"
        kwargs['verify'] = self.verify_ssl
        kwargs['headers'] = self.headers

        logger.debug(f"Making {method} request to {url}")
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def list_scans(self) -> List[Dict]:
        """
        List all scans.

        Returns:
            List of scan dictionaries
        """
        logger.info("Fetching list of scans from Nessus")
        response = self._make_request('GET', '/scans')
        data = response.json()
        return data.get('scans', [])

    def get_scan_details(self, scan_id: int) -> Dict:
        """
        Get detailed information about a specific scan.

        Args:
            scan_id: Scan ID

        Returns:
            Scan details dictionary
        """
        logger.info(f"Fetching details for scan ID: {scan_id}")
        response = self._make_request('GET', f'/scans/{scan_id}')
        return response.json()

    def export_scan(self, scan_id: int, format: str = 'nessus') -> int:
        """
        Request a scan export.

        Args:
            scan_id: Scan ID to export
            format: Export format ('nessus', 'csv', 'html', 'pdf', 'db')

        Returns:
            File ID for the export
        """
        logger.info(f"Requesting export for scan ID: {scan_id} in format: {format}")
        payload = {'format': format}
        response = self._make_request('POST', f'/scans/{scan_id}/export', json=payload)
        data = response.json()
        file_id = data.get('file')
        logger.info(f"Export requested, file ID: {file_id}")
        return file_id

    def check_export_status(self, scan_id: int, file_id: int) -> str:
        """
        Check the status of a scan export.

        Args:
            scan_id: Scan ID
            file_id: Export file ID

        Returns:
            Status string ('ready' or 'loading')
        """
        response = self._make_request('GET', f'/scans/{scan_id}/export/{file_id}/status')
        data = response.json()
        return data.get('status')

    def download_scan(self, scan_id: int, file_id: int) -> bytes:
        """
        Download exported scan file.

        Args:
            scan_id: Scan ID
            file_id: Export file ID

        Returns:
            Scan file content as bytes
        """
        logger.info(f"Downloading scan ID: {scan_id}, file ID: {file_id}")
        response = self._make_request('GET', f'/scans/{scan_id}/export/{file_id}/download')
        return response.content

    def get_scan_export(self, scan_id: int, format: str = 'nessus', max_retries: int = 30) -> bytes:
        """
        Export and download a scan (convenience method that handles the full workflow).

        Args:
            scan_id: Scan ID to export
            format: Export format ('nessus', 'csv', 'html', 'pdf', 'db')
            max_retries: Maximum number of times to check export status

        Returns:
            Scan file content as bytes

        Raises:
            TimeoutError: If export doesn't complete within max_retries
        """
        import time

        # Request export
        file_id = self.export_scan(scan_id, format)

        # Wait for export to be ready
        for i in range(max_retries):
            status = self.check_export_status(scan_id, file_id)
            if status == 'ready':
                logger.info(f"Export ready after {i+1} attempts")
                break
            logger.debug(f"Export status: {status}, waiting... ({i+1}/{max_retries})")
            time.sleep(2)
        else:
            raise TimeoutError(f"Export did not complete within {max_retries} retries")

        # Download the export
        return self.download_scan(scan_id, file_id)
