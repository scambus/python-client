"""
Base client with shared logic for sync and async Scambus API clients.
"""

import logging
import random
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Union

from .config import get_api_url, get_api_token, get_api_key_id, get_api_key_secret
from .exceptions import (
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusNotFoundError,
    ScambusServerError,
    ScambusValidationError,
)
from ._retry import (
    RETRY_BASE_DELAY,
    RETRY_MAX_BACKOFF,
    RETRY_THROTTLE_BASE,
    RETRYABLE_STATUS_CODES,
)

logger = logging.getLogger(__name__)


def _to_rfc3339(dt: datetime) -> str:
    """Convert a datetime to RFC3339 string. Assumes UTC if no timezone is set."""
    if dt.tzinfo is None:
        warnings.warn(
            f"Naive datetime {dt!r} has no timezone info; assuming UTC. "
            "Pass a timezone-aware datetime to silence this warning "
            "(e.g., datetime(..., tzinfo=timezone.utc)).",
            stacklevel=3,
        )
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


class BaseScambusClient:
    """Base class for sync and async Scambus API clients.

    Contains all shared initialization logic, configuration loading,
    authentication setup, and static helper methods.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 10,
        retry_max_time: int = 300,
    ):
        # Load configuration with priority: explicit param > env var > config file > default
        api_url = get_api_url(api_url)
        api_key_id = get_api_key_id(api_key_id)
        api_key_secret = get_api_key_secret(api_key_secret)

        # Ensure /api suffix
        if not api_url.endswith("/api"):
            api_url = f"{api_url}/api"

        # Only try to load api_token if api_key auth not available
        if not (api_key_id and api_key_secret):
            api_token = get_api_token(api_token)

        self.api_url = api_url.rstrip("/") if api_url else "https://scambus.net/api"
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_max_time = retry_max_time

        # Build auth headers (subclasses apply to their HTTP client)
        if api_key_id and api_key_secret:
            self._auth_headers = {
                "X-API-Key": f"{api_key_id}:{api_key_secret}",
                "User-Agent": "scambus-python-client/1.0.0",
            }
        elif api_token:
            self._auth_headers = {
                "Authorization": f"Bearer {api_token}",
                "User-Agent": "scambus-python-client/1.0.0",
            }
        else:
            raise ValueError(
                "No authentication provided. Either:\n"
                "1. Set SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET environment variables, or\n"
                "2. Provide api_key_id/api_key_secret parameters, or\n"
                "3. Run 'scambus auth login' to authenticate via CLI, or\n"
                "4. Set SCAMBUS_API_TOKEN environment variable"
            )

    @staticmethod
    def _compute_backoff(attempt: int, base: float, max_backoff: float) -> float:
        """Compute retry delay using truncated exponential backoff with full jitter.

        Implements the "Full Jitter" algorithm recommended by AWS:
            sleep = random(0, min(max_backoff, base * 2^attempt))
        """
        ceiling = min(max_backoff, base * (2 ** attempt))
        return random.uniform(0, ceiling)

    @staticmethod
    def _parse_retry_after(response) -> Optional[float]:
        """Extract delay from the Retry-After header, if present.

        Works with both httpx.Response and requests.Response objects.
        """
        header = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if header is None:
            return None
        try:
            return float(header)
        except ValueError:
            pass
        # HTTP-date format (RFC 7231)
        try:
            retry_dt = parsedate_to_datetime(header)
            delta = (retry_dt - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, delta)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _handle_error_response(response):
        """Handle error responses from the API.

        Works with both httpx.Response and requests.Response objects.
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error", response.text)
        except (ValueError, Exception):
            error_data = None
            error_message = response.text or f"HTTP {response.status_code}"

        if response.status_code == 401:
            raise ScambusAuthenticationError(
                error_message, response.status_code, error_data,
            )
        elif response.status_code == 400:
            raise ScambusValidationError(
                error_message, response.status_code, error_data,
            )
        elif response.status_code == 404:
            raise ScambusNotFoundError(
                error_message, response.status_code, error_data,
            )
        elif response.status_code >= 500:
            raise ScambusServerError(
                error_message, response.status_code, error_data,
            )
        else:
            raise ScambusAPIError(
                error_message, response.status_code, error_data,
            )
