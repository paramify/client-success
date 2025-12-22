"""
GitHub API Client for retrieving Nessus scan files from repositories.
"""
import requests
import base64
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API to fetch Nessus scan files."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token (optional, for private repos or higher rate limits)
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        if token:
            self.headers['Authorization'] = f'Bearer {token}'

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to GitHub API.

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
        kwargs['headers'] = self.headers

        logger.debug(f"Making {method} request to {url}")
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    def list_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main"
    ) -> List[Dict]:
        """
        List contents of a directory in a repository.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            path: Path within the repository (empty string for root)
            ref: Branch, tag, or commit SHA (default: "main")

        Returns:
            List of file/directory objects
        """
        logger.info(f"Listing contents of {owner}/{repo}/{path} (ref: {ref})")
        params = {'ref': ref}
        response = self._make_request(
            'GET',
            f'/repos/{owner}/{repo}/contents/{path}',
            params=params
        )
        return response.json()

    def find_nessus_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main",
        recursive: bool = True
    ) -> List[Dict]:
        """
        Find all .nessus files in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path (default: root)
            ref: Branch/tag/commit
            recursive: Search subdirectories (default: True)

        Returns:
            List of .nessus file objects with metadata
        """
        return self.find_scan_files(owner, repo, path, ref, recursive, file_types=['.nessus'])

    def find_scan_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main",
        recursive: bool = True,
        file_types: List[str] = None
    ) -> List[Dict]:
        """
        Find all scan files (Nessus and CSV) in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path (default: root)
            ref: Branch/tag/commit
            recursive: Search subdirectories (default: True)
            file_types: List of file extensions to search for (default: ['.nessus', '.csv'])

        Returns:
            List of scan file objects with metadata
        """
        if file_types is None:
            file_types = ['.nessus', '.csv']

        scan_files = []

        try:
            contents = self.list_repository_contents(owner, repo, path, ref)

            for item in contents:
                if item['type'] == 'file':
                    # Check if file has any of the target extensions
                    if any(item['name'].lower().endswith(ext) for ext in file_types):
                        # Determine file type
                        file_type = None
                        for ext in file_types:
                            if item['name'].lower().endswith(ext):
                                file_type = ext.lstrip('.')
                                break

                        scan_files.append({
                            'name': item['name'],
                            'path': item['path'],
                            'size': item['size'],
                            'sha': item['sha'],
                            'download_url': item.get('download_url'),
                            'url': item['url'],
                            'type': file_type
                        })
                elif item['type'] == 'dir' and recursive:
                    # Recursively search subdirectories
                    subdir_files = self.find_scan_files(
                        owner, repo, item['path'], ref, recursive, file_types
                    )
                    scan_files.extend(subdir_files)

        except Exception as e:
            logger.warning(f"Error accessing {path}: {e}")

        return scan_files

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> bytes:
        """
        Get the content of a file from the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path within repository
            ref: Branch/tag/commit

        Returns:
            File content as bytes
        """
        logger.info(f"Fetching file {owner}/{repo}/{path} (ref: {ref})")

        params = {'ref': ref}
        response = self._make_request(
            'GET',
            f'/repos/{owner}/{repo}/contents/{path}',
            params=params
        )

        data = response.json()

        # GitHub API returns file content base64-encoded
        if data.get('encoding') == 'base64':
            content = base64.b64decode(data['content'])
            logger.info(f"Downloaded file: {len(content)} bytes")
            return content
        else:
            raise ValueError(f"Unsupported encoding: {data.get('encoding')}")

    def download_file_direct(self, download_url: str) -> bytes:
        """
        Download file directly using the download URL.

        Args:
            download_url: Direct download URL from GitHub

        Returns:
            File content as bytes
        """
        logger.info(f"Downloading file from {download_url}")
        response = requests.get(download_url)
        response.raise_for_status()
        return response.content

    @staticmethod
    def parse_github_url(url: str) -> Dict[str, str]:
        """
        Parse a GitHub URL into owner, repo, path, and ref components.

        Supports formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo/tree/branch/path/to/file
        - https://github.com/owner/repo/blob/branch/path/to/file.nessus

        Args:
            url: GitHub URL

        Returns:
            Dict with owner, repo, path, and ref
        """
        import re

        # Remove trailing slashes and .git
        url = url.rstrip('/').replace('.git', '')

        # Match GitHub URL patterns
        pattern = r'github\.com/([^/]+)/([^/]+)(?:/(?:tree|blob)/([^/]+)(?:/(.*))?)?'
        match = re.search(pattern, url)

        if not match:
            raise ValueError(f"Invalid GitHub URL: {url}")

        owner, repo, ref, path = match.groups()
        return {
            'owner': owner,
            'repo': repo,
            'ref': ref or 'main',
            'path': path or ''
        }
