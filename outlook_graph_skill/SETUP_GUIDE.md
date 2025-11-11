# Outlook Graph API Skill - Setup Guide

This guide will walk you through the complete setup process for the Outlook Graph API Skill.

## Table of Contents

1. [Azure AD Configuration](#azure-ad-configuration)
2. [Local Setup](#local-setup)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)

## Azure AD Configuration

### Step 1: Register an Application

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Azure Active Directory**
3. Select **App registrations** from the left menu
4. Click **+ New registration**

### Step 2: Configure Basic Settings

1. **Name**: Enter a descriptive name (e.g., "Outlook Graph API Skill")
2. **Supported account types**: Select "Accounts in this organizational directory only"
3. **Redirect URI**: Leave blank (not needed for service-to-service auth)
4. Click **Register**

### Step 3: Note Important IDs

After registration, you'll see the app overview page. Copy these values:

- **Application (client) ID**: e.g., `12345678-1234-1234-1234-123456789012`
- **Directory (tenant) ID**: e.g., `87654321-4321-4321-4321-210987654321`

**Save these values** - you'll need them for configuration.

### Step 4: Create a Client Secret

1. In your app's page, go to **Certificates & secrets**
2. Click **+ New client secret**
3. Add a description (e.g., "Outlook Skill Secret")
4. Select expiration period:
   - **6 months** - More secure, requires rotation
   - **12 months** - Balanced approach
   - **24 months** - Less maintenance, but less secure
5. Click **Add**
6. **IMMEDIATELY COPY THE SECRET VALUE** - you can't view it again!

The secret looks like: `abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA`

⚠️ **IMPORTANT**: Store this securely and never commit it to version control!

### Step 5: Configure API Permissions

1. In your app's page, go to **API permissions**
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Application permissions** (not Delegated)
5. Search for and add these permissions:

   **For Reading Emails:**
   - `Mail.Read` - Read mail in all mailboxes
   - `MailboxSettings.Read` - Read mailbox settings

   **For Sending Emails:**
   - `Mail.Send` - Send mail as any user

   **For Full Management:**
   - `Mail.ReadWrite` - Read and write mail in all mailboxes

6. Click **Add permissions**

### Step 6: Grant Admin Consent

⚠️ **Required**: Application permissions need admin consent.

1. After adding permissions, click **Grant admin consent for [Your Org]**
2. Confirm by clicking **Yes**
3. Wait for the status to change to "Granted"

✅ All permissions should now show a green checkmark under "Status"

### Step 7: Verify Configuration

Your app should now have:
- ✅ Application (client) ID
- ✅ Directory (tenant) ID
- ✅ Client secret
- ✅ Permissions granted with admin consent

## Local Setup

### Step 1: Install Python Dependencies

Ensure you have Python 3.8 or higher:

```bash
python --version
```

Navigate to the skill directory:

```bash
cd outlook_graph_skill
```

Install required packages:

```bash
pip install -r requirements.txt
```

### Step 2: Create Configuration

Choose one of these configuration methods:

#### Method A: Environment Variables (Recommended)

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your actual values:

```bash
AZURE_CLIENT_ID=12345678-1234-1234-1234-123456789012
AZURE_TENANT_ID=87654321-4321-4321-4321-210987654321
AZURE_CLIENT_SECRET=abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA
GRAPH_API_SCOPES=https://graph.microsoft.com/.default
```

3. Load environment variables (if using python-dotenv):

```python
from dotenv import load_dotenv
load_dotenv()
```

#### Method B: JSON Configuration

1. Copy the example config:

```bash
cp config/config.example.json config/config.json
```

2. Edit `config/config.json`:

```json
{
  "auth": {
    "client_id": "12345678-1234-1234-1234-123456789012",
    "tenant_id": "87654321-4321-4321-4321-210987654321",
    "client_secret": "abC1d~EfG2hI3jK4lM5nO6pQ7rS8tU9vW0xY1zA"
  }
}
```

### Step 3: Verify Installation

Create a test script `test_setup.py`:

```python
from outlook_graph_skill import SkillConfig, EmailClient

# Test configuration loading
config = SkillConfig.from_env()  # or SkillConfig.from_json("config/config.json")

# Test authentication
client = EmailClient(config)

# Validate token acquisition
try:
    client.authenticator.validate_token()
    print("✅ Setup successful! Authentication working.")
except Exception as e:
    print(f"❌ Setup failed: {e}")
```

Run the test:

```bash
python test_setup.py
```

## Testing

### Test 1: Read Inbox

```python
from outlook_graph_skill import SkillConfig, EmailClient

config = SkillConfig.from_env()
client = EmailClient(config)

# Get recent messages
messages = client.get_messages(folder="inbox", top=5)

print(f"Found {len(messages)} messages:")
for msg in messages:
    print(f"  - {msg.subject}")
```

### Test 2: Send Test Email

```python
client.send_email(
    subject="Test Email from Graph API Skill",
    body="This is a test. If you receive this, the skill is working!",
    to_recipients=["your-email@example.com"],
)
print("✅ Test email sent!")
```

### Test 3: Search Emails

```python
from outlook_graph_skill.mailbox import EmailSearch

search = EmailSearch().is_read(False)
unread = client.search_emails(search, top=10)

print(f"Found {len(unread)} unread messages")
```

## Troubleshooting

### Issue 1: Authentication Failed

**Error**: `AuthenticationException: Token acquisition failed`

**Possible Causes**:
1. Incorrect client ID, tenant ID, or client secret
2. Client secret expired
3. Permissions not granted

**Solutions**:
1. Double-check all IDs and secret in your configuration
2. Verify the client secret hasn't expired (check in Azure Portal)
3. Ensure admin consent was granted for all permissions
4. Try creating a new client secret

### Issue 2: Insufficient Permissions

**Error**: `PermissionException: Insufficient permissions`

**Possible Causes**:
1. Required permissions not added
2. Admin consent not granted
3. Using Delegated instead of Application permissions

**Solutions**:
1. Go to Azure Portal > App registrations > Your app > API permissions
2. Verify all required permissions are listed
3. Ensure they are **Application** permissions (not Delegated)
4. Click "Grant admin consent" again
5. Wait 5-10 minutes for changes to propagate

### Issue 3: Rate Limiting

**Error**: `RateLimitException: API rate limit exceeded`

**Solutions**:
1. The skill will automatically retry - just wait
2. Reduce request frequency
3. Implement batching for multiple operations

### Issue 4: Token Cache Errors

**Error**: `TokenException: Failed to save token cache`

**Possible Causes**:
1. Insufficient file permissions
2. Invalid cache directory path

**Solutions**:
1. Ensure the `.cache` directory is writable
2. Check directory permissions: `chmod 700 .cache`
3. Try disabling cache temporarily:

```python
from outlook_graph_skill.config import CacheConfig

cache_config = CacheConfig(enabled=False)
config = SkillConfig(auth_config=auth_config, cache_config=cache_config)
```

### Issue 5: Network/SSL Errors

**Error**: `SSLError` or `ConnectionError`

**Solutions**:
1. Check internet connectivity
2. Verify firewall settings allow HTTPS to `login.microsoftonline.com` and `graph.microsoft.com`
3. Check proxy settings if behind corporate firewall
4. Update SSL certificates: `pip install --upgrade certifi`

## Security Checklist

Before deploying to production:

- [ ] Client secret stored securely (not in code)
- [ ] `.env` and `config.json` in `.gitignore`
- [ ] Token cache directory has restrictive permissions (700)
- [ ] Using least privilege permissions (only what's needed)
- [ ] Client secret rotation plan in place
- [ ] Logging configured appropriately (no secrets in logs)
- [ ] Error handling implemented
- [ ] Rate limiting handled

## Next Steps

1. Review the main [README.md](README.md) for usage examples
2. Check [examples/usage_examples.py](examples/usage_examples.py) for code samples
3. Implement your specific use cases
4. Set up monitoring and logging for production

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Review error messages carefully
3. Check Microsoft Graph API documentation
4. Verify Azure AD configuration
5. Test with [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)

## Resources

- [Azure Portal](https://portal.azure.com)
- [Microsoft Graph Documentation](https://learn.microsoft.com/en-us/graph/)
- [MSAL Python Guide](https://learn.microsoft.com/en-us/entra/msal/python/)
- [Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
- [Graph API Permissions Reference](https://learn.microsoft.com/en-us/graph/permissions-reference)
