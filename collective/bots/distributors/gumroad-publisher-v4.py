#!/usr/bin/env python3
"""
Gumroad Publisher Bot - Production-ready API client for Gumroad v2
Uses REST API only (no browser automation)
"""

import os
import sys
import time
import random
import logging
import argparse
from typing import Optional, Dict, List, Any, Union, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta

# Constants
GUMROAD_API_BASE = "https://api.gumroad.com/v2"
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5
DEFAULT_TIMEOUT = 30
HUMAN_DELAY_MIN = 0.8
HUMAN_DELAY_MAX = 3.5
RATE_LIMIT_DELAY = 60  # seconds to wait when rate limited (increased from 5)
MAX_SESSION_AGE = timedelta(hours=1)  # Maximum session age before renewal
REQUEST_WINDOW = 60  # seconds for rate limit tracking
MAX_REQUESTS_PER_WINDOW = 60  # Gumroad's typical rate limit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("gumroad-publisher")
logger.setLevel(logging.DEBUG)  # Enable debug logging

class GumroadAPIError(Exception):
    """Custom exception for Gumroad API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict] = None, request_id: Optional[str] = None):
        self.status_code = status_code
        self.response_data = response_data
        self.request_id = request_id
        super().__init__(message)

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            base += f" (HTTP {self.status_code})"
        if self.request_id:
            base += f" [Request ID: {self.request_id}]"
        return base

class GumroadPublisher:
    def __init__(self):
        self.access_token = self._get_access_token()
        self.session = self._create_session()
        self._validate_token()
        self.last_request_time = 0
        self.session_created = datetime.now()
        self.request_timestamps: List[datetime] = []
        self._initialize_rate_limit_tracking()

    def _get_access_token(self) -> str:
        """Read Gumroad access token from environment"""
        token = os.getenv("GUMROAD_ACCESS_TOKEN")
        if not token:
            raise GumroadAPIError("GUMROAD_ACCESS_TOKEN environment variable not set")
        if not isinstance(token, str) or len(token.strip()) < 10:
            raise GumroadAPIError("Invalid GUMROAD_ACCESS_TOKEN format")
        return token.strip()

    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retry logic"""
        session = requests.Session()

        retry_strategy = Retry(
            total=DEFAULT_RETRIES,
            backoff_factor=DEFAULT_BACKOFF,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "POST", "DELETE", "OPTIONS", "TRACE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _initialize_rate_limit_tracking(self) -> None:
        """Initialize rate limit tracking structures"""
        self.request_timestamps = []

    def _check_session_age(self) -> bool:
        """Check if session needs to be renewed"""
        return datetime.now() - self.session_created > MAX_SESSION_AGE

    def _renew_session(self) -> None:
        """Renew the session if it's too old"""
        if self._check_session_age():
            logger.info("Session age exceeded maximum, renewing session")
            self.session = self._create_session()
            self.session_created = datetime.now()

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limits by tracking request timestamps"""
        now = datetime.now()
        # Remove timestamps older than our window
        self.request_timestamps = [
            ts for ts in self.request_timestamps
            if now - ts < timedelta(seconds=REQUEST_WINDOW)
        ]

        if len(self.request_timestamps) >= MAX_REQUESTS_PER_WINDOW:
            oldest = self.request_timestamps[0]
            wait_time = (oldest + timedelta(seconds=REQUEST_WINDOW) - now).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                # After waiting, we need to re-check
                self._enforce_rate_limit()
                return

        self.request_timestamps.append(now)

    def _human_delay(self) -> None:
        """Add random human-like delay between requests"""
        delay = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
        time.sleep(delay)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make an API request with proper error handling and rate limiting"""
        self._renew_session()
        self._enforce_rate_limit()

        url = f"{GUMROAD_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                timeout=timeout or DEFAULT_TIMEOUT
            )

            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', RATE_LIMIT_DELAY))
                logger.warning(f"Rate limited. Waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, data, json, timeout)

            response.raise_for_status()

            try:
                return response.json()
            except ValueError:
                raise GumroadAPIError("Invalid JSON response from server")

        except requests.exceptions.Timeout:
            raise GumroadAPIError(f"Request timed out after {timeout or DEFAULT_TIMEOUT} seconds")
        except requests.exceptions.RequestException as e:
            raise GumroadAPIError(f"Network error: {str(e)}")
        finally:
            self._human_delay()

    def _validate_token(self) -> None:
        """Validate the access token by making a test request"""
        try:
            self._make_request("GET", "/user")
        except GumroadAPIError as e:
            raise GumroadAPIError(f"Token validation failed: {str(e)}")

    def get_user(self) -> Dict[str, Any]:
        """Get information about the authenticated user"""
        return self._make_request("GET", "/user")

    def get_products(self) -> Dict[str, Any]:
        """Get a list of products for the authenticated user"""
        return self._make_request("GET", "/products")

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get details for a specific product"""
        return self._make_request("GET", f"/products/{product_id}")

    def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        return self._make_request("POST", "/products", json=product_data)

    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing product"""
        return self._make_request("PUT", f"/products/{product_id}", json=product_data)

    def get_sales(self) -> Dict[str, Any]:
        """Get a list of sales for the authenticated user"""
        return self._make_request("GET", "/sales")

    def get_sale(self, sale_id: str) -> Dict[str, Any]:
        """Get details for a specific sale"""
        return self._make_request("GET", f"/sales/{sale_id}")

    def refund_sale(self, sale_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Refund a sale (partially or fully)"""
        data = {"sale_id": sale_id}
        if amount is not None:
            data["amount"] = amount
        return self._make_request("POST", "/sales/refund", json=data)