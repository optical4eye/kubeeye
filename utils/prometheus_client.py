#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus query tool for obtaining metric data from Prometheus
"""

import requests
from typing import Dict, Optional
from datetime import datetime
import time
import base64

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
        self.url = config['url'].rstrip('/')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.token = config.get('token', '')
        self.enabled = config.get('enabled', False)

    def _get_headers(self) -> Dict:
        """Get request headers"""
        headers = {'Accept': 'application/json'}

        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        elif self.username and self.password:
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers['Authorization'] = f"Basic {auth}"

        return headers

    def query(self, query_expr: str, time_param: Optional[str] = None) -> Dict:
        """
        Execute Prometheus query

        Args:
            query_expr: Prometheus query expression
            time_param: optional time parameter

        Returns:
            query results dictionary
        """
        if not self.enabled or not self.url:
            return {'status': 'error', 'error': 'Prometheus is not configured or not enabled'}

        params = {'query': query_expr}
        if time_param:
            params['time'] = time_param

        # Use request with retries
        return self._request_with_retry(f"{self.url}/api/v1/query", params)

    def query_range(self, query_expr: str, start_time: datetime,
                   end_time: datetime, step: str = "15s") -> Dict:
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
            return {'status': 'error', 'error': 'Prometheus is not configured or not enabled'}

        params = {
            'query': query_expr,
            'start': start_time.timestamp(),
            'end': end_time.timestamp(),
            'step': step
        }

        # Use request with retries
        return self._request_with_retry(f"{self.url}/api/v1/query_range", params)

    def alerts(self) -> Dict:
        """Get current triggered alerts"""
        if not self.enabled or not self.url:
            return {'status': 'error', 'error': 'Prometheus is not configured or not enabled'}

        # Use request with retries
        return self._request_with_retry(f"{self.url}/api/v1/alerts")

    def _request_with_retry(self, url: str, params: Dict = None, max_retries: int = 3) -> Dict:
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
        verify_ssl = url.lower().startswith('https://')

        # If this is an HTTP request, disable warnings about insecure requests
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        while retries < max_retries:
            try:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=30,
                    verify=verify_ssl  # Determine whether to verify SSL based on protocol
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 503 or response.status_code >= 500:
                    # Service unavailable, try to retry
                    retries += 1
                    if retries < max_retries:
                        time.sleep(1)  # Wait 1 second before retry
                        continue
                    else:
                        return {
                            'status': 'error',
                            'error': f"After several retries connection still failed: HTTP {response.status_code}",
                            'detail': response.text
                        }
                else:
                    return {
                        'status': 'error',
                        'error': f"Request failed: HTTP {response.status_code}",
                        'detail': response.text
                    }
            except requests.exceptions.Timeout:
                # Retry on timeout
                retries += 1
                if retries < max_retries:
                    time.sleep(1)
                    continue
                else:
                    return {'status': 'error', 'error': "Request timeout, several retries failed"}
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                retries += 1
                if retries < max_retries:
                    time.sleep(1)
                    continue
                else:
                    return {'status': 'error', 'error': f"Request exception: {last_error}"}

    def test_connection(self) -> Dict:
        """Test connection to Prometheus"""
        if not self.enabled or not self.url:
            return {'status': 'error', 'error': 'Prometheus is not configured or not enabled'}

        # Determine whether to verify SSL based on URL protocol
        verify_ssl = self.url.lower().startswith('https://')

        # If this is an HTTP request, disable warnings about insecure requests
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            response = requests.get(
                f"{self.url}/api/v1/status/config",
                headers=self._get_headers(),
                timeout=10,
                verify=verify_ssl  # Determine whether to verify SSL based on protocol
            )

            if response.status_code == 200:
                return {'status': 'success', 'message': 'Connection to Prometheus successful'}
            else:
                return {
                    'status': 'error',
                    'error': f"Connection failed: HTTP {response.status_code}",
                    'detail': response.text
                }
        except requests.exceptions.RequestException as e:
            return {'status': 'error', 'error': f"Request exception: {str(e)}"}
