"""
Custom exception classes for the application.
Provides structured error handling with appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str = "An application error occurred",
        status_code: int = 500,
        detail: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__(message=message, status_code=404)


class BadRequestException(AppException):
    """Invalid request data."""

    def __init__(self, message: str = "Bad request"):
        super().__init__(message=message, status_code=400)


class FileProcessingException(AppException):
    """Error during file processing."""

    def __init__(self, message: str = "Failed to process file"):
        super().__init__(message=message, status_code=400)


class AnalysisException(AppException):
    """Error during contract analysis."""

    def __init__(self, message: str = "Failed to analyze contract"):
        super().__init__(message=message, status_code=500)


class DatabaseException(AppException):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message=message, status_code=500)
