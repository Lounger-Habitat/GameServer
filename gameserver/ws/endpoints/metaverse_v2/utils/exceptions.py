"""Custom exceptions for the star server."""

from typing import Optional


class StarServerError(Exception):
    """Base exception for star server errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ConnectionError(StarServerError):
    """Raised when connection-related errors occur."""

    pass


class MessageError(StarServerError):
    """Raised when message processing errors occur."""

    pass


class ValidationError(StarServerError):
    """Raised when message validation errors occur."""

    pass


class ClientNotFoundError(ConnectionError):
    """Raised when a client is not found."""

    pass


class EnvironmentNotFoundError(ConnectionError):
    """Raised when an environment is not found."""

    pass


class DuplicateConnectionError(ConnectionError):
    """Raised when attempting to create a duplicate connection."""

    pass
