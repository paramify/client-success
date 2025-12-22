"""
Configuration management for the Nessus-Paramify integration.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings for the integration."""

    # Paramify settings
    PARAMIFY_API_KEY: str = os.getenv('PARAMIFY_API_KEY', '')
    PARAMIFY_BASE_URL: str = os.getenv('PARAMIFY_BASE_URL', 'https://demo.paramify.com/api/v0')

    # Nessus settings
    NESSUS_URL: str = os.getenv('NESSUS_URL', 'https://localhost:8834')
    NESSUS_ACCESS_KEY: str = os.getenv('NESSUS_ACCESS_KEY', '')
    NESSUS_SECRET_KEY: str = os.getenv('NESSUS_SECRET_KEY', '')

    # Logging settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """
        Validate that all required configuration is present.

        Only PARAMIFY_API_KEY is required. Other credentials are optional
        and only needed for specific features (Nessus import, private GitHub repos).

        Returns:
            Tuple of (is_valid, list of missing keys)
        """
        missing = []

        if not cls.PARAMIFY_API_KEY:
            missing.append('PARAMIFY_API_KEY')

        return len(missing) == 0, missing

    @classmethod
    def validate_nessus(cls) -> tuple[bool, list[str]]:
        """
        Validate that Nessus credentials are present.

        Returns:
            Tuple of (is_valid, list of missing keys)
        """
        missing = []

        if not cls.NESSUS_ACCESS_KEY:
            missing.append('NESSUS_ACCESS_KEY')
        if not cls.NESSUS_SECRET_KEY:
            missing.append('NESSUS_SECRET_KEY')

        return len(missing) == 0, missing

    @classmethod
    def get_log_level(cls) -> int:
        """
        Get the logging level as an integer.

        Returns:
            Logging level constant
        """
        import logging
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return level_map.get(cls.LOG_LEVEL.upper(), logging.INFO)
