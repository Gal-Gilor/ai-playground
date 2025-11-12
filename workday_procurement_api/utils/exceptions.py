"""Custom exceptions for Workday Procurement API.

This module defines custom exception classes for better error handling
and debugging throughout the application.
"""

from typing import Optional


class WorkdayAPIException(Exception):
    """Base exception for Workday API errors.

    Attributes:
        message: Error message.
        error_code: Error code for categorization.
        details: Additional error details.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Initialize exception.

        Args:
            message: Error message.
            error_code: Error code for categorization.
            details: Additional error details.
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation of exception.

        Returns:
            Formatted error message.
        """
        error_str = f"{self.message}"
        if self.error_code:
            error_str = f"[{self.error_code}] {error_str}"
        if self.details:
            error_str = f"{error_str} - Details: {self.details}"
        return error_str


class ConfigurationException(WorkdayAPIException):
    """Exception raised for configuration errors."""

    pass


class AuthenticationException(WorkdayAPIException):
    """Exception raised for authentication errors."""

    pass


class SOAPClientException(WorkdayAPIException):
    """Exception raised for SOAP client errors."""

    pass


class ValidationException(WorkdayAPIException):
    """Exception raised for data validation errors."""

    pass


class PurchaseOrderNotFoundException(WorkdayAPIException):
    """Exception raised when a purchase order is not found."""

    pass


class WorkdayServiceException(WorkdayAPIException):
    """Exception raised for Workday service-level errors.

    Attributes:
        fault_code: SOAP fault code.
        fault_string: SOAP fault string.
    """

    def __init__(
        self,
        message: str,
        fault_code: Optional[str] = None,
        fault_string: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Initialize Workday service exception.

        Args:
            message: Error message.
            fault_code: SOAP fault code.
            fault_string: SOAP fault string.
            error_code: Error code for categorization.
            details: Additional error details.
        """
        super().__init__(message, error_code, details)
        self.fault_code = fault_code
        self.fault_string = fault_string

    def __str__(self) -> str:
        """Return string representation of exception.

        Returns:
            Formatted error message.
        """
        error_str = super().__str__()
        if self.fault_code or self.fault_string:
            fault_info = []
            if self.fault_code:
                fault_info.append(f"Code: {self.fault_code}")
            if self.fault_string:
                fault_info.append(f"String: {self.fault_string}")
            error_str = f"{error_str} - SOAP Fault ({', '.join(fault_info)})"
        return error_str
