"""Mailbox operations module for Outlook Graph API Skill."""

from outlook_graph_skill.mailbox.email_client import EmailClient
from outlook_graph_skill.mailbox.message import (
    Attachment,
    EmailMessage,
    EmailRecipient,
    MessageImportance,
)
from outlook_graph_skill.mailbox.search import EmailSearch, SearchFilter

__all__ = [
    "EmailClient",
    "EmailMessage",
    "EmailRecipient",
    "Attachment",
    "MessageImportance",
    "EmailSearch",
    "SearchFilter",
]
