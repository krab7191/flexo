# src/llm/watsonx_config.py

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class WatsonXConfig:
    """Configuration management for WatsonX credentials and settings.

    This class handles loading and validation of required WatsonX credentials
    from environment variables.

    Attributes:
        CREDS (dict): Dictionary containing API key and URL for WatsonX.
        PROJECT_ID (str): WatsonX project identifier.

    Example:
        ```python
        # Validate credentials before use
        WatsonXConfig.validate_credentials()

        # Access credentials
        credentials = WatsonXConfig.CREDS
        project_id = WatsonXConfig.PROJECT_ID
        ```
    """
    CREDS = {'apikey': os.getenv("WXAI_API_KEY"), 'url': os.getenv("WXAI_URL")}
    PROJECT_ID = os.getenv("WXAI_PROJECT_ID")

    @classmethod
    def validate_credentials(cls):
        """Validate the presence of required WatsonX credentials.

        Checks for the presence of all required credentials and logs appropriate
        messages for missing values.

        Raises:
            ValueError: If any required credential is missing.
        """
        missing = [key for key, value in {
            'WXAI_API_KEY': cls.CREDS['apikey'],
            'WXAI_URL': cls.CREDS['url'],
            'WXAI_PROJECT_ID': cls.PROJECT_ID
        }.items() if not value]

        if missing:
            logger.error(f"Missing WatsonX credentials: {', '.join(missing)}")
            raise ValueError(f"Missing WatsonX credentials: {', '.join(missing)}")

        logger.info("All WatsonX credentials loaded successfully.")
