"""Custom exceptions for Outlook Graph API Skill.

This module defines custom exception classes for better error handling
and debugging throughout the skill.
"""

from typing import Optional


class OutlookGraphSkillException(Exception):
    """Base exception for all Outlook Graph Skill errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            error_code: Optional error code for categorization.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the exception."""
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.details:
            base_msg += f" | Details: {self.details}"
        return base_msg


class AuthenticationException(OutlookGraphSkillException):
    """Exception raised for authentication-related errors."""

    pass


class ConfigurationException(OutlookGraphSkillException):
    """Exception raised for configuration-related errors."""

    pass


class TokenException(OutlookGraphSkillException):
    """Exception raised for token acquisition or refresh errors."""

    pass


class APIException(OutlookGraphSkillException):
    """Exception raised for Microsoft Graph API errors."""

    pass


class ValidationException(OutlookGraphSkillException):
    """Exception raised for input validation errors."""

    pass


class EmailOperationException(OutlookGraphSkillException):
    """Exception raised for email operation errors."""

    pass


class RateLimitException(APIException):
    """Exception raised when API rate limits are exceeded."""

    pass


class PermissionException(APIException):
    """Exception raised for insufficient permission errors."""

    pass
