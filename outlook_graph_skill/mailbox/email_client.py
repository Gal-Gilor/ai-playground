"""Email client for Microsoft Graph API mailbox operations.

This module provides comprehensive email operations including reading,
sending, searching, and managing emails through Microsoft Graph API.
"""

import logging
import time
from typing import List, Optional
from urllib.parse import quote

import requests

from outlook_graph_skill.auth.authenticator import GraphAuthenticator
from outlook_graph_skill.config.settings import SkillConfig
from outlook_graph_skill.mailbox.message import (
    Attachment,
    EmailMessage,
    EmailRecipient,
)
from outlook_graph_skill.mailbox.search import EmailSearch
from outlook_graph_skill.utils.exceptions import (
    APIException,
    EmailOperationException,
    PermissionException,
    RateLimitException,
)
from outlook_graph_skill.utils.validators import (
    ContentValidator,
    EmailValidator,
    PaginationValidator,
    SubjectValidator,
)

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for Microsoft Graph API email operations.

    This class provides a high-level interface for interacting with
    Outlook mailboxes through Microsoft Graph API.

    Attributes:
        config: Skill configuration instance.
        authenticator: Graph API authenticator.
        user_id: User ID or 'me' for current user.
    """

    def __init__(
        self,
        config: SkillConfig,
        user_id: str = "me",
    ) -> None:
        """Initialize email client.

        Args:
            config: Configuration instance.
            user_id: User ID or 'me' for authenticated user.
        """
        self.config = config
        self.authenticator = GraphAuthenticator(config)
        self.user_id = user_id
        self._base_url = f"{config.api.endpoint}/users/{user_id}"

    def _get_headers(self) -> dict:
        """Get request headers with authorization.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = self.authenticator.get_authorization_header()
        headers["Content-Type"] = "application/json"
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            **kwargs: Additional arguments for requests.

        Returns:
            Response object.

        Raises:
            APIException: If request fails after retries.
            RateLimitException: If rate limit is exceeded.
            PermissionException: If insufficient permissions.
        """
        url = f"{self._base_url}/{endpoint}"
        headers = self._get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        max_retries = self.config.api.max_retries
        timeout = self.config.api.timeout
        backoff_factor = self.config.api.retry_backoff_factor

        for attempt in range(max_retries + 1):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", 60)
                    )
                    if attempt < max_retries:
                        logger.warning(
                            f"Rate limited. Retrying after {retry_after}s"
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        raise RateLimitException(
                            "API rate limit exceeded",
                            error_code="RATE_LIMIT_EXCEEDED",
                            details={"retry_after": retry_after},
                        )

                # Handle authentication errors (might need token refresh)
                if response.status_code == 401:
                    if attempt < max_retries:
                        logger.info("Token expired, refreshing...")
                        self.authenticator.refresh_token()
                        headers = self._get_headers()
                        continue
                    else:
                        raise APIException(
                            "Authentication failed",
                            error_code="AUTH_FAILED",
                        )

                # Handle permission errors
                if response.status_code == 403:
                    raise PermissionException(
                        "Insufficient permissions for this operation",
                        error_code="INSUFFICIENT_PERMISSIONS",
                        details=response.json() if response.content else {},
                    )

                # Raise for other HTTP errors
                response.raise_for_status()

                return response

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    sleep_time = backoff_factor**attempt
                    logger.warning(
                        f"Request timeout. Retrying in {sleep_time}s..."
                    )
                    time.sleep(sleep_time)
                else:
                    raise APIException(
                        "Request timeout",
                        error_code="TIMEOUT",
                    )

            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    sleep_time = backoff_factor**attempt
                    logger.warning(f"Request failed. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    raise APIException(
                        f"Request failed: {e}",
                        error_code="REQUEST_FAILED",
                    )

        raise APIException(
            "Max retries exceeded",
            error_code="MAX_RETRIES_EXCEEDED",
        )

    def send_email(
        self,
        subject: str,
        body: str,
        to_recipients: List[str],
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        body_type: str = "text",
        importance: str = "normal",
        save_to_sent_items: bool = True,
    ) -> bool:
        """Send an email message.

        Args:
            subject: Email subject.
            body: Email body content.
            to_recipients: List of recipient email addresses.
            cc_recipients: List of CC recipient email addresses.
            bcc_recipients: List of BCC recipient email addresses.
            body_type: Body content type ('text' or 'html').
            importance: Message importance ('low', 'normal', 'high').
            save_to_sent_items: Whether to save to Sent Items folder.

        Returns:
            True if email sent successfully.

        Raises:
            ValidationException: If input validation fails.
            EmailOperationException: If send operation fails.
        """
        # Validate inputs
        subject = SubjectValidator.validate_subject(subject)
        body, body_type = ContentValidator.validate_body(body, body_type)
        to_recipients = EmailValidator.validate_email_list(to_recipients)

        if cc_recipients:
            cc_recipients = EmailValidator.validate_email_list(cc_recipients)
        if bcc_recipients:
            bcc_recipients = EmailValidator.validate_email_list(bcc_recipients)

        # Build message
        message = EmailMessage(
            subject=subject,
            body=body,
            body_type=body_type,
            to_recipients=[EmailRecipient(email=e) for e in to_recipients],
            cc_recipients=(
                [EmailRecipient(email=e) for e in cc_recipients]
                if cc_recipients
                else []
            ),
            bcc_recipients=(
                [EmailRecipient(email=e) for e in bcc_recipients]
                if bcc_recipients
                else []
            ),
        )

        # Prepare request payload
        payload = {
            "message": message.to_graph_format(),
            "saveToSentItems": save_to_sent_items,
        }

        try:
            response = self._make_request(
                "POST",
                "sendMail",
                json=payload,
            )

            logger.info(f"Email sent successfully: '{subject}'")
            return True

        except Exception as e:
            raise EmailOperationException(
                f"Failed to send email: {e}",
                error_code="SEND_FAILED",
            )

    def get_messages(
        self,
        folder: str = "inbox",
        top: int = 10,
        skip: int = 0,
        search_filter: Optional[str] = None,
        order_by: str = "receivedDateTime DESC",
    ) -> List[EmailMessage]:
        """Retrieve email messages from a folder.

        Args:
            folder: Folder name or ID (default: 'inbox').
            top: Number of messages to retrieve (max 1000).
            skip: Number of messages to skip.
            search_filter: OData filter query string.
            order_by: OData orderBy clause.

        Returns:
            List of EmailMessage objects.

        Raises:
            EmailOperationException: If retrieval fails.
        """
        top = PaginationValidator.validate_page_size(top)

        # Build query parameters
        params = {
            "$top": top,
            "$skip": skip,
            "$orderby": order_by,
        }

        if search_filter:
            params["$filter"] = search_filter

        try:
            response = self._make_request(
                "GET",
                f"mailFolders/{folder}/messages",
                params=params,
            )

            data = response.json()
            messages = [
                EmailMessage.from_graph_format(m)
                for m in data.get("value", [])
            ]

            logger.info(f"Retrieved {len(messages)} messages from {folder}")
            return messages

        except Exception as e:
            raise EmailOperationException(
                f"Failed to retrieve messages: {e}",
                error_code="RETRIEVAL_FAILED",
            )

    def search_emails(
        self,
        search: EmailSearch,
        folder: str = "inbox",
        top: int = 10,
    ) -> List[EmailMessage]:
        """Search for emails using EmailSearch criteria.

        Args:
            search: EmailSearch instance with search criteria.
            folder: Folder to search in.
            top: Maximum number of results.

        Returns:
            List of matching EmailMessage objects.
        """
        filter_query = search.build()
        return self.get_messages(
            folder=folder,
            top=top,
            search_filter=filter_query,
        )

    def get_message_by_id(self, message_id: str) -> EmailMessage:
        """Retrieve a specific message by ID.

        Args:
            message_id: Message ID.

        Returns:
            EmailMessage object.

        Raises:
            EmailOperationException: If retrieval fails.
        """
        try:
            response = self._make_request(
                "GET",
                f"messages/{message_id}",
            )

            message = EmailMessage.from_graph_format(response.json())
            logger.info(f"Retrieved message: {message_id}")
            return message

        except Exception as e:
            raise EmailOperationException(
                f"Failed to retrieve message: {e}",
                error_code="MESSAGE_NOT_FOUND",
            )

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read.

        Args:
            message_id: Message ID.

        Returns:
            True if successful.

        Raises:
            EmailOperationException: If operation fails.
        """
        try:
            self._make_request(
                "PATCH",
                f"messages/{message_id}",
                json={"isRead": True},
            )

            logger.info(f"Marked message as read: {message_id}")
            return True

        except Exception as e:
            raise EmailOperationException(
                f"Failed to mark message as read: {e}",
                error_code="UPDATE_FAILED",
            )

    def mark_as_unread(self, message_id: str) -> bool:
        """Mark a message as unread.

        Args:
            message_id: Message ID.

        Returns:
            True if successful.

        Raises:
            EmailOperationException: If operation fails.
        """
        try:
            self._make_request(
                "PATCH",
                f"messages/{message_id}",
                json={"isRead": False},
            )

            logger.info(f"Marked message as unread: {message_id}")
            return True

        except Exception as e:
            raise EmailOperationException(
                f"Failed to mark message as unread: {e}",
                error_code="UPDATE_FAILED",
            )

    def delete_message(self, message_id: str) -> bool:
        """Delete a message.

        Args:
            message_id: Message ID.

        Returns:
            True if successful.

        Raises:
            EmailOperationException: If deletion fails.
        """
        try:
            self._make_request(
                "DELETE",
                f"messages/{message_id}",
            )

            logger.info(f"Deleted message: {message_id}")
            return True

        except Exception as e:
            raise EmailOperationException(
                f"Failed to delete message: {e}",
                error_code="DELETE_FAILED",
            )

    def get_attachments(self, message_id: str) -> List[Attachment]:
        """Get attachments for a message.

        Args:
            message_id: Message ID.

        Returns:
            List of Attachment objects.

        Raises:
            EmailOperationException: If retrieval fails.
        """
        try:
            response = self._make_request(
                "GET",
                f"messages/{message_id}/attachments",
            )

            data = response.json()
            attachments = [
                Attachment.from_graph_format(a)
                for a in data.get("value", [])
            ]

            logger.info(
                f"Retrieved {len(attachments)} attachments for message {message_id}"
            )
            return attachments

        except Exception as e:
            raise EmailOperationException(
                f"Failed to retrieve attachments: {e}",
                error_code="ATTACHMENT_RETRIEVAL_FAILED",
            )

    def list_folders(self) -> List[dict]:
        """List all mail folders.

        Returns:
            List of folder information dictionaries.

        Raises:
            EmailOperationException: If retrieval fails.
        """
        try:
            response = self._make_request("GET", "mailFolders")

            data = response.json()
            folders = data.get("value", [])

            logger.info(f"Retrieved {len(folders)} mail folders")
            return folders

        except Exception as e:
            raise EmailOperationException(
                f"Failed to list folders: {e}",
                error_code="FOLDER_LIST_FAILED",
            )

    def __enter__(self) -> "EmailClient":
        """Context manager entry.

        Returns:
            Self for use in with statements.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        # Clean up resources if needed
        pass
