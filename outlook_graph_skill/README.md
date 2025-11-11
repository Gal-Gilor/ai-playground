# Outlook Graph API Skill for Claude Code

Enterprise-grade Python skill for interacting with Microsoft Outlook through the Microsoft Graph API. This skill provides secure authentication, comprehensive email operations, and advanced search capabilities.

## Features

- **Enterprise OAuth2 Authentication** - Secure authentication using Microsoft Authentication Library (MSAL)
- **Pydantic-Powered Configuration** - Automatic .env loading, validation, and type safety with Pydantic Settings
- **Token Caching** - Automatic token caching and refresh for optimal performance
- **Email Operations** - Send, read, search, and manage emails
- **Advanced Search** - Flexible search with multiple criteria and filters
- **Attachment Support** - Handle email attachments
- **Error Handling** - Comprehensive error handling with retry logic
- **Type Safety** - Full type hints and validation throughout
- **Security Best Practices** - Input validation, sanitization, and secure credential management

## Prerequisites

### 1. Microsoft Entra ID App Registration

You need to register an application in Microsoft Entra ID (formerly Azure AD):

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Microsoft Entra ID** > **App registrations**
3. Click **New registration**
4. Provide a name (e.g., "Outlook Graph Skill")
5. Select **Accounts in this organizational directory only**
6. Click **Register**

### 2. Configure API Permissions

After registration, configure permissions:

1. Go to **API permissions** in your app
2. Click **Add a permission** > **Microsoft Graph** > **Application permissions**
3. Add the following permissions:
   - `Mail.Read` - Read mail in all mailboxes
   - `Mail.ReadWrite` - Read and write mail in all mailboxes
   - `Mail.Send` - Send mail as any user
   - `MailboxSettings.Read` - Read mailbox settings
4. Click **Grant admin consent** for your organization

### 3. Create Client Secret

