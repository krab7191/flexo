# src/llm/adapters/watsonx/ibm_token_manager.py

import os
import time
import asyncio
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IBMTokenManager:
    """Manages IBM Cloud OAuth2 token lifecycle for WatsonX API access.

    This class handles authentication token management for IBM Cloud services,
    including automatic token refresh and thread-safe token access. It implements
    a singleton pattern to maintain one token instance across the application.

    Attributes:
        api_key (str): IBM Cloud API key for authentication.
        token_url (str): IBM IAM authentication endpoint URL.
        refresh_buffer (int): Time buffer in seconds before token expiry to trigger refresh.
        access_token (Optional[str]): Current valid access token.
        expiry_time (float): Unix timestamp when the current token expires.
        lock (asyncio.Lock): Async lock for thread-safe token refresh operations.
    """

    def __init__(self, api_key: str, refresh_buffer: int = 60):
        """Initialize the IBM Token Manager.

        Args:
            api_key (str): IBM WatsonX API key for authentication.
            refresh_buffer (int, optional): Buffer time in seconds before token expiry
                to trigger a refresh. Defaults to 60 seconds.

        Raises:
            ValueError: If api_key is empty or None.
            EnvironmentError: If IBM_AUTH_URL environment variable is not set.
        """
        if not api_key:
            raise ValueError("API key cannot be empty or None")

        self.api_key = api_key
        self.token_url = os.getenv("IBM_AUTH_URL")
        if not self.token_url:
            raise EnvironmentError("IBM_AUTH_URL environment variable not set")

        self.refresh_buffer = refresh_buffer
        self.access_token: Optional[str] = None
        self.expiry_time: float = 0
        self.lock = asyncio.Lock()

        logger.debug("Initialized IBMTokenManager with refresh buffer of %d seconds", refresh_buffer)

    async def _is_token_expired(self) -> bool:
        """Check if the current token is expired or approaching expiry.

        Returns:
            bool: True if token is expired or will expire soon, False otherwise.
        """
        current_time = time.time()
        is_expired = self.access_token is None or current_time > (self.expiry_time - self.refresh_buffer)

        if is_expired:
            logger.debug("Token is expired or approaching expiry")
        return is_expired

    async def _refresh_token(self) -> None:
        """Fetch a new OAuth token from IBM IAM.

        Raises:
            aiohttp.ClientError: If the token refresh request fails.
            ValueError: If the response doesn't contain expected token information.
            Exception: For any other unexpected errors during token refresh.
        """
        async with self.lock:
            if not await self._is_token_expired():
                logger.debug("Token refresh skipped - current token still valid")
                return

            logger.debug("Starting token refresh process")
            try:
                headers = {"Content-Type": "application/x-www-form-urlencoded"}
                payload = {
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                }

                async with aiohttp.ClientSession() as session:
                    logger.debug("Making token refresh request to IBM IAM")
                    async with session.post(self.token_url, headers=headers, data=payload) as response:
                        response.raise_for_status()
                        token_info = await response.json()

                        if "access_token" not in token_info or "expires_in" not in token_info:
                            raise ValueError("Invalid token response from IBM IAM")

                        self.access_token = token_info["access_token"]
                        expires_in = int(token_info["expires_in"])
                        self.expiry_time = time.time() + expires_in

                        logger.info("Successfully refreshed IBM token. Expires in %d seconds", expires_in)
                        logger.debug("Token expiry time set to %s", time.ctime(self.expiry_time))

            except aiohttp.ClientError as e:
                logger.error("HTTP error during token refresh: %s", str(e))
                self.access_token = None
                raise
            except Exception as e:
                logger.error("Unexpected error during token refresh: %s", str(e))
                self.access_token = None
                raise

    async def get_token(self) -> Optional[str]:
        """Retrieve a valid access token, refreshing if necessary.

        Returns:
            Optional[str]: Valid access token if successful, None if token
                refresh fails.

        Raises:
            Exception: If token refresh fails when attempted.
        """
        logger.debug("Token requested")
        if await self._is_token_expired():
            logger.debug("Token refresh needed before returning")
            await self._refresh_token()
        return self.access_token
