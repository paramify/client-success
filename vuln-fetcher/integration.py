"""
Integration orchestration for Nessus to Paramify workflow.
"""
import logging
from typing import Optional
from nessus_client import NessusClient
from paramify_client import ParamifyClient

logger = logging.getLogger(__name__)


class NessusParamifyIntegration:
    """Orchestrates the integration between Nessus and Paramify."""

    def __init__(
        self,
        nessus_url: str,
        nessus_access_key: str,
        nessus_secret_key: str,
        paramify_api_key: str,
        paramify_base_url: str = "https://stage.paramify.com/api/v0"
    ):
        """
        Initialize the integration.

        Args:
            nessus_url: Nessus server URL
            nessus_access_key: Nessus API access key
            nessus_secret_key: Nessus API secret key
            paramify_api_key: Paramify API key
            paramify_base_url: Paramify API base URL
        """
        self.nessus_client = NessusClient(
            url=nessus_url,
            access_key=nessus_access_key,
            secret_key=nessus_secret_key
        )
        self.paramify_client = ParamifyClient(
            api_key=paramify_api_key,
            base_url=paramify_base_url
        )

    def list_nessus_scans(self):
        """
        List all available Nessus scans.

        Returns:
            List of scan dictionaries
        """
        return self.nessus_client.list_scans()

    def list_paramify_assessments(self, params: Optional[dict] = None):
        """
        List all available Paramify assessments.

        Args:
            params: Optional filter parameters

        Returns:
            List of assessment dictionaries
        """
        return self.paramify_client.list_assessments(params)

    def import_scan_to_assessment(
        self,
        scan_id: int,
        assessment_id: str,
        effective_date: Optional[str] = None,
        artifact_metadata: Optional[dict] = None
    ) -> dict:
        """
        Import a Nessus scan into a Paramify assessment.

        This method:
        1. Retrieves scan details from Nessus
        2. Exports the scan in .nessus format
        3. Uploads it to the specified Paramify assessment

        Args:
            scan_id: Nessus scan ID
            assessment_id: Paramify assessment UUID
            effective_date: Optional effective date (YYYY-MM-DD format)
            artifact_metadata: Optional metadata for the artifact

        Returns:
            Response from Paramify upload

        Raises:
            Exception: If any step fails
        """
        logger.info(f"Starting import of Nessus scan {scan_id} to Paramify assessment {assessment_id}")

        # Get scan details for metadata
        scan_details = self.nessus_client.get_scan_details(scan_id)
        scan_name = scan_details.get('info', {}).get('name', f'scan_{scan_id}')
        logger.info(f"Scan name: {scan_name}")

        # Export and download the scan
        logger.info("Exporting scan from Nessus...")
        scan_content = self.nessus_client.get_scan_export(scan_id, format='nessus')
        logger.info(f"Successfully exported scan ({len(scan_content)} bytes)")

        # Generate filename
        filename = f"{scan_name}.nessus"
        # Sanitize filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).strip()

        # Create artifact metadata if not provided
        if artifact_metadata is None:
            artifact_metadata = {}

        # Upload to Paramify
        logger.info(f"Uploading to Paramify assessment {assessment_id}...")
        result = self.paramify_client.upload_intake(
            assessment_id=assessment_id,
            file_content=scan_content,
            filename=filename,
            artifact_metadata=artifact_metadata,
            effective_date=effective_date
        )

        logger.info("Import completed successfully")
        return result

    def get_scan_info(self, scan_id: int) -> dict:
        """
        Get detailed information about a Nessus scan.

        Args:
            scan_id: Nessus scan ID

        Returns:
            Scan details dictionary
        """
        return self.nessus_client.get_scan_details(scan_id)

    def get_assessment_info(self, assessment_id: str) -> dict:
        """
        Get detailed information about a Paramify assessment.

        Args:
            assessment_id: Paramify assessment UUID

        Returns:
            Assessment details dictionary
        """
        return self.paramify_client.get_assessment(assessment_id)
