# api/base_client.py
"""
Base API client for DGT Traffic.
"""
import aiohttp
import logging
from typing import Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)


class DGTBaseClient:
    """Base client for DGT API."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize base client."""
        self._session = session
        self._logger = _LOGGER

    async def _make_request(self, url: str, **kwargs) -> Optional[str]:
        """Make HTTP request."""
        try:
            async with self._session.get(url, **kwargs) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    self._logger.error("HTTP %s from %s", response.status, url)
                    return None
        except Exception as err:
            self._logger.error("Error requesting %s: %s", url, err)
            return None
