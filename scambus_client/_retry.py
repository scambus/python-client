"""Retry constants for Scambus client HTTP requests.

Inspired by AWS SDK standard retry mode.
See: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html
See: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
"""

RETRY_BASE_DELAY = 1.0  # Base delay in seconds (AWS default)
RETRY_MAX_BACKOFF = 20.0  # Cap per-retry delay (AWS standard mode default)
RETRY_THROTTLE_BASE = 2.0  # Higher base delay for 429 throttling responses

# HTTP status codes that are safe to retry (transient / server-side errors).
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
