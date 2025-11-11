"""Email search and filtering capabilities.

This module provides advanced search and filtering functionality
for Microsoft Graph API mailbox operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from outlook_graph_skill.utils.validators import SearchValidator


@dataclass
class SearchFilter:
    """Email search filter builder.

    This class helps construct OData filter queries for Microsoft Graph API
    to search and filter emails efficiently.

    Attributes:
        subject_contains: Filter by subject containing text.
        from_email: Filter by sender email address.
        to_email: Filter by recipient email address.
        has_attachments: Filter by attachment presence.
        is_read: Filter by read status.
        received_after: Filter by received date (after).
        received_before: Filter by received date (before).
        importance: Filter by importance level.
        body_contains: Filter by body content.
        custom_filters: List of custom OData filter strings.
    """

    subject_contains: Optional[str] = None
    from_email: Optional[str] = None
    to_email: Optional[str] = None
    has_attachments: Optional[bool] = None
    is_read: Optional[bool] = None
    received_after: Optional[datetime] = None
    received_before: Optional[datetime] = None
    importance: Optional[str] = None
    body_contains: Optional[str] = None
    custom_filters: List[str] = field(default_factory=list)

    def build_filter_query(self) -> Optional[str]:
        """Build OData filter query string from criteria.

        Returns:
            OData filter query string, or None if no filters set.
        """
        filters = []

        if self.subject_contains:
            escaped_subject = self._escape_odata_string(self.subject_contains)
            filters.append(f"contains(subject, '{escaped_subject}')")

        if self.from_email:
            escaped_email = self._escape_odata_string(self.from_email)
            filters.append(
                f"from/emailAddress/address eq '{escaped_email}'"
            )

        if self.to_email:
            escaped_email = self._escape_odata_string(self.to_email)
            filters.append(
                f"toRecipients/any(r: r/emailAddress/address eq '{escaped_email}')"
            )

        if self.has_attachments is not None:
            filters.append(
                f"hasAttachments eq {str(self.has_attachments).lower()}"
            )

        if self.is_read is not None:
            filters.append(f"isRead eq {str(self.is_read).lower()}")

        if self.received_after:
            iso_date = self.received_after.isoformat()
            filters.append(f"receivedDateTime ge {iso_date}")

        if self.received_before:
            iso_date = self.received_before.isoformat()
            filters.append(f"receivedDateTime le {iso_date}")

        if self.importance:
            filters.append(f"importance eq '{self.importance.lower()}'")

        if self.body_contains:
            escaped_body = self._escape_odata_string(self.body_contains)
            filters.append(f"contains(body/content, '{escaped_body}')")

        # Add custom filters
        filters.extend(self.custom_filters)

        if not filters:
            return None

        return " and ".join(filters)

    @staticmethod
    def _escape_odata_string(value: str) -> str:
        """Escape string for use in OData queries.

        Args:
            value: String to escape.

        Returns:
            Escaped string safe for OData queries.
        """
        # Replace single quotes with double single quotes (OData escaping)
        return value.replace("'", "''")


class EmailSearch:
    """Advanced email search functionality.

    This class provides search capabilities for emails using Microsoft Graph
    search syntax and filtering.
    """

    def __init__(self) -> None:
        """Initialize email search."""
        self._filter = SearchFilter()

    def with_subject(self, subject: str) -> "EmailSearch":
        """Filter emails with subject containing text.

        Args:
            subject: Text to search for in subject.

        Returns:
            Self for method chaining.
        """
        SearchValidator.validate_search_query(subject)
        self._filter.subject_contains = subject
        return self

    def from_sender(self, email: str) -> "EmailSearch":
        """Filter emails from specific sender.

        Args:
            email: Sender email address.

        Returns:
            Self for method chaining.
        """
        self._filter.from_email = email
        return self

    def to_recipient(self, email: str) -> "EmailSearch":
        """Filter emails to specific recipient.

        Args:
            email: Recipient email address.

        Returns:
            Self for method chaining.
        """
        self._filter.to_email = email
        return self

    def with_attachments(self, has_attachments: bool = True) -> "EmailSearch":
        """Filter emails by attachment presence.

        Args:
            has_attachments: True to find emails with attachments.

        Returns:
            Self for method chaining.
        """
        self._filter.has_attachments = has_attachments
        return self

    def is_read(self, read: bool = True) -> "EmailSearch":
        """Filter emails by read status.

        Args:
            read: True to find read emails, False for unread.

        Returns:
            Self for method chaining.
        """
        self._filter.is_read = read
        return self

    def received_after(self, date: datetime) -> "EmailSearch":
        """Filter emails received after date.

        Args:
            date: Datetime threshold.

        Returns:
            Self for method chaining.
        """
        self._filter.received_after = date
        return self

    def received_before(self, date: datetime) -> "EmailSearch":
        """Filter emails received before date.

        Args:
            date: Datetime threshold.

        Returns:
            Self for method chaining.
        """
        self._filter.received_before = date
        return self

    def with_importance(self, importance: str) -> "EmailSearch":
        """Filter emails by importance level.

        Args:
            importance: Importance level ('low', 'normal', 'high').

        Returns:
            Self for method chaining.
        """
        self._filter.importance = importance
        return self

    def with_body_containing(self, text: str) -> "EmailSearch":
        """Filter emails with body containing text.

        Args:
            text: Text to search for in body.

        Returns:
            Self for method chaining.
        """
        SearchValidator.validate_search_query(text)
        self._filter.body_contains = text
        return self

    def add_custom_filter(self, odata_filter: str) -> "EmailSearch":
        """Add custom OData filter expression.

        Args:
            odata_filter: OData filter string.

        Returns:
            Self for method chaining.
        """
        self._filter.custom_filters.append(odata_filter)
        return self

    def build(self) -> Optional[str]:
        """Build the final filter query string.

        Returns:
            OData filter query string, or None if no filters.
        """
        return self._filter.build_filter_query()

    def reset(self) -> "EmailSearch":
        """Reset all search filters.

        Returns:
            Self for method chaining.
        """
        self._filter = SearchFilter()
        return self
