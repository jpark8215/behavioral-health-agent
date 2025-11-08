"""
Custom exceptions for behavioral health application
Provides structured error handling with healthcare-specific context
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class BehavioralHealthException(Exception):
    """Base exception for behavioral health application"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BehavioralHealthException):
    """Input validation errors"""
    pass


class ProcessingError(BehavioralHealthException):
    """Audio/text processing errors"""
    pass


class DatabaseError(BehavioralHealthException):
    """Database operation errors"""
    pass


class ExternalServiceError(BehavioralHealthException):
    """External service (Ollama, etc.) errors"""
    pass


class SecurityError(BehavioralHealthException):
    """Security-related errors"""
    pass


class ConfigurationError(BehavioralHealthException):
    """Configuration and setup errors"""
    pass


# HTTP Exception Factories
def create_http_exception(
    status_code: int,
    message: str,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create standardized HTTP exception"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_code or "UnknownError",
            "message": message,
            "details": details or {}
        }
    )


def validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create validation error response"""
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=message,
        error_code="ValidationError",
        details=details
    )


def processing_error(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create processing error response"""
    return create_http_exception(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=message,
        error_code="ProcessingError",
        details=details
    )


def service_unavailable_error(service: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create service unavailable error"""
    return create_http_exception(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        message=f"{service} service is currently unavailable",
        error_code="ServiceUnavailable",
        details=details
    )


def not_found_error(resource: str, identifier: str) -> HTTPException:
    """Create not found error"""
    return create_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        message=f"{resource} with ID '{identifier}' not found",
        error_code="NotFound",
        details={"resource": resource, "id": identifier}
    )


def internal_server_error(message: str = "An internal error occurred") -> HTTPException:
    """Create internal server error (sanitized for production)"""
    return create_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code="InternalServerError"
    )