1. Go to **Certificates & secrets** in your app
2. Click **New client secret**
3. Add a description and select expiration period
4. Click **Add**
5. **Copy the secret value immediately** (you won't be able to see it again)

### 4. Note Your IDs

From the **Overview** page, copy:
- **Application (client) ID** - Your Entra ID application identifier
- **Directory (tenant) ID** - Your Entra ID tenant identifier

## Installation

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Packages

- `msal>=1.28.0` - Microsoft Authentication Library
- `requests>=2.31.0` - HTTP library
- `pydantic>=2.0.0` - Data validation and settings management
- `pydantic-settings>=2.0.0` - Settings management with automatic .env loading

## Configuration

This skill uses **Pydantic Settings** for robust, validated configuration with automatic .env file loading.

### Option 1: Automatic .env Loading (Recommended)

Create a `.env` file in your project root:

```bash
AZURE_CLIENT_ID=your-application-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_SECRET=your-client-secret
GRAPH_API_SCOPES=https://graph.microsoft.com/.default
```

Then in your code:

```python
from outlook_graph_skill import SkillConfig, EmailClient

# Automatically loads from .env file - no from_env() needed!
config = SkillConfig()
client = EmailClient(config)
```

**Backwards Compatible:** The old `SkillConfig.from_env()` method still works:

```python
config = SkillConfig.from_env()  # Still works!
```

### Advanced Configuration

**Nested settings** using double underscore delimiter:

```bash
# .env file
API__TIMEOUT=60
API__MAX_RETRIES=5
CACHE__ENABLED=true
CACHE__CACHE_DIR=/tmp/cache
```

**Programmatic overrides:**

```python
config = SkillConfig(
    api__timeout=120,      # Override API timeout
    cache__enabled=False   # Disable cache
)
```

**Multiple environment files:**

```python
# Load from specific .env file
config = SkillConfig(_env_file='.env.production')
```

### Option 2: JSON Configuration

Create `config.json`:

```json
{
  "auth": {
    "client_id": "your-application-id",
    "tenant_id": "your-tenant-id",
    "client_secret": "your-client-secret",
    "scopes": ["https://graph.microsoft.com/.default"]
  },
  "api": {
    "base_url": "https://graph.microsoft.com",
    "api_version": "v1.0",
    "timeout": 30,
    "max_retries": 3
  }
}
```

Then in your code:

```python
from outlook_graph_skill import SkillConfig, EmailClient

config = SkillConfig.from_json("config.json")
client = EmailClient(config)
```

### Option 3: Programmatic Configuration

```python
from outlook_graph_skill import SkillConfig, EmailClient
from outlook_graph_skill.config import AuthConfig

auth_config = AuthConfig(
    client_id="your-application-id",
    tenant_id="your-tenant-id",
    client_secret="your-client-secret",
)

config = SkillConfig(auth_config=auth_config)
client = EmailClient(config)
```

## Usage Examples

### Basic Email Operations

#### Send a Simple Email

```python
from outlook_graph_skill import SkillConfig, EmailClient

config = SkillConfig.from_env()
client = EmailClient(config)

client.send_email(
    subject="Hello from Graph API",
    body="This is a test email.",
    to_recipients=["recipient@example.com"],
)
```

#### Send HTML Email with CC/BCC

```python
html_body = """
<html>
    <body>
        <h1>Important Update</h1>
        <p>This is an <strong>HTML</strong> email.</p>
    </body>
</html>
"""

client.send_email(
    subject="Important Update",
    body=html_body,
    to_recipients=["user1@example.com", "user2@example.com"],
    cc_recipients=["manager@example.com"],
    bcc_recipients=["archive@example.com"],
    body_type="html",
    importance="high",
)
```

#### Read Inbox Messages

```python
# Get 10 most recent emails
messages = client.get_messages(folder="inbox", top=10)

for message in messages:
    print(f"From: {message.from_recipient.email}")
    print(f"Subject: {message.subject}")
    print(f"Received: {message.received_datetime}")
    print(f"Read: {message.is_read}")
    print("-" * 50)
```

### Advanced Search

#### Search for Unread Emails

```python
from outlook_graph_skill.mailbox import EmailSearch

search = EmailSearch().is_read(False)
unread_messages = client.search_emails(search, top=20)

print(f"Found {len(unread_messages)} unread messages")
```

#### Search by Sender

```python
search = EmailSearch().from_sender("boss@example.com")
messages = client.search_emails(search, top=50)
```

#### Search with Multiple Criteria

```python
from datetime import datetime, timedelta

# Find unread emails with attachments from last 7 days
search = (
    EmailSearch()
    .is_read(False)
    .with_attachments(True)
    .received_after(datetime.now() - timedelta(days=7))
    .with_subject("report")
)

messages = client.search_emails(search, top=100)
```

#### Complex Search

```python
search = (
    EmailSearch()
    .from_sender("client@example.com")
    .with_importance("high")
    .with_attachments(True)
    .received_after(datetime.now() - timedelta(days=3))
    .with_subject("urgent")
)

messages = client.search_emails(search)
```

### Message Management

#### Mark Messages as Read/Unread

```python
# Mark as read
client.mark_as_read(message_id)

# Mark as unread
client.mark_as_unread(message_id)
```

#### Delete Message

```python
client.delete_message(message_id)
```

#### Get Message Details

```python
message = client.get_message_by_id(message_id)

print(f"Subject: {message.subject}")
print(f"From: {message.from_recipient.email}")
print(f"Body: {message.body}")
print(f"Attachments: {len(message.attachments)}")
```

### Working with Attachments

```python
# Get attachments for a message
attachments = client.get_attachments(message_id)

for attachment in attachments:
    print(f"Name: {attachment.name}")
    print(f"Size: {attachment.size} bytes")
    print(f"Type: {attachment.content_type}")
```

### Folder Management

```python
# List all mail folders
folders = client.list_folders()

for folder in folders:
    print(f"Folder: {folder['displayName']}")
    print(f"ID: {folder['id']}")
```

## Error Handling

The skill provides comprehensive error handling:

```python
from outlook_graph_skill.utils.exceptions import (
    EmailOperationException,
    RateLimitException,
    PermissionException,
    AuthenticationException,
)

try:
    client.send_email(
        subject="Test",
        body="Test message",
        to_recipients=["test@example.com"],
    )
except RateLimitException as e:
    print(f"Rate limit exceeded. Retry after: {e.details.get('retry_after')}s")
except PermissionException as e:
    print(f"Insufficient permissions: {e}")
except AuthenticationException as e:
    print(f"Authentication failed: {e}")
except EmailOperationException as e:
    print(f"Email operation failed: {e.error_code} - {e.message}")
```

## Context Manager Usage

Use context managers for automatic cleanup:

```python
with EmailClient(config) as client:
    messages = client.get_messages(top=10)
    # Token cache is automatically saved on exit
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables or secure vaults
2. **Use least privilege** - Only request necessary permissions
3. **Rotate secrets regularly** - Update client secrets periodically
4. **Secure token cache** - The skill automatically sets restrictive file permissions (0600)
5. **Validate inputs** - All inputs are automatically validated and sanitized
6. **Use HTTPS** - All API calls use HTTPS by default

## Architecture

```
outlook_graph_skill/
├── __init__.py              # Main package exports
├── auth/                    # Authentication module
│   ├── authenticator.py     # MSAL OAuth2 authenticator
│   └── token_cache.py       # Secure token caching
├── mailbox/                 # Mailbox operations module
│   ├── email_client.py      # Main email client
│   ├── message.py           # Message models
│   └── search.py            # Search and filtering
├── config/                  # Configuration module
│   ├── settings.py          # Configuration management
│   └── config.example.json  # Example configuration
├── utils/                   # Utilities module
│   ├── exceptions.py        # Custom exceptions
│   └── validators.py        # Input validation
├── examples/                # Usage examples
│   └── usage_examples.py
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Design Principles

- **SOLID Principles** - Single responsibility, open/closed, dependency inversion
- **Type Safety** - Full type hints throughout
- **Security First** - Input validation, secure credential management
- **Performance** - Token caching, connection pooling, retry logic
- **Pythonic** - Follows PEP 8 and Google Python Style Guide
- **Modular** - Reusable components with clear interfaces

## API Rate Limits

Microsoft Graph API has rate limits:
- **Automatic retry** - The skill automatically retries on 429 errors
- **Exponential backoff** - Uses exponential backoff for retries
- **Respect Retry-After** - Honors Retry-After headers

## Logging

Enable logging for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("outlook_graph_skill")
```

## Troubleshooting

### Authentication Errors

**Problem**: `AuthenticationException: Token acquisition failed`

**Solutions**:
1. Verify client ID, tenant ID, and client secret
2. Ensure app has required permissions
3. Check that admin consent has been granted
4. Verify the authority URL is correct

### Permission Errors

**Problem**: `PermissionException: Insufficient permissions`

**Solutions**:
1. Add required permissions in Azure AD
2. Grant admin consent
3. Wait a few minutes for permissions to propagate

### Rate Limit Errors

**Problem**: `RateLimitException: API rate limit exceeded`

**Solutions**:
1. The skill automatically retries - wait for completion
2. Reduce request frequency
3. Implement batching for bulk operations

## Contributing

This skill follows Google Python Style Guide and PEP 8:
- Use type hints
- Write docstrings (Google style)
- Validate all inputs
- Handle errors gracefully
- Add tests for new features

## License

MIT License

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the examples
3. Check Microsoft Graph API documentation
4. Review error messages and codes

## Resources

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/)
- [MSAL Python Documentation](https://learn.microsoft.com/en-us/entra/msal/python/)
- [Azure AD App Registration](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
- [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) - Test API calls

## Version History

### 1.0.0 (Current)
- Initial release
- OAuth2 authentication with MSAL
- Email send, read, search operations
- Advanced search filters
- Attachment support
- Comprehensive error handling
- Token caching
