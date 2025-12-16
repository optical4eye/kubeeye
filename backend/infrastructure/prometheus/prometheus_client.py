#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus query tool for obtaining metric data from Prometheus
"""

import aiohttp
from typing import Dict, Optional
from datetime import datetime
import base64
import asyncio


class PrometheusClient:
    """Prometheus client class"""

    def __init__(self, config: Dict):
        """
        Initialize Prometheus client

        Args:
            config: configuration dictionary containing the following fields:
                - url: Prometheus URL
                - username: optional username
                - password: optional password
                - token: optional access token
                - enabled: whether enabled
        """
        self.url = config["url"].rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.token = config.get("token", "")
        self.enabled = config.get("enabled", False)

    def _get_headers(self) -> Dict:
        """Get request headers"""
        headers = {"Accept": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.username and self.password:
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {auth}"

        return headers

    async def query(self, query_expr: str, time_param: Optional[str] = None) -> Dict:
        """
        Execute Prometheus query

        Args:
            query_expr: Prometheus query expression
            time_param: optional time parameter

        Returns:
            query results dictionary
        """
        if not self.enabled or not self.url:
            return {
                "status": "error",
                "error": "Prometheus is not configured or not enabled",
            }

        params = {"query": query_expr}
        if time_param:
            params["time"] = time_param

        # Use request with retries
        return await self._request_with_retry(f"{self.url}/api/v1/query", params)

    async def query_range(
        self,
        query_expr: str,
        start_time: datetime,
        end_time: datetime,
        step: str = "15s",
    ) -> Dict:
        """
        Execute range query

        Args:
            query_expr: Prometheus query expression
            start_time: start time
            end_time: end time
            step: step

        Returns:
            query results dictionary
        """
        if not self.enabled or not self.url:
            return {
                "status": "error",
                "error": "Prometheus is not configured or not enabled",
            }

        params = {
            "query": query_expr,
            "start": start_time.timestamp(),
            "end": end_time.timestamp(),
            "step": step,
        }

        # Use request with retries
        return await self._request_with_retry(f"{self.url}/api/v1/query_range", params)

    async def alerts(self) -> Dict:
        """Get current triggered alerts"""
        if not self.enabled or not self.url:
            return {
                "status": "error",
                "error": "Prometheus is not configured or not enabled",
            }

        # Use request with retries
        return await self._request_with_retry(f"{self.url}/api/v1/alerts")

    async def _request_with_retry(self, url: str, params: Dict = None, max_retries: int = 3) -> Dict:
        """
        Execute Prometheus API request with retries

        Args:
            url: API URL
            params: request parameters
            max_retries: maximum number of retries

        Returns:
            response result
        """
        retries = 0
        last_error = None

        # Determine whether to verify SSL based on URL protocol
        verify_ssl = url.lower().startswith("https://")

        # If this is an HTTP request, disable warnings about insecure requests
        if not verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            while retries < max_retries:
                try:
                    async with session.get(
                        url,
                        headers=self._get_headers(),
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 503 or response.status >= 500:
                            # Service unavailable, try to retry
                            retries += 1
                            if retries < max_retries:
                                await asyncio.sleep(1)  # Wait 1 second before retry
                                continue
                            else:
                                text = await response.text()
                                return {
                                    "status": "error",
                                    "error": f"After several retries connection still failed: HTTP {response.status}",
                                    "detail": text,
                                }
                        else:
                            text = await response.text()
                            return {
                                "status": "error",
                                "error": f"Request failed: HTTP {response.status}",
                                "detail": text,
                            }
                except asyncio.TimeoutError:
                    # Retry on timeout
                    retries += 1
                    if retries < max_retries:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return {
                            "status": "error",
                            "error": "Request timeout, several retries failed",
                        }
                except aiohttp.ClientError as e:
                    last_error = str(e)
                    retries += 1
                    if retries < max_retries:
                        await asyncio.sleep(1)
                        continue
                    else:
                        return {
                            "status": "error",
                            "error": f"Request exception: {last_error}",
                        }

    async def test_connection(self) -> Dict:
        """Test connection to Prometheus"""
        if not self.enabled or not self.url:
            return {
                "status": "error",
                "error": "Prometheus is not configured or not enabled",
            }

        # Determine whether to verify SSL based on URL protocol
        verify_ssl = self.url.lower().startswith("https://")

        connector = aiohttp.TCPConnector(verify_ssl=verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.get(
                    f"{self.url}/api/v1/status/config",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        return {
                            "status": "success",
                            "message": "Connection to Prometheus successful",
                        }
                    else:
                        text = await response.text()
                        return {
                            "status": "error",
                            "error": f"Connection failed: HTTP {response.status}",
                            "detail": text,
                        }
            except aiohttp.ClientError as e:
                return {"status": "error", "error": f"Request exception: {str(e)}"}
