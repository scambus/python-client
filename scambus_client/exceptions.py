"""
Exceptions for the Scambus client library.
"""


class ScambusAPIError(Exception):
    """Base exception for all Scambus API errors."""

    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class ScambusAuthenticationError(ScambusAPIError):
    """Raised when authentication fails (401 or invalid credentials)."""

    pass


class ScambusValidationError(ScambusAPIError):
    """Raised when request validation fails (400)."""

    pass


class ScambusNotFoundError(ScambusAPIError):
    """Raised when a resource is not found (404)."""

    pass


class ScambusServerError(ScambusAPIError):
    """Raised when the server returns a 5xx error."""

    pass
