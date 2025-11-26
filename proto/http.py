import aiohttp
import logging
from typing import Dict, Any, Optional, Tuple
import json


class HTTPClient:
    """HTTP client for REST API communication"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.logger = logging.getLogger("HTTPClient")
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Tuple[bool, Dict]:
        """Make HTTP request"""
        if not self.session:
            await self.initialize()

        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.request(
                method, url, json=data, params=params
            ) as response:
                result = await response.json()
                if response.status in (200, 201):
                    return True, result
                else:
                    self.logger.error(
                        f"HTTP error {response.status}: {result}"
                    )
                    return False, result
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return False, {"error": str(e)}

    async def get(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Tuple[bool, Dict]:
        """Make GET request"""
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, data: Dict) -> Tuple[bool, Dict]:
        """Make POST request"""
        return await self.request("POST", endpoint, data=data)

    async def cleanup(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
