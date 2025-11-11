"""Email message models and data structures.

This module defines data classes for representing email messages,
recipients, attachments, and related structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MessageImportance(str, Enum):
    """Email importance levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass
class EmailRecipient:
    """Email recipient representation.

    Attributes:
        email: Email address.
        name: Display name (optional).
    """

    email: str
    name: Optional[str] = None

    def to_graph_format(self) -> dict:
        """Convert to Microsoft Graph API format.

        Returns:
            Dictionary in Graph API recipient format.
        """
        recipient = {"emailAddress": {"address": self.email}}
        if self.name:
            recipient["emailAddress"]["name"] = self.name
        return recipient

    @classmethod
    def from_graph_format(cls, data: dict) -> "EmailRecipient":
        """Create instance from Graph API response.

        Args:
            data: Graph API recipient data.

        Returns:
            EmailRecipient instance.
        """
        email_address = data.get("emailAddress", {})
        return cls(
            email=email_address.get("address", ""),
            name=email_address.get("name"),
        )


@dataclass
class Attachment:
    """Email attachment representation.

    Attributes:
        name: Attachment filename.
        content_type: MIME type of the attachment.
        size: Size in bytes.
        content_bytes: Base64 encoded content (for downloads).
        is_inline: Whether attachment is inline.
        attachment_id: Graph API attachment ID.
    """

    name: str
    content_type: str
    size: int
    content_bytes: Optional[str] = None
    is_inline: bool = False
    attachment_id: Optional[str] = None

    @classmethod
    def from_graph_format(cls, data: dict) -> "Attachment":
        """Create instance from Graph API response.

        Args:
            data: Graph API attachment data.

        Returns:
            Attachment instance.
        """
        return cls(
            name=data.get("name", ""),
            content_type=data.get("contentType", ""),
            size=data.get("size", 0),
            content_bytes=data.get("contentBytes"),
            is_inline=data.get("isInline", False),
            attachment_id=data.get("id"),
        )


@dataclass
class EmailMessage:
    """Email message representation.

    Attributes:
        subject: Email subject.
        body: Email body content.
        body_type: Body content type ('text' or 'html').
        to_recipients: List of To recipients.
        cc_recipients: List of CC recipients.
        bcc_recipients: List of BCC recipients.
        from_recipient: Sender information.
        importance: Message importance level.
        is_read: Whether message has been read.
        has_attachments: Whether message has attachments.
        attachments: List of attachments.
        received_datetime: When message was received.
        sent_datetime: When message was sent.
        message_id: Graph API message ID.
        conversation_id: Conversation thread ID.
        internet_message_id: Internet message ID.
    """

    subject: str
    body: str
    body_type: str = "text"
    to_recipients: List[EmailRecipient] = field(default_factory=list)
    cc_recipients: List[EmailRecipient] = field(default_factory=list)
    bcc_recipients: List[EmailRecipient] = field(default_factory=list)
    from_recipient: Optional[EmailRecipient] = None
    importance: MessageImportance = MessageImportance.NORMAL
    is_read: bool = False
    has_attachments: bool = False
    attachments: List[Attachment] = field(default_factory=list)
    received_datetime: Optional[datetime] = None
    sent_datetime: Optional[datetime] = None
    message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    internet_message_id: Optional[str] = None

    def to_graph_format(self) -> dict:
        """Convert to Microsoft Graph API format for sending.

        Returns:
            Dictionary in Graph API message format.
        """
        message = {
            "subject": self.subject,
            "body": {"contentType": self.body_type, "content": self.body},
            "importance": self.importance.value,
        }

        if self.to_recipients:
            message["toRecipients"] = [
                r.to_graph_format() for r in self.to_recipients
            ]

        if self.cc_recipients:
            message["ccRecipients"] = [
                r.to_graph_format() for r in self.cc_recipients
            ]

        if self.bcc_recipients:
            message["bccRecipients"] = [
                r.to_graph_format() for r in self.bcc_recipients
            ]

        return message

    @classmethod
    def from_graph_format(cls, data: dict) -> "EmailMessage":
        """Create instance from Graph API response.

        Args:
            data: Graph API message data.

        Returns:
            EmailMessage instance.
        """
        body_data = data.get("body", {})
        from_data = data.get("from")

        # Parse recipients
        to_recipients = [
            EmailRecipient.from_graph_format(r)
            for r in data.get("toRecipients", [])
        ]
        cc_recipients = [
            EmailRecipient.from_graph_format(r)
            for r in data.get("ccRecipients", [])
        ]
        bcc_recipients = [
            EmailRecipient.from_graph_format(r)
            for r in data.get("bccRecipients", [])
        ]

        # Parse attachments if present
        attachments = [
            Attachment.from_graph_format(a)
            for a in data.get("attachments", [])
        ]

        # Parse datetime fields
        received_dt = None
        if data.get("receivedDateTime"):
            try:
                received_dt = datetime.fromisoformat(
                    data["receivedDateTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        sent_dt = None
        if data.get("sentDateTime"):
            try:
                sent_dt = datetime.fromisoformat(
                    data["sentDateTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return cls(
            subject=data.get("subject", ""),
            body=body_data.get("content", ""),
            body_type=body_data.get("contentType", "text").lower(),
            to_recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            from_recipient=(
                EmailRecipient.from_graph_format(from_data)
                if from_data
                else None
            ),
            importance=MessageImportance(
                data.get("importance", "normal").lower()
            ),
            is_read=data.get("isRead", False),
            has_attachments=data.get("hasAttachments", False),
            attachments=attachments,
            received_datetime=received_dt,
            sent_datetime=sent_dt,
            message_id=data.get("id"),
            conversation_id=data.get("conversationId"),
            internet_message_id=data.get("internetMessageId"),
        )

    def __repr__(self) -> str:
        """Return string representation of message."""
        from_str = (
            f"{self.from_recipient.name} <{self.from_recipient.email}>"
            if self.from_recipient and self.from_recipient.name
            else (
                self.from_recipient.email if self.from_recipient else "Unknown"
            )
        )

        return (
            f"EmailMessage(from={from_str}, subject='{self.subject}', "
            f"received={self.received_datetime})"
        )
