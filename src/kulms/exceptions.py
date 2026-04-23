from __future__ import annotations


class KULMSError(Exception):
    """Base exception for this package."""


class AuthExpiredError(KULMSError):
    """Raised when a cached Sakai/KULMS session is no longer usable."""


class APIError(KULMSError):
    """Raised when a KULMS Direct API response cannot be used."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(APIError):
    """Raised for HTTP 404 responses."""

