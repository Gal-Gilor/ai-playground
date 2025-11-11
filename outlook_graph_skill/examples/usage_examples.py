"""Usage examples for Outlook Graph API Skill.

This module demonstrates various use cases and patterns for interacting
with Microsoft Graph API through the Outlook Graph Skill.
"""

import os
from datetime import datetime, timedelta

from outlook_graph_skill import EmailClient, GraphAuthenticator, SkillConfig
from outlook_graph_skill.mailbox import EmailRecipient, MessageImportance
from outlook_graph_skill.mailbox.search import EmailSearch


def example_basic_setup():
    """Example: Basic setup using environment variables."""
    # Load configuration from environment variables
    # Set these in your environment or .env file:
    # - AZURE_CLIENT_ID
    # - AZURE_TENANT_ID
    # - AZURE_CLIENT_SECRET

    # NEW PYDANTIC WAY (recommended): Automatically loads from .env
    config = SkillConfig()

    # OLD WAY (still works for backwards compatibility):
    # config = SkillConfig.from_env()

    # Create email client
    client = EmailClient(config)

    print("✓ Email client initialized successfully")
    return client


def example_pydantic_configuration():
    """Example: Leveraging Pydantic Settings features."""
    # Method 1: Automatic .env loading (simplest)
    config = SkillConfig()

    # Method 2: Override specific values programmatically
    config = SkillConfig(
        azure_client_id="custom-client-id",
        azure_tenant_id="custom-tenant-id",
        azure_client_secret="custom-secret",
    )

    # Method 3: Use nested configuration with double underscore
    config = SkillConfig(
        api__timeout=60,  # Override API timeout
        api__max_retries=5,  # Override max retries
        cache__enabled=True,  # Enable cache
    )

    # Method 4: Load from different .env file
    config = SkillConfig(_env_file='.env.production')

    # Access configuration (Pydantic provides full type safety)
    print(f"Client ID: {config.azure_client_id}")
    print(f"API Endpoint: {config.api.endpoint}")
    print(f"Cache Path: {config.cache.cache_path}")

    # Export to dictionary (secrets redacted by default)
    config_dict = config.to_dict()
    print(f"Configuration: {config_dict}")

    print("✓ Pydantic configuration examples completed")


def example_send_simple_email(client: EmailClient):
    """Example: Send a simple text email."""
    client.send_email(
        subject="Test Email from Graph API Skill",
        body="This is a test email sent using the Outlook Graph API Skill.",
        to_recipients=["recipient@example.com"],
        body_type="text",
    )

    print("✓ Simple email sent successfully")


def example_send_html_email(client: EmailClient):
    """Example: Send an HTML email with multiple recipients."""
    html_body = """
    <html>
        <body>
            <h1>Hello from Graph API</h1>
            <p>This is a <strong>formatted</strong> email with HTML content.</p>
            <ul>
                <li>Feature 1</li>
                <li>Feature 2</li>
                <li>Feature 3</li>
            </ul>
        </body>
    </html>
    """

    client.send_email(
        subject="Important Update",
        body=html_body,
        to_recipients=["user1@example.com", "user2@example.com"],
        cc_recipients=["manager@example.com"],
        body_type="html",
        importance="high",
    )

    print("✓ HTML email sent successfully")


def example_read_inbox(client: EmailClient):
    """Example: Read recent emails from inbox."""
    # Get the 10 most recent emails
    messages = client.get_messages(folder="inbox", top=10)

    print(f"\n📬 Found {len(messages)} messages in inbox:\n")

    for i, message in enumerate(messages, 1):
        sender = (
            message.from_recipient.email if message.from_recipient else "Unknown"
        )
        print(f"{i}. From: {sender}")
        print(f"   Subject: {message.subject}")
        print(f"   Received: {message.received_datetime}")
        print(f"   Read: {'Yes' if message.is_read else 'No'}")
        print(f"   Attachments: {'Yes' if message.has_attachments else 'No'}\n")


def example_search_unread_emails(client: EmailClient):
    """Example: Search for unread emails."""
    # Build search criteria
    search = EmailSearch().is_read(False)

    # Execute search
    unread_messages = client.search_emails(search, top=20)

    print(f"\n📧 Found {len(unread_messages)} unread messages")

    for message in unread_messages:
        print(f"  - {message.subject}")


def example_search_emails_with_attachments(client: EmailClient):
    """Example: Search for emails with attachments from last week."""
    # Calculate date one week ago
    one_week_ago = datetime.now() - timedelta(days=7)

    # Build search criteria
    search = (
        EmailSearch()
        .with_attachments(True)
        .received_after(one_week_ago)
    )

    # Execute search
    messages = client.search_emails(search, top=50)

    print(f"\n📎 Found {len(messages)} messages with attachments from last week")

    for message in messages:
        print(f"  - {message.subject} ({len(message.attachments)} attachments)")


