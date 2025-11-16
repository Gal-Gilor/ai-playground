# Microsoft Graph API OAuth2 Authentication Guide

A comprehensive guide for developers to build tools that authenticate via OAuth2 with Microsoft Graph API to interact with SharePoint Lists and Email operations.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Azure AD App Registration](#azure-ad-app-registration)
4. [OAuth2 Authentication Setup](#oauth2-authentication-setup)
5. [SharePoint Lists Integration](#sharepoint-lists-integration)
6. [Email Operations Integration](#email-operations-integration)
7. [Complete Code Examples](#complete-code-examples)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Resources](#resources)

## Introduction

This guide demonstrates how to create applications that authenticate with Microsoft Graph API using OAuth2 to:

- **SharePoint Lists**: Get information stored in Lists within a SharePoint site
- **Email Operations**: Read, mark as read, send emails, and add CC recipients

Microsoft Graph API provides a unified endpoint (`https://graph.microsoft.com`) to access data across Microsoft 365 services including SharePoint, Outlook, Teams, and more.

### Authentication Flow

We'll use the **OAuth2 Client Credentials Flow** (also known as app-only authentication), which is ideal for:
- Backend services and daemons
- Automated processes without user interaction
- Applications that access resources with their own identity

## Prerequisites

### 1. Required Accounts and Access

- **Azure AD Administrator Access**: Required to register applications and grant admin consent
- **Microsoft 365 Subscription**: For SharePoint and Exchange Online access
- **SharePoint Site**: A SharePoint site with Lists to test against
- **Mailbox Access**: User mailbox for email operations testing

### 2. Development Environment

**Python 3.8+** with the following packages:

```bash
pip install msal>=1.28.0
pip install requests>=2.31.0
pip install python-dotenv>=1.0.0
```

**Alternative Languages**: This guide provides Python examples, but the concepts apply to any language. Microsoft provides SDKs for:
- .NET/C#
- JavaScript/TypeScript
- Java
- PHP
- PowerShell

## Azure AD App Registration

### Step 1: Register Your Application

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Azure Active Directory**
3. Select **App registrations** from the left navigation
4. Click **+ New registration**

### Step 2: Configure Basic Settings

Fill in the registration form:

| Field | Value |
|-------|-------|
| **Name** | `Graph API SharePoint & Email Tool` (or your preferred name) |
| **Supported account types** | `Accounts in this organizational directory only (Single tenant)` |
| **Redirect URI** | Leave blank (not needed for client credentials flow) |

Click **Register**.

### Step 3: Note Your Application IDs

After registration, you'll see the app overview page. **Save these values**:

```
Application (client) ID: 12345678-1234-1234-1234-123456789012
Directory (tenant) ID: 87654321-4321-4321-4321-210987654321
```

⚠️ **Important**: You'll need these for authentication.

### Step 4: Create a Client Secret

1. In your app's page, navigate to **Certificates & secrets**
2. Click **+ New client secret**
3. Configure the secret:
   - **Description**: `Graph API Tool Secret`
   - **Expires**: Select based on your security policy
     - **6 months** - Most secure, requires frequent rotation
     - **12 months** - Balanced approach (recommended)
     - **24 months** - Less maintenance overhead

4. Click **Add**
5. **IMMEDIATELY COPY THE SECRET VALUE** - you cannot view it again!

Example secret: `abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA`

⚠️ **Security Warning**:
- Never commit secrets to version control
- Store securely in environment variables or key vault
- Rotate secrets regularly

### Step 5: Configure API Permissions

#### Required Permissions

Navigate to **API permissions** in your app and add the following:

1. Click **+ Add a permission**
2. Select **Microsoft Graph**
3. Choose **Application permissions** (NOT Delegated permissions)

Add these permissions:

**For SharePoint Lists:**

| Permission | Description | Admin Consent Required |
|------------|-------------|------------------------|
| `Sites.Read.All` | Read items in all site collections | Yes |
| `Sites.ReadWrite.All` | Read and write items in all site collections (if you need to modify lists) | Yes |

**For Email Operations:**

| Permission | Description | Admin Consent Required |
|------------|-------------|------------------------|
| `Mail.Read` | Read mail in all mailboxes | Yes |
| `Mail.ReadWrite` | Read and write mail in all mailboxes | Yes |
| `Mail.Send` | Send mail as any user | Yes |
| `MailboxSettings.Read` | Read all mailbox settings | Yes |

**Optional but Recommended:**

| Permission | Description |
|------------|-------------|
| `User.Read.All` | Read all users' full profiles (for resolving email addresses) |

### Step 6: Grant Admin Consent

⚠️ **Critical Step**: Application permissions require administrator consent.

1. After adding all permissions, click **Grant admin consent for [Your Organization]**
2. Click **Yes** in the confirmation dialog
3. Wait for all permissions to show a green checkmark under the **Status** column

✅ Verify all permissions show "Granted for [Your Organization]"

### Step 7: Verify Configuration Checklist

Before proceeding, ensure you have:

- ✅ Application (client) ID
- ✅ Directory (tenant) ID
- ✅ Client secret (stored securely)
- ✅ All required permissions added
- ✅ Admin consent granted (green checkmarks)

## OAuth2 Authentication Setup

### Understanding the Client Credentials Flow

The client credentials flow works as follows:

```
Your Application
    │
    │ 1. Request access token with client credentials
    ├──────────────────────────────────────────────────►
    │                                          Azure AD Token Endpoint
    │ 2. Return access token
    ◄──────────────────────────────────────────────────┤
    │
    │ 3. Call Graph API with access token
    ├──────────────────────────────────────────────────►
    │                                          Microsoft Graph API
    │ 4. Return requested data
    ◄──────────────────────────────────────────────────┤
```

### Configuration File Setup

#### Option 1: Environment Variables (Recommended)

Create a `.env` file:

```bash
# Azure AD Application Settings
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789012
AZURE_TENANT_ID=87654321-4321-4321-4321-210987654321
AZURE_CLIENT_SECRET=abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA

# Microsoft Graph Settings
GRAPH_API_BASE_URL=https://graph.microsoft.com
GRAPH_API_VERSION=v1.0
GRAPH_API_SCOPE=https://graph.microsoft.com/.default
```

⚠️ **Important**: Add `.env` to your `.gitignore` file!

#### Option 2: JSON Configuration

Create `config.json`:

```json
{
  "azure": {
    "client_id": "12345678-1234-1234-1234-123456789012",
    "tenant_id": "87654321-4321-4321-4321-210987654321",
    "client_secret": "abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA"
  },
  "graph_api": {
    "base_url": "https://graph.microsoft.com",
    "version": "v1.0",
    "scope": "https://graph.microsoft.com/.default"
  }
}
```

⚠️ **Important**: Add `config.json` to your `.gitignore` file!

### Authentication Code Implementation

#### Basic Authentication Class

```python
"""
Microsoft Graph API OAuth2 Authenticator using MSAL
"""
import os
import msal
from typing import Optional
from dotenv import load_dotenv

class GraphAuthenticator:
    """
    Handles OAuth2 authentication for Microsoft Graph API
    using the client credentials flow.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None
    ):
        """
        Initialize the authenticator.

        Args:
            client_id: Azure AD application (client) ID
            tenant_id: Azure AD directory (tenant) ID
            client_secret: Azure AD client secret
            scope: OAuth2 scope (default: https://graph.microsoft.com/.default)
        """
        # Load from environment if not provided
        load_dotenv()

        self.client_id = client_id or os.getenv('AZURE_CLIENT_ID')
        self.tenant_id = tenant_id or os.getenv('AZURE_TENANT_ID')
        self.client_secret = client_secret or os.getenv('AZURE_CLIENT_SECRET')
        self.scope = scope or os.getenv(
            'GRAPH_API_SCOPE',
            'https://graph.microsoft.com/.default'
        )

        # Validate required parameters
        if not all([self.client_id, self.tenant_id, self.client_secret]):
            raise ValueError(
                "Missing required credentials. Provide client_id, tenant_id, "
                "and client_secret either as parameters or environment variables."
            )

        # Build authority URL
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"

        # Initialize MSAL confidential client
        self.app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )

        # Token cache
        self._access_token: Optional[str] = None

    def get_access_token(self) -> str:
        """
        Acquire an access token using client credentials flow.

        Returns:
            str: Valid access token

        Raises:
            Exception: If token acquisition fails
        """
        # Try to get token from cache first
        result = self.app.acquire_token_silent(
            scopes=[self.scope],
            account=None
        )

        # If no cached token, acquire new token
        if not result:
            result = self.app.acquire_token_for_client(
                scopes=[self.scope]
            )

        # Check for errors
        if "error" in result:
            error_description = result.get(
                "error_description",
                result.get("error")
            )
            raise Exception(
                f"Authentication failed: {error_description}"
            )

        # Cache and return token
        self._access_token = result["access_token"]
        return self._access_token

    def get_auth_header(self) -> dict:
        """
        Get authorization header for API requests.

        Returns:
            dict: Headers dictionary with Bearer token
        """
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
```

#### Test Authentication

Create `test_auth.py`:

```python
from graph_authenticator import GraphAuthenticator

# Initialize authenticator
auth = GraphAuthenticator()

try:
    # Get access token
    token = auth.get_access_token()
    print("✅ Authentication successful!")
    print(f"Token preview: {token[:50]}...")

    # Get auth headers
    headers = auth.get_auth_header()
    print(f"✅ Authorization headers ready")

except Exception as e:
    print(f"❌ Authentication failed: {e}")
```

Run the test:

```bash
python test_auth.py
```

Expected output:
```
✅ Authentication successful!
Token preview: eyJ0eXAiOiJKV1QiLCJub25jZSI6IlVhTzBTNEpYVUQxN...
✅ Authorization headers ready
```

## SharePoint Lists Integration

### Understanding SharePoint Site and List IDs

Before accessing SharePoint Lists, you need to identify:

1. **Site ID**: The unique identifier for your SharePoint site
2. **List ID**: The unique identifier for the specific List

### Finding Your SharePoint Site ID

#### Method 1: Using Graph API Explorer

Use the Graph API to find your site:

```python
import requests
from graph_authenticator import GraphAuthenticator

auth = GraphAuthenticator()
headers = auth.get_auth_header()

# Get site by hostname and site path
# Format: GET /sites/{hostname}:/{site-path}
site_url = "yourtenant.sharepoint.com:/sites/yoursite"
endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_url}"

response = requests.get(endpoint, headers=headers)
site_data = response.json()

print(f"Site ID: {site_data['id']}")
print(f"Site Name: {site_data['displayName']}")
print(f"Web URL: {site_data['webUrl']}")
```

#### Method 2: Using Root Site and Search

```python
# Get root site
endpoint = "https://graph.microsoft.com/v1.0/sites/root"
response = requests.get(endpoint, headers=headers)
root_site = response.json()

print(f"Root Site ID: {root_site['id']}")

# Search for sites
search_endpoint = "https://graph.microsoft.com/v1.0/sites?search=yoursite"
response = requests.get(search_endpoint, headers=headers)
sites = response.json()

for site in sites.get('value', []):
    print(f"Site: {site['displayName']} - ID: {site['id']}")
```

### Getting Lists from a SharePoint Site

Once you have the Site ID, get all Lists:

```python
import requests
from typing import List, Dict
from graph_authenticator import GraphAuthenticator

class SharePointClient:
    """Client for SharePoint operations via Microsoft Graph API"""

    def __init__(self, site_id: str):
        """
        Initialize SharePoint client.

        Args:
            site_id: SharePoint site ID
        """
        self.auth = GraphAuthenticator()
        self.site_id = site_id
        self.base_url = "https://graph.microsoft.com/v1.0"

    def get_lists(self) -> List[Dict]:
        """
        Get all lists in the SharePoint site.

        Returns:
            List of list objects with metadata
        """
        endpoint = f"{self.base_url}/sites/{self.site_id}/lists"
        headers = self.auth.get_auth_header()

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()

        data = response.json()
        return data.get('value', [])

    def get_list_by_name(self, list_name: str) -> Dict:
        """
        Get a specific list by display name.

        Args:
            list_name: Display name of the list

        Returns:
            List object with metadata
        """
        lists = self.get_lists()

        for lst in lists:
            if lst['displayName'].lower() == list_name.lower():
                return lst

        raise ValueError(f"List '{list_name}' not found")

    def get_list_items(
        self,
        list_id: str,
        select_fields: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        top: int = 100
    ) -> List[Dict]:
        """
        Get items from a SharePoint List.

        Args:
            list_id: List ID
            select_fields: Specific fields to retrieve (e.g., ['Title', 'Status'])
            filter_query: OData filter query (e.g., "fields/Status eq 'Active'")
            top: Maximum number of items to return

        Returns:
            List of list item objects
        """
        endpoint = f"{self.base_url}/sites/{self.site_id}/lists/{list_id}/items"

        # Build query parameters
        params = {
            'expand': 'fields',
            '$top': top
        }

        if select_fields:
            fields_select = ','.join(select_fields)
            params['expand'] = f'fields(select={fields_select})'

        if filter_query:
            params['$filter'] = filter_query

        headers = self.auth.get_auth_header()
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get('value', [])
```

### Example: Reading SharePoint List Items

```python
# Initialize client with your site ID
site_id = "yourtenant.sharepoint.com,abc-123-def,xyz-456-ghi"
sp_client = SharePointClient(site_id)

# Example 1: Get all lists in the site
print("=== All Lists ===")
lists = sp_client.get_lists()
for lst in lists:
    print(f"List: {lst['displayName']}")
    print(f"  ID: {lst['id']}")
    print(f"  Template: {lst['list']['template']}")
    print()

# Example 2: Get a specific list by name
print("=== Get Specific List ===")
my_list = sp_client.get_list_by_name("Tasks")
print(f"List Name: {my_list['displayName']}")
print(f"List ID: {my_list['id']}")
print(f"Created: {my_list['createdDateTime']}")

# Example 3: Get all items from a list
print("\n=== All List Items ===")
list_id = my_list['id']
items = sp_client.get_list_items(list_id)

for item in items:
    fields = item.get('fields', {})
    print(f"Item ID: {item['id']}")
    print(f"  Title: {fields.get('Title', 'N/A')}")
    print(f"  Created: {item['createdDateTime']}")
    print()

# Example 4: Get specific fields
print("=== Specific Fields ===")
items = sp_client.get_list_items(
    list_id,
    select_fields=['Title', 'Status', 'Priority', 'AssignedTo']
)

for item in items:
    fields = item['fields']
    print(f"{fields.get('Title')} - Status: {fields.get('Status')}")

# Example 5: Filter items
print("\n=== Filtered Items ===")
active_items = sp_client.get_list_items(
    list_id,
    filter_query="fields/Status eq 'Active'",
    select_fields=['Title', 'Status', 'DueDate']
)

print(f"Found {len(active_items)} active items")
for item in active_items:
    fields = item['fields']
    print(f"  {fields.get('Title')} - Due: {fields.get('DueDate')}")
```

### Advanced SharePoint Operations

#### Pagination for Large Lists

```python
def get_all_list_items_paginated(self, list_id: str) -> List[Dict]:
    """
    Get all items from a list with pagination support.

    Args:
        list_id: List ID

    Returns:
        All list items across all pages
    """
    all_items = []
    endpoint = f"{self.base_url}/sites/{self.site_id}/lists/{list_id}/items"
    params = {'expand': 'fields', '$top': 200}

    headers = self.auth.get_auth_header()

    while endpoint:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        all_items.extend(data.get('value', []))

        # Get next page URL
        endpoint = data.get('@odata.nextLink')
        params = {}  # NextLink already includes parameters

    return all_items
```

## Email Operations Integration

### Email Client Implementation

```python
import requests
from typing import List, Optional, Dict
from graph_authenticator import GraphAuthenticator

class EmailClient:
    """Client for email operations via Microsoft Graph API"""

    def __init__(self, user_email: Optional[str] = None):
        """
        Initialize email client.

        Args:
            user_email: User email address or user principal name.
                       If None, uses 'me' endpoint (requires delegated permissions)
                       For app-only auth, must provide user email.
        """
        self.auth = GraphAuthenticator()
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.user_email = user_email

        # Build user endpoint
        if user_email:
            self.user_endpoint = f"users/{user_email}"
        else:
            self.user_endpoint = "me"

    def send_email(
        self,
        subject: str,
        body: str,
        to_recipients: List[str],
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        body_type: str = "text",
        importance: str = "normal",
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send an email.

        Args:
            subject: Email subject
            body: Email body content
            to_recipients: List of recipient email addresses
            cc_recipients: List of CC recipient email addresses
            bcc_recipients: List of BCC recipient email addresses
            body_type: 'text' or 'html'
            importance: 'low', 'normal', or 'high'
            attachments: List of attachment objects

        Returns:
            bool: True if sent successfully
        """
        endpoint = f"{self.base_url}/{self.user_endpoint}/sendMail"
        headers = self.auth.get_auth_header()

        # Build recipient lists
        to_list = [
            {"emailAddress": {"address": email}}
            for email in to_recipients
        ]

        cc_list = [
            {"emailAddress": {"address": email}}
            for email in (cc_recipients or [])
        ]

        bcc_list = [
            {"emailAddress": {"address": email}}
            for email in (bcc_recipients or [])
        ]

        # Build message payload
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": body_type.capitalize(),
                    "content": body
                },
                "toRecipients": to_list,
                "importance": importance
            }
        }

        # Add CC recipients if provided
        if cc_list:
            message["message"]["ccRecipients"] = cc_list

        # Add BCC recipients if provided
        if bcc_list:
            message["message"]["bccRecipients"] = bcc_list

        # Add attachments if provided
        if attachments:
            message["message"]["attachments"] = attachments

        # Send email
        response = requests.post(endpoint, headers=headers, json=message)
        response.raise_for_status()

        return response.status_code == 202

    def get_messages(
        self,
        folder: str = "inbox",
        top: int = 10,
        select_fields: Optional[List[str]] = None,
        filter_query: Optional[str] = None
    ) -> List[Dict]:
        """
        Get messages from a mail folder.

        Args:
            folder: Folder name (inbox, sentitems, drafts, deleteditems)
            top: Maximum number of messages to return
            select_fields: Specific fields to retrieve
            filter_query: OData filter query

        Returns:
            List of message objects
        """
        endpoint = f"{self.base_url}/{self.user_endpoint}/mailFolders/{folder}/messages"

        params = {'$top': top}

        if select_fields:
            params['$select'] = ','.join(select_fields)

        if filter_query:
            params['$filter'] = filter_query

        headers = self.auth.get_auth_header()
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get('value', [])

    def get_unread_messages(self, top: int = 50) -> List[Dict]:
        """
        Get unread messages from inbox.

        Args:
            top: Maximum number of messages to return

        Returns:
            List of unread message objects
        """
        return self.get_messages(
            folder="inbox",
            top=top,
            filter_query="isRead eq false"
        )

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark a message as read.

        Args:
            message_id: Message ID

        Returns:
            bool: True if successful
        """
        endpoint = f"{self.base_url}/{self.user_endpoint}/messages/{message_id}"
        headers = self.auth.get_auth_header()

        payload = {"isRead": True}

        response = requests.patch(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        return response.status_code == 200

    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark a message as unread.

        Args:
            message_id: Message ID

        Returns:
            bool: True if successful
        """
        endpoint = f"{self.base_url}/{self.user_endpoint}/messages/{message_id}"
        headers = self.auth.get_auth_header()

        payload = {"isRead": False}

        response = requests.patch(endpoint, headers=headers, json=payload)
        response.raise_for_status()

        return response.status_code == 200

    def get_message_by_id(self, message_id: str) -> Dict:
        """
        Get a specific message by ID.

        Args:
            message_id: Message ID

        Returns:
            Message object
        """
        endpoint = f"{self.base_url}/{self.user_endpoint}/messages/{message_id}"
        headers = self.auth.get_auth_header()

        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()

        return response.json()
```

### Example: Email Operations

```python
# Initialize email client
# For app-only auth, provide the user's email address
email_client = EmailClient(user_email="[email protected]")

# Example 1: Send a simple email
print("=== Sending Simple Email ===")
email_client.send_email(
    subject="Test Email from Graph API",
    body="This is a test email sent via Microsoft Graph API.",
    to_recipients=["[email protected]"]
)
print("✅ Email sent successfully")

# Example 2: Send HTML email with CC
print("\n=== Sending HTML Email with CC ===")
html_body = """
<html>
    <body>
        <h1>Project Update</h1>
        <p>Dear Team,</p>
        <p>This is an important update about our project:</p>
        <ul>
            <li><strong>Status:</strong> On Track</li>
            <li><strong>Next Milestone:</strong> Phase 2 Completion</li>
            <li><strong>Due Date:</strong> End of Month</li>
        </ul>
        <p>Best regards,<br>Project Manager</p>
    </body>
</html>
"""

email_client.send_email(
    subject="Project Status Update",
    body=html_body,
    to_recipients=["[email protected]", "[email protected]"],
    cc_recipients=["[email protected]", "[email protected]"],
    body_type="html",
    importance="high"
)
print("✅ HTML email with CC sent successfully")

# Example 3: Read inbox messages
print("\n=== Reading Inbox Messages ===")
messages = email_client.get_messages(folder="inbox", top=5)

for msg in messages:
    print(f"Subject: {msg['subject']}")
    print(f"From: {msg['from']['emailAddress']['address']}")
    print(f"Received: {msg['receivedDateTime']}")
    print(f"Is Read: {msg['isRead']}")
    print(f"Has Attachments: {msg['hasAttachments']}")
    print("-" * 60)

# Example 4: Get unread messages
print("\n=== Unread Messages ===")
unread = email_client.get_unread_messages(top=10)
print(f"Found {len(unread)} unread messages")

for msg in unread:
    print(f"  - {msg['subject']} (from {msg['from']['emailAddress']['address']})")

# Example 5: Mark messages as read
print("\n=== Marking Messages as Read ===")
if unread:
    for msg in unread[:3]:  # Mark first 3 as read
        message_id = msg['id']
        email_client.mark_as_read(message_id)
        print(f"✅ Marked as read: {msg['subject']}")

# Example 6: Get specific message details
print("\n=== Message Details ===")
if messages:
    msg_id = messages[0]['id']
    details = email_client.get_message_by_id(msg_id)

    print(f"Subject: {details['subject']}")
    print(f"Body Preview: {details['bodyPreview'][:100]}...")
    print(f"Importance: {details['importance']}")

    if details.get('ccRecipients'):
        print("CC Recipients:")
        for cc in details['ccRecipients']:
            print(f"  - {cc['emailAddress']['address']}")

# Example 7: Search for specific emails
print("\n=== Search for Specific Emails ===")
urgent_emails = email_client.get_messages(
    folder="inbox",
    filter_query="importance eq 'high' and isRead eq false",
    top=20
)

print(f"Found {len(urgent_emails)} urgent unread emails")
for msg in urgent_emails:
    print(f"  - {msg['subject']}")
```

## Complete Code Examples

### Complete Implementation

Here's a complete example combining both SharePoint and Email operations:

```python
"""
complete_example.py - Complete Microsoft Graph API integration example
"""
import os
from dotenv import load_dotenv
from graph_authenticator import GraphAuthenticator
from sharepoint_client import SharePointClient
from email_client import EmailClient

def main():
    """Main example demonstrating Graph API integration"""

    # Load environment variables
    load_dotenv()

    print("=" * 70)
    print("Microsoft Graph API Integration Demo")
    print("=" * 70)

    # ========================================================================
    # SHAREPOINT OPERATIONS
    # ========================================================================

    print("\n" + "=" * 70)
    print("SHAREPOINT OPERATIONS")
    print("=" * 70)

    # Initialize SharePoint client
    site_id = os.getenv('SHAREPOINT_SITE_ID')
    sp_client = SharePointClient(site_id)

    # Get all lists
    print("\n1. Getting all SharePoint Lists...")
    lists = sp_client.get_lists()
    print(f"   Found {len(lists)} lists:")
    for lst in lists[:5]:  # Show first 5
        print(f"   - {lst['displayName']}")

    # Get specific list
    print("\n2. Getting 'Tasks' list...")
    try:
        tasks_list = sp_client.get_list_by_name("Tasks")
        print(f"   List ID: {tasks_list['id']}")

        # Get list items
        print("\n3. Getting items from 'Tasks' list...")
        items = sp_client.get_list_items(
            tasks_list['id'],
            select_fields=['Title', 'Status', 'Priority'],
            top=10
        )
        print(f"   Found {len(items)} items:")
        for item in items[:3]:  # Show first 3
            fields = item['fields']
            print(f"   - {fields.get('Title')} (Status: {fields.get('Status')})")

    except ValueError as e:
        print(f"   ⚠️  {e}")

    # ========================================================================
    # EMAIL OPERATIONS
    # ========================================================================

    print("\n" + "=" * 70)
    print("EMAIL OPERATIONS")
    print("=" * 70)

    # Initialize email client
    user_email = os.getenv('USER_EMAIL')
    email_client = EmailClient(user_email=user_email)

    # Get inbox messages
    print("\n1. Getting inbox messages...")
    messages = email_client.get_messages(folder="inbox", top=5)
    print(f"   Found {len(messages)} recent messages:")
    for msg in messages[:3]:
        print(f"   - {msg['subject'][:50]}...")

    # Get unread messages
    print("\n2. Getting unread messages...")
    unread = email_client.get_unread_messages(top=10)
    print(f"   Found {len(unread)} unread messages")

    # Send notification email about SharePoint items
    if items:
        print("\n3. Sending summary email...")

        # Build email body
        html_body = """
        <html>
        <body>
            <h2>SharePoint Tasks Summary</h2>
            <p>Here's a summary of recent tasks:</p>
            <table border="1" cellpadding="5">
                <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Priority</th>
                </tr>
        """

        for item in items[:5]:
            fields = item['fields']
            html_body += f"""
                <tr>
                    <td>{fields.get('Title', 'N/A')}</td>
                    <td>{fields.get('Status', 'N/A')}</td>
                    <td>{fields.get('Priority', 'N/A')}</td>
                </tr>
            """

        html_body += """
            </table>
            <p>This email was generated automatically by the Graph API integration.</p>
        </body>
        </html>
        """

        # Send email
        email_client.send_email(
            subject="Daily SharePoint Tasks Summary",
            body=html_body,
            to_recipients=[user_email],
            cc_recipients=["[email protected]"],
            body_type="html",
            importance="normal"
        )
        print("   ✅ Summary email sent successfully")

    # Mark old unread messages as read
    if unread:
        print("\n4. Marking old messages as read...")
        for msg in unread[:2]:  # Mark first 2 as read
            email_client.mark_as_read(msg['id'])
            print(f"   ✅ Marked as read: {msg['subject'][:40]}...")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)

if __name__ == "__main__":
    main()
```

### Required .env File

```bash
# Azure AD Credentials
AZURE_CLIENT_ID=your-client-id-here
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# Graph API Settings
GRAPH_API_SCOPE=https://graph.microsoft.com/.default

# SharePoint Settings
SHAREPOINT_SITE_ID=yourtenant.sharepoint.com,site-guid,web-guid

# Email Settings
USER_EMAIL=[email protected]
```

## Security Best Practices

### 1. Credential Management

**DO:**
- ✅ Store credentials in environment variables or Azure Key Vault
- ✅ Use `.env` files for local development (add to `.gitignore`)
- ✅ Rotate client secrets regularly (every 6-12 months)
- ✅ Use managed identities when running on Azure

**DON'T:**
- ❌ Never commit secrets to version control
- ❌ Never hardcode credentials in source code
- ❌ Never share secrets in chat/email
- ❌ Never use production secrets in development

### 2. Permission Management

**Principle of Least Privilege:**
- Only request permissions your application actually needs
- Use read-only permissions (`*.Read`) when you don't need write access
- Consider using `Sites.Selected` for specific SharePoint sites instead of `Sites.Read.All`

### 3. Token Security

```python
class SecureGraphAuthenticator(GraphAuthenticator):
    """Enhanced authenticator with security features"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._token_expiry = None

    def get_access_token(self) -> str:
        """Get access token with expiry tracking"""
        result = self.app.acquire_token_for_client(
            scopes=[self.scope]
        )

        if "error" in result:
            # Log error securely (don't log tokens/secrets)
            logger.error(
                f"Token acquisition failed: {result.get('error')}",
                extra={"error_code": result.get("error")}
            )
            raise Exception(f"Authentication failed: {result.get('error')}")

        # Track expiry
        import time
        self._token_expiry = time.time() + result.get('expires_in', 3600)

        return result["access_token"]

    def is_token_expired(self) -> bool:
        """Check if token is expired"""
        if not self._token_expiry:
            return True

        import time
        # Add 5-minute buffer
        return time.time() >= (self._token_expiry - 300)
```

### 4. Input Validation

```python
import re
from typing import List

def validate_email(email: str) -> bool:
    """Validate email address format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_recipients(recipients: List[str]) -> List[str]:
    """Validate and sanitize recipient list"""
    valid_recipients = []

    for email in recipients:
        email = email.strip()
        if validate_email(email):
            valid_recipients.append(email)
        else:
            print(f"⚠️  Invalid email address skipped: {email}")

    return valid_recipients

# Usage
to_recipients = sanitize_recipients([
    "[email protected]",
    "invalid-email",
    "[email protected]"
])
```

### 5. Error Handling

```python
import requests
from typing import Optional
import time

class GraphAPIError(Exception):
    """Base exception for Graph API errors"""
    pass

class AuthenticationError(GraphAPIError):
    """Authentication failed"""
    pass

class PermissionError(GraphAPIError):
    """Insufficient permissions"""
    pass

class RateLimitError(GraphAPIError):
    """Rate limit exceeded"""
    pass

def handle_graph_api_response(response: requests.Response) -> dict:
    """
    Handle Graph API response with proper error handling.

    Args:
        response: requests Response object

    Returns:
        Response JSON data

    Raises:
        Appropriate exception based on error type
    """
    if response.status_code == 200:
        return response.json()

    elif response.status_code == 201:
        return response.json() if response.text else {}

    elif response.status_code == 202:
        return {}

    elif response.status_code == 401:
        raise AuthenticationError("Authentication failed. Check credentials.")

    elif response.status_code == 403:
        raise PermissionError(
            "Insufficient permissions. Check Azure AD app permissions."
        )

    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After', 60)
        raise RateLimitError(
            f"Rate limit exceeded. Retry after {retry_after} seconds."
        )

    elif response.status_code >= 500:
        raise GraphAPIError(
            f"Server error: {response.status_code}. Try again later."
        )

    else:
        error_data = response.json() if response.text else {}
        error_msg = error_data.get('error', {}).get('message', 'Unknown error')
        raise GraphAPIError(f"Request failed: {error_msg}")

def retry_on_rate_limit(func, max_retries: int = 3):
    """
    Decorator to retry on rate limit errors.

    Args:
        func: Function to retry
        max_retries: Maximum number of retries
    """
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise

                # Extract retry-after from error message or use exponential backoff
                wait_time = 2 ** attempt
                print(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)

        return func(*args, **kwargs)

    return wrapper
```

### 6. Logging

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure secure logging
def setup_logging():
    """Setup secure logging configuration"""

    # Create logger
    logger = logging.getLogger('graph_api')
    logger.setLevel(logging.INFO)

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # File handler (for production)
    file_handler = RotatingFileHandler(
        'graph_api.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Usage
logger = setup_logging()

# Good: Log actions without sensitive data
logger.info("Sending email to recipient", extra={"subject": "Meeting"})

# Bad: Never log tokens, secrets, or full email content
# logger.info(f"Token: {token}")  # ❌ NEVER DO THIS
```

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Authentication Failed

**Error Message:**
```
AuthenticationException: Token acquisition failed: invalid_client
```

**Possible Causes:**
1. Incorrect client ID or tenant ID
2. Expired or invalid client secret
3. Wrong authority URL

**Solutions:**
1. Verify credentials in Azure Portal:
   - Go to Azure AD > App registrations > Your app
   - Check Application (client) ID
   - Check Directory (tenant) ID
2. Create a new client secret if expired
3. Ensure authority URL format: `https://login.microsoftonline.com/{tenant_id}`

#### Issue 2: Insufficient Permissions

**Error Message:**
```
PermissionException: Insufficient permissions to complete the operation
```

**Possible Causes:**
1. Required permissions not added to app
2. Admin consent not granted
3. Using application permissions without specifying user

**Solutions:**
1. Add required permissions:
   - Azure AD > App registrations > Your app > API permissions
   - Add missing permissions
2. Click "Grant admin consent for [Your Org]"
3. For application permissions, specify user email in API calls:
   - Use `/users/{email}/...` instead of `/me/...`

#### Issue 3: Site or List Not Found

**Error Message:**
```
404 Not Found: The requested site/list does not exist
```

**Solutions:**
1. Verify site ID format:
   ```python
   # Correct format: hostname,site-guid,web-guid
   site_id = "contoso.sharepoint.com,abc123,def456"
   ```

2. Test site access:
   ```python
   # Verify site exists
   endpoint = f"https://graph.microsoft.com/v1.0/sites/{site_id}"
   response = requests.get(endpoint, headers=headers)
   print(response.json())
   ```

3. Check permissions:
   - Ensure `Sites.Read.All` or `Sites.Selected` is granted

#### Issue 4: Rate Limiting

**Error Message:**
```
429 Too Many Requests: Retry-After: 120
```

**Solutions:**
1. Implement exponential backoff (see security best practices)
2. Reduce request frequency
3. Use batching for multiple operations:
   ```python
   # Batch requests to reduce API calls
   batch_endpoint = "https://graph.microsoft.com/v1.0/$batch"
   ```

#### Issue 5: Email Not Sending

**Error Message:**
```
ErrorInvalidRecipients: At least one recipient isn't valid
```

**Solutions:**
1. Validate email addresses before sending
2. Check recipient addresses exist in your organization
3. For external recipients, ensure external sharing is enabled
4. Use proper email format:
   ```python
   # Correct format
   to_recipients = ["[email protected]"]  # ✅

   # Incorrect format
   to_recipients = ["John Doe <john@contoso com>"]  # ❌
   ```

#### Issue 6: Token Cache Errors

**Error Message:**
```
PermissionError: [Errno 13] Permission denied: 'token_cache.bin'
```

**Solutions:**
1. Check file permissions:
   ```bash
   chmod 600 token_cache.bin
   ```

2. Ensure cache directory exists:
   ```python
   import os
   cache_dir = ".cache"
   os.makedirs(cache_dir, exist_ok=True)
   ```

### Debugging Tips

#### Enable Detailed Logging

```python
import logging
import http.client as http_client

# Enable HTTP request/response logging
http_client.HTTPConnection.debuglevel = 1

# Enable detailed logging
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

#### Test with Graph Explorer

Use [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) to test API calls:

1. Navigate to Graph Explorer
2. Sign in with your account
3. Test your queries before implementing in code
4. Copy working queries to your application

#### Verify Permissions Programmatically

```python
def check_permissions(auth: GraphAuthenticator):
    """Check what permissions the app has"""

    # Decode JWT token to see permissions
    import base64
    import json

    token = auth.get_access_token()

    # JWT tokens have 3 parts separated by dots
    parts = token.split('.')

    # Decode payload (second part)
    # Add padding if needed
    payload = parts[1]
    payload += '=' * (4 - len(payload) % 4)

    decoded = base64.b64decode(payload)
    token_data = json.loads(decoded)

    # Print permissions
    print("App Permissions (roles):")
    for role in token_data.get('roles', []):
        print(f"  - {role}")
```

## Resources

### Official Documentation

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/)
- [Graph API Reference](https://learn.microsoft.com/en-us/graph/api/overview)
- [MSAL Python Documentation](https://learn.microsoft.com/en-us/entra/msal/python/)
- [Graph Permissions Reference](https://learn.microsoft.com/en-us/graph/permissions-reference)

### Interactive Tools

- [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer) - Test API calls interactively
- [Azure Portal](https://portal.azure.com) - Manage app registrations
- [JWT Decoder](https://jwt.ms) - Decode and inspect access tokens

### SDKs and Libraries

- [Microsoft Graph Python SDK](https://github.com/microsoftgraph/msgraph-sdk-python)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Requests Library](https://requests.readthedocs.io/)

### Code Samples

- [Microsoft Graph Samples](https://github.com/microsoftgraph)
- [Azure AD Samples](https://github.com/Azure-Samples)

### Community Resources

- [Microsoft Tech Community](https://techcommunity.microsoft.com/t5/microsoft-graph/ct-p/microsoft-graph)
- [Stack Overflow - microsoft-graph](https://stackoverflow.com/questions/tagged/microsoft-graph)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/tags/158/ms-graph)

## Next Steps

1. **Set up your Azure AD app** following the steps in this guide
2. **Test authentication** with the provided code examples
3. **Implement SharePoint integration** for your specific use case
4. **Implement email operations** as needed
5. **Add error handling and logging** for production use
6. **Implement security best practices** before deployment
7. **Set up monitoring** to track API usage and errors

## License

This guide is provided as-is for educational and development purposes.

## Support

For issues and questions:
- Review this guide's troubleshooting section
- Check official Microsoft Graph documentation
- Test with Graph Explorer
- Search Microsoft Q&A and Stack Overflow
- Contact Microsoft Support for licensing/billing questions

---

**Last Updated:** 2025-01-16
**API Version:** Microsoft Graph v1.0
**Author:** AI Engineering Playground
