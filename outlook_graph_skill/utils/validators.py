"""Input validation utilities for Outlook Graph API Skill.

This module provides validation functions to ensure data integrity
and security throughout the skill.
"""

import re
from typing import Any, List, Optional
from outlook_graph_skill.utils.exceptions import ValidationException


class EmailValidator:
    """Validator for email-related inputs."""

    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )
    MAX_EMAIL_LENGTH = 320  # RFC 5321

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email address format.

        Args:
            email: Email address to validate.

        Returns:
            The validated email address.

        Raises:
            ValidationException: If email format is invalid.
        """
        if not isinstance(email, str):
            raise ValidationException(
                "Email must be a string",
                error_code="INVALID_TYPE",
            )

        email = email.strip()

        if not email:
            raise ValidationException(
                "Email address cannot be empty",
                error_code="EMPTY_EMAIL",
            )

        if len(email) > cls.MAX_EMAIL_LENGTH:
            raise ValidationException(
                f"Email address exceeds maximum length of {cls.MAX_EMAIL_LENGTH}",
                error_code="EMAIL_TOO_LONG",
            )

        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationException(
                f"Invalid email format: {email}",
                error_code="INVALID_EMAIL_FORMAT",
            )

        return email

    @classmethod
    def validate_email_list(cls, emails: List[str]) -> List[str]:
        """Validate a list of email addresses.

        Args:
            emails: List of email addresses to validate.

        Returns:
            List of validated email addresses.

        Raises:
            ValidationException: If any email format is invalid.
        """
        if not isinstance(emails, list):
            raise ValidationException(
                "Email list must be a list",
                error_code="INVALID_TYPE",
            )

        return [cls.validate_email(email) for email in emails]


class SubjectValidator:
    """Validator for email subject lines."""

    MAX_SUBJECT_LENGTH = 255

    @classmethod
    def validate_subject(cls, subject: str) -> str:
        """Validate email subject.

        Args:
            subject: Email subject to validate.

        Returns:
            The validated subject.

        Raises:
            ValidationException: If subject is invalid.
        """
        if not isinstance(subject, str):
            raise ValidationException(
                "Subject must be a string",
                error_code="INVALID_TYPE",
            )

        if len(subject) > cls.MAX_SUBJECT_LENGTH:
            raise ValidationException(
                f"Subject exceeds maximum length of {cls.MAX_SUBJECT_LENGTH}",
                error_code="SUBJECT_TOO_LONG",
            )

        return subject


class ContentValidator:
    """Validator for email content."""

    MAX_BODY_LENGTH = 1_000_000  # 1MB as characters
    ALLOWED_CONTENT_TYPES = {"text", "html"}

    @classmethod
    def validate_body(
        cls,
        body: str,
        content_type: str = "text",
    ) -> tuple[str, str]:
        """Validate email body content.

        Args:
            body: Email body content to validate.
            content_type: Content type ('text' or 'html').

        Returns:
            Tuple of (validated body, content_type).

        Raises:
            ValidationException: If body or content_type is invalid.
        """
        if not isinstance(body, str):
            raise ValidationException(
                "Body must be a string",
                error_code="INVALID_TYPE",
            )

        if len(body) > cls.MAX_BODY_LENGTH:
            raise ValidationException(
                f"Body exceeds maximum length of {cls.MAX_BODY_LENGTH}",
                error_code="BODY_TOO_LONG",
            )

        content_type = content_type.lower()
        if content_type not in cls.ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                f"Content type must be one of {cls.ALLOWED_CONTENT_TYPES}",
                error_code="INVALID_CONTENT_TYPE",
            )

        return body, content_type


class SearchValidator:
    """Validator for search queries."""

    MAX_QUERY_LENGTH = 500

    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate search query.

        Args:
            query: Search query to validate.

        Returns:
            The validated query.

        Raises:
            ValidationException: If query is invalid.
        """
        if not isinstance(query, str):
            raise ValidationException(
                "Search query must be a string",
                error_code="INVALID_TYPE",
            )

        query = query.strip()

        if not query:
            raise ValidationException(
                "Search query cannot be empty",
                error_code="EMPTY_QUERY",
            )

        if len(query) > cls.MAX_QUERY_LENGTH:
            raise ValidationException(
                f"Query exceeds maximum length of {cls.MAX_QUERY_LENGTH}",
                error_code="QUERY_TOO_LONG",
            )

        return query


class PaginationValidator:
    """Validator for pagination parameters."""

    MAX_PAGE_SIZE = 1000
    MIN_PAGE_SIZE = 1

    @classmethod
    def validate_page_size(cls, page_size: int) -> int:
        """Validate page size for pagination.

        Args:
            page_size: Number of items per page.

        Returns:
            The validated page size.

        Raises:
            ValidationException: If page size is invalid.
        """
        if not isinstance(page_size, int):
            raise ValidationException(
                "Page size must be an integer",
                error_code="INVALID_TYPE",
            )

        if page_size < cls.MIN_PAGE_SIZE:
            raise ValidationException(
                f"Page size must be at least {cls.MIN_PAGE_SIZE}",
                error_code="PAGE_SIZE_TOO_SMALL",
            )

        if page_size > cls.MAX_PAGE_SIZE:
            raise ValidationException(
                f"Page size cannot exceed {cls.MAX_PAGE_SIZE}",
                error_code="PAGE_SIZE_TOO_LARGE",
            )

        return page_size