def example_search_by_sender(client: EmailClient):
    """Example: Search for emails from specific sender."""
    sender_email = "boss@example.com"

    search = EmailSearch().from_sender(sender_email)

    messages = client.search_emails(search, top=25)

    print(f"\n👤 Found {len(messages)} messages from {sender_email}")


def example_complex_search(client: EmailClient):
    """Example: Complex search with multiple criteria."""
    # Search for high-importance unread emails with attachments
    # from the last 3 days
    three_days_ago = datetime.now() - timedelta(days=3)

    search = (
        EmailSearch()
        .is_read(False)
        .with_attachments(True)
        .with_importance("high")
        .received_after(three_days_ago)
        .with_subject("urgent")
    )

    messages = client.search_emails(search, top=100)

    print(f"\n🔍 Complex search found {len(messages)} matching messages")


def example_manage_emails(client: EmailClient):
    """Example: Mark emails as read/unread and delete."""
    # Get recent unread messages
    search = EmailSearch().is_read(False)
    messages = client.search_emails(search, top=5)

    if messages:
        first_message = messages[0]
        message_id = first_message.message_id

        print(f"\n📝 Managing message: {first_message.subject}")

        # Mark as read
        client.mark_as_read(message_id)
        print("  ✓ Marked as read")

        # Mark as unread
        client.mark_as_unread(message_id)
        print("  ✓ Marked as unread")

        # Note: Be careful with delete!
        # client.delete_message(message_id)
        # print("  ✓ Deleted")


def example_get_message_details(client: EmailClient):
    """Example: Get detailed information about a specific message."""
    # Get first message from inbox
    messages = client.get_messages(folder="inbox", top=1)

    if messages:
        message = messages[0]

        print(f"\n📄 Message Details:")
        print(f"  ID: {message.message_id}")
        print(f"  Subject: {message.subject}")
        print(f"  From: {message.from_recipient.email if message.from_recipient else 'N/A'}")
        print(f"  To: {', '.join(r.email for r in message.to_recipients)}")
        print(f"  Received: {message.received_datetime}")
        print(f"  Read: {message.is_read}")
        print(f"  Importance: {message.importance.value}")

        # Get attachments if present
        if message.has_attachments:
            attachments = client.get_attachments(message.message_id)
            print(f"\n  📎 Attachments ({len(attachments)}):")
            for att in attachments:
                print(f"    - {att.name} ({att.size} bytes)")


def example_list_folders(client: EmailClient):
    """Example: List all mail folders."""
    folders = client.list_folders()

    print(f"\n📁 Mail Folders ({len(folders)}):")
    for folder in folders:
        print(f"  - {folder.get('displayName')} (ID: {folder.get('id')})")


def example_context_manager_usage():
    """Example: Using context managers for automatic cleanup."""
    config = SkillConfig.from_env()

    # Using context managers ensures proper cleanup
    with EmailClient(config) as client:
        messages = client.get_messages(top=5)
        print(f"\n✓ Retrieved {len(messages)} messages using context manager")


def example_custom_configuration():
    """Example: Custom configuration from JSON file."""
    # Load from JSON configuration file
    config = SkillConfig.from_json("config/config.json")

    # Or create programmatically
    from outlook_graph_skill.config import AuthConfig

    auth_config = AuthConfig(
        client_id="your-client-id",
        tenant_id="your-tenant-id",
        client_secret="your-client-secret",
    )

    config = SkillConfig(auth_config=auth_config)

    client = EmailClient(config)

    print("✓ Client initialized with custom configuration")


def example_error_handling():
    """Example: Proper error handling."""
    from outlook_graph_skill.utils.exceptions import (
        EmailOperationException,
        RateLimitException,
    )

    config = SkillConfig.from_env()
    client = EmailClient(config)

    try:
        client.send_email(
            subject="Test",
            body="Test message",
            to_recipients=["test@example.com"],
        )
        print("✓ Email sent successfully")

    except RateLimitException as e:
        print(f"⚠ Rate limit exceeded: {e}")
        print(f"  Retry after: {e.details.get('retry_after')} seconds")

    except EmailOperationException as e:
        print(f"✗ Email operation failed: {e}")
        print(f"  Error code: {e.error_code}")

    except Exception as e:
        print(f"✗ Unexpected error: {e}")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Outlook Graph API Skill - Usage Examples")
    print("=" * 60)

    try:
        # Initialize client
        client = example_basic_setup()

        # Uncomment the examples you want to run:

        # Sending emails
        # example_send_simple_email(client)
        # example_send_html_email(client)

        # Reading emails
        example_read_inbox(client)

        # Searching emails
        # example_search_unread_emails(client)
        # example_search_emails_with_attachments(client)
        # example_search_by_sender(client)
        # example_complex_search(client)

        # Managing emails
        # example_manage_emails(client)

        # Getting details
        # example_get_message_details(client)
        # example_list_folders(client)

        # Other patterns
        # example_context_manager_usage()
        # example_error_handling()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")


if __name__ == "__main__":
    main()
