# Quick Start Guide

Get started with the Outlook Graph API Skill in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Azure AD account with admin access
- 10 minutes for Azure setup

## Step 1: Azure AD Setup (5 minutes)

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration**
3. Name it "Outlook Graph Skill" → Register
4. Copy **Application (client) ID** and **Directory (tenant) ID**
5. Go to **Certificates & secrets** → **New client secret** → Copy the secret value
6. Go to **API permissions** → **Add permission** → **Microsoft Graph** → **Application permissions**
7. Add: `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`
8. Click **Grant admin consent**

## Step 2: Install (1 minute)

```bash
cd outlook_graph_skill
pip install -r requirements.txt
```

Dependencies include:
- `msal` - Microsoft Authentication
- `requests` - HTTP client
- `pydantic` & `pydantic-settings` - Configuration management

## Step 3: Configure (1 minute)

Create a `.env` file:

```bash
AZURE_CLIENT_ID=your-client-id-here
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
```

## Step 4: Test (1 minute)

Create `test.py`:

```python
from outlook_graph_skill import SkillConfig, EmailClient

# Load configuration (automatically loads from .env)
config = SkillConfig()

# Create client
client = EmailClient(config)

# Read inbox
messages = client.get_messages(folder="inbox", top=5)

print(f"✅ Success! Found {len(messages)} messages:")
for msg in messages:
    print(f"  - {msg.subject}")
```

Run it:

```bash
python test.py
```

## That's it!

You're ready to use the skill. The configuration now uses **Pydantic Settings** for:
- ✅ Automatic .env file loading
- ✅ Type validation
- ✅ Clear error messages
- ✅ IDE autocomplete support

Check out these resources:

- [Full Documentation](README.md)
- [Setup Guide](SETUP_GUIDE.md)
- [Usage Examples](examples/usage_examples.py)
- [Pydantic Migration Guide](PYDANTIC_MIGRATION.md)

## Common Use Cases

### Send an Email

```python
client.send_email(
    subject="Hello World",
    body="This is my first email!",
    to_recipients=["someone@example.com"],
)
```

### Find Unread Emails

```python
from outlook_graph_skill.mailbox import EmailSearch

search = EmailSearch().is_read(False)
unread = client.search_emails(search)

print(f"You have {len(unread)} unread messages")
```

### Search by Sender

```python
search = EmailSearch().from_sender("boss@example.com")
messages = client.search_emails(search)
```

### Get Emails with Attachments

```python
search = EmailSearch().with_attachments(True)
messages = client.search_emails(search, top=20)
```

## Need Help?

- Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions
- See [README.md](README.md) for comprehensive documentation
- Review [examples/usage_examples.py](examples/usage_examples.py) for more examples
