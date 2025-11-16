# Integrating OAuth2 Authentication with Google ADK for Workday API Access

## Overview

This guide demonstrates how to integrate OAuth2 authentication into a Google Agent Development Kit (ADK) agent to access Workday's REST APIs, specifically focusing on Purchase Order operations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding ADK OAuth2 Authentication](#understanding-adk-oauth2-authentication)
3. [Workday OAuth2 Setup](#workday-oauth2-setup)
4. [Implementation Guide](#implementation-guide)
5. [Complete Code Example](#complete-code-example)
6. [Testing and Deployment](#testing-and-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Components

- **Google Cloud Project** with ADK enabled
- **Workday Tenant** with API access
- **Python 3.10+** installed
- **ADK Python SDK** (`pip install google-adk`)

### Workday Requirements

- Administrator access to Workday tenant
- API Client registration permissions
- Access to Resource Management API

---

## Understanding ADK OAuth2 Authentication

### How ADK Handles OAuth2

The Google ADK simplifies OAuth2 authentication by:

1. **Managing Token Lifecycle**: Automatically handles token refresh
2. **Providing Valid Tokens**: Always supplies valid `access_token` to tool calls
3. **Supporting Multiple Flows**: Authorization Code, Client Credentials, JWT Bearer
4. **Abstracting Complexity**: Developers don't implement token refresh logic

### Key ADK Authentication Components

#### AuthScheme

Defines how an API expects authentication credentials:

```python
from google.adk.tools.auth_schemes import Oauth2

oauth_scheme = Oauth2(
    authorization_url="https://your-auth-server.com/auth",
    token_url="https://your-auth-server.com/token",
    scopes=["your:scope"],
)
```

#### AuthCredential

Holds initial information needed to start authentication:

```python
from google.adk.auth.auth_credential import AuthCredential, OAuth2Auth

auth_credential = AuthCredential(
    oauth2=OAuth2Auth(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET",
        auth_uri="https://authorization-url.com",
        token_uri="https://token-url.com"
    )
)
```

---

## Workday OAuth2 Setup

### Step 1: Register API Client in Workday

1. Log into your Workday tenant as an administrator
2. Navigate to **View API Clients** task
3. Click **Register API Client for Integrations**
4. Configure the following:
   - **Client Name**: `ADK-PurchaseOrder-Integration`
   - **Client Grant Type**: Select based on your use case:
     - **Authorization Code Grant** - For user-delegated access
     - **Client Credentials** - For server-to-server integration
     - **JWT Bearer Grant** - For service account authentication

### Step 2: Configure Scopes

Select the required functional area scopes:

- **Resource Management** (for Purchase Order access)
- **System** (if needed for tenant-level operations)

### Step 3: Save Credentials

After registration, Workday provides:
- **Client ID**
- **Client Secret**
- **Authorization Endpoint**
- **Token Endpoint**

**Important**: Store these securely (use environment variables or secret management).

### Workday OAuth2 Endpoints

The standard format for Workday OAuth2 endpoints:

```
Authorization URL: https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/authorize
Token URL: https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/token
```

Replace `{tenant}` with your Workday tenant name.

### Supported Grant Types

#### 1. Authorization Code Grant

Best for user-delegated access where users authenticate themselves:

```bash
# Step 1: Get Authorization Code
GET https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/authorize?
    response_type=code&
    client_id={CLIENT_ID}&
    redirect_uri={REDIRECT_URI}&
    scope={SCOPES}

# Step 2: Exchange Code for Token
POST https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code={AUTHORIZATION_CODE}&
client_id={CLIENT_ID}&
client_secret={CLIENT_SECRET}&
redirect_uri={REDIRECT_URI}
```

#### 2. Client Credentials Grant

Best for server-to-server integration:

```bash
POST https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/token
Authorization: Basic {BASE64(CLIENT_ID:CLIENT_SECRET)}
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
```

#### 3. Refresh Token

To refresh an expired access token:

```bash
POST https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
refresh_token={REFRESH_TOKEN}&
client_id={CLIENT_ID}&
client_secret={CLIENT_SECRET}
```

### Token Response

Successful authentication returns:

```json
{
  "access_token": "eyJraWQiOiI...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "v1.MR3tnW..."
}
```

---

## Workday Purchase Order API

### Available Endpoints

#### GET Purchase Orders

**Endpoint**: `/ccx/api/resourceManagement/v1/purchaseOrders`

**Supported Operations**:
- Get all purchase orders
- Get a specific purchase order by ID
- Search purchase orders by criteria

**Request Example**:
```http
GET /ccx/api/resourceManagement/v1/purchaseOrders
Authorization: Bearer {ACCESS_TOKEN}
Accept: application/json
```

**Query Parameters**:
- `limit` - Maximum number of results
- `offset` - Pagination offset
- `search` - Search criteria

**Response Structure**:
```json
{
  "data": [
    {
      "id": "PO-00001",
      "documentNumber": "PO-00001",
      "company": {
        "descriptor": "ABC Corp"
      },
      "supplier": {
        "descriptor": "Supplier Inc"
      },
      "purchaseOrderDate": "2025-01-15",
      "totalAmount": 15000.00,
      "currency": "USD",
      "status": "Approved",
      "lines": [
        {
          "lineNumber": 1,
          "description": "Office Supplies",
          "quantity": 100,
          "unitPrice": 150.00
        }
      ]
    }
  ]
}
```

#### GET Specific Purchase Order

**Endpoint**: `/ccx/api/resourceManagement/v1/purchaseOrders/{id}`

**Request Example**:
```http
GET /ccx/api/resourceManagement/v1/purchaseOrders/PO-00001
Authorization: Bearer {ACCESS_TOKEN}
Accept: application/json
```

### Creating Purchase Orders

**Note**: The REST API currently has limited support for creating purchase orders via POST. For purchase order creation, you may need to use the SOAP API:

**SOAP Operation**: `Submit_Purchase_Order` in the Resource Management WSDL

---

## Implementation Guide

### Step 1: Install Dependencies

```bash
pip install google-adk requests python-dotenv
```

### Step 2: Environment Configuration

Create a `.env` file:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# Workday OAuth2 Credentials
WORKDAY_TENANT=your_tenant_name
WORKDAY_CLIENT_ID=your_client_id
WORKDAY_CLIENT_SECRET=your_client_secret
WORKDAY_AUTHORIZATION_URL=https://wd2-impl-services1.workday.com/ccx/oauth2/your_tenant_name/authorize
WORKDAY_TOKEN_URL=https://wd2-impl-services1.workday.com/ccx/oauth2/your_tenant_name/token
WORKDAY_API_BASE_URL=https://wd2-impl-services1.workday.com/ccx/api

# OAuth2 Configuration
WORKDAY_SCOPES=system
REDIRECT_URI=http://localhost:8000/dev-ui
```

### Step 3: Define OAuth2 Scheme

```python
import os
from google.adk.tools.auth_schemes import Oauth2
from google.adk.auth.auth_credential import AuthCredential, OAuth2Auth

# Define OAuth2 scheme for Workday
workday_oauth_scheme = Oauth2(
    authorization_url=os.getenv("WORKDAY_AUTHORIZATION_URL"),
    token_url=os.getenv("WORKDAY_TOKEN_URL"),
    scopes=[os.getenv("WORKDAY_SCOPES", "system")],
)

# Create initial auth credential
workday_auth_credential = AuthCredential(
    oauth2=OAuth2Auth(
        client_id=os.getenv("WORKDAY_CLIENT_ID"),
        client_secret=os.getenv("WORKDAY_CLIENT_SECRET"),
        auth_uri=os.getenv("WORKDAY_AUTHORIZATION_URL"),
        token_uri=os.getenv("WORKDAY_TOKEN_URL"),
    )
)
```

### Step 4: Create Authenticated Tools

```python
import requests
from typing import Dict, List, Optional
from google.adk.tools import Tool
from google.adk.tools.tool_context import ToolContext

class WorkdayPurchaseOrderTool:
    """Tool for accessing Workday Purchase Order API with OAuth2"""

    def __init__(self, base_url: str, auth_scheme: Oauth2, auth_credential: AuthCredential):
        self.base_url = base_url
        self.auth_scheme = auth_scheme
        self.auth_credential = auth_credential

    def _get_access_token(self, tool_context: ToolContext) -> str:
        """
        Retrieve valid access token from ADK context.
        ADK automatically handles token refresh.
        """
        # Check if we have a cached token
        cached_token = tool_context.state.get("workday_access_token")
        if cached_token:
            return cached_token

        # Request authentication if needed
        auth_response = tool_context.get_auth_response()
        if auth_response and auth_response.oauth2:
            access_token = auth_response.oauth2.access_token
            # Cache the token
            tool_context.state["workday_access_token"] = access_token
            return access_token

        # Request credential from user
        tool_context.request_credential(
            auth_scheme=self.auth_scheme,
            credential=self.auth_credential
        )

        # This will trigger ADK's OAuth flow
        raise Exception("Authentication required. Please complete OAuth flow.")

    def get_purchase_orders(
        self,
        tool_context: ToolContext,
        limit: int = 10,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve purchase orders from Workday.

        Args:
            tool_context: ADK tool context for authentication
            limit: Maximum number of results
            offset: Pagination offset
            search: Optional search criteria

        Returns:
            List of purchase order dictionaries
        """
        access_token = self._get_access_token(tool_context)

        url = f"{self.base_url}/resourceManagement/v1/purchaseOrders"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        params = {
            "limit": limit,
            "offset": offset
        }
        if search:
            params["search"] = search

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json().get("data", [])

    def get_purchase_order_by_id(
        self,
        tool_context: ToolContext,
        purchase_order_id: str
    ) -> Dict:
        """
        Retrieve a specific purchase order by ID.

        Args:
            tool_context: ADK tool context for authentication
            purchase_order_id: The purchase order ID

        Returns:
            Purchase order dictionary
        """
        access_token = self._get_access_token(tool_context)

        url = f"{self.base_url}/resourceManagement/v1/purchaseOrders/{purchase_order_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()
```

### Step 5: Create ADK Agent with Authenticated Tools

```python
from google.adk.agents import Agent

# Initialize Workday tool
workday_tool = WorkdayPurchaseOrderTool(
    base_url=os.getenv("WORKDAY_API_BASE_URL"),
    auth_scheme=workday_oauth_scheme,
    auth_credential=workday_auth_credential
)

# Create ADK agent
workday_agent = Agent(
    name="workday_purchase_order_agent",
    model="gemini-2.0-flash-exp",
    instruction="""
    You are a Workday Purchase Order assistant. You help users:
    - Search and retrieve purchase orders
    - Get details about specific purchase orders
    - Answer questions about purchase order status and details

    Always use the provided tools to access Workday data.
    """,
    description="An agent that can access Workday Purchase Orders via OAuth2-authenticated API",
    tools=[
        Tool.from_function(
            workday_tool.get_purchase_orders,
            name="get_purchase_orders",
            description="Retrieve a list of purchase orders from Workday"
        ),
        Tool.from_function(
            workday_tool.get_purchase_order_by_id,
            name="get_purchase_order_by_id",
            description="Get detailed information about a specific purchase order"
        )
    ]
)
```

---

## Complete Code Example

Here's a complete implementation:

```python
#!/usr/bin/env python3
"""
Workday Purchase Order ADK Agent with OAuth2 Authentication
"""

import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.tools import Tool
from google.adk.tools.auth_schemes import Oauth2
from google.adk.auth.auth_credential import AuthCredential, OAuth2Auth
from google.adk.tools.tool_context import ToolContext

# Load environment variables
load_dotenv()


class WorkdayPurchaseOrderTool:
    """OAuth2-authenticated tool for Workday Purchase Order API"""

    def __init__(self, base_url: str, auth_scheme: Oauth2, auth_credential: AuthCredential):
        self.base_url = base_url
        self.auth_scheme = auth_scheme
        self.auth_credential = auth_credential

    def _get_access_token(self, tool_context: ToolContext) -> str:
        """Get valid access token, handling OAuth flow if needed"""
        # Check cache
        cached_token = tool_context.state.get("workday_access_token")
        if cached_token:
            return cached_token

        # Get from auth response
        auth_response = tool_context.get_auth_response()
        if auth_response and auth_response.oauth2:
            access_token = auth_response.oauth2.access_token
            tool_context.state["workday_access_token"] = access_token
            return access_token

        # Request authentication
        tool_context.request_credential(
            auth_scheme=self.auth_scheme,
            credential=self.auth_credential
        )
        raise Exception("Authentication required")

    def get_purchase_orders(
        self,
        tool_context: ToolContext,
        limit: int = 10,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[Dict]:
        """Retrieve purchase orders from Workday"""
        access_token = self._get_access_token(tool_context)

        url = f"{self.base_url}/resourceManagement/v1/purchaseOrders"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {"limit": limit, "offset": offset}
        if search:
            params["search"] = search

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

    def get_purchase_order_by_id(
        self,
        tool_context: ToolContext,
        purchase_order_id: str
    ) -> Dict:
        """Get specific purchase order by ID"""
        access_token = self._get_access_token(tool_context)

        url = f"{self.base_url}/resourceManagement/v1/purchaseOrders/{purchase_order_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


def create_workday_agent() -> Agent:
    """Create and configure the Workday Purchase Order agent"""

    # Configure OAuth2 scheme
    oauth_scheme = Oauth2(
        authorization_url=os.getenv("WORKDAY_AUTHORIZATION_URL"),
        token_url=os.getenv("WORKDAY_TOKEN_URL"),
        scopes=[os.getenv("WORKDAY_SCOPES", "system")],
    )

    # Configure auth credential
    auth_credential = AuthCredential(
        oauth2=OAuth2Auth(
            client_id=os.getenv("WORKDAY_CLIENT_ID"),
            client_secret=os.getenv("WORKDAY_CLIENT_SECRET"),
            auth_uri=os.getenv("WORKDAY_AUTHORIZATION_URL"),
            token_uri=os.getenv("WORKDAY_TOKEN_URL"),
        )
    )

    # Initialize tool
    workday_tool = WorkdayPurchaseOrderTool(
        base_url=os.getenv("WORKDAY_API_BASE_URL"),
        auth_scheme=oauth_scheme,
        auth_credential=auth_credential
    )

    # Create agent
    agent = Agent(
        name="workday_purchase_order_agent",
        model="gemini-2.0-flash-exp",
        instruction="""
        You are a Workday Purchase Order assistant. You help users:
        - Search and retrieve purchase orders
        - Get details about specific purchase orders
        - Answer questions about purchase order status and details

        Always use the provided tools to access Workday data.
        Be concise and format data in a readable way.
        """,
        description="Workday Purchase Order Agent with OAuth2 authentication",
        tools=[
            Tool.from_function(
                workday_tool.get_purchase_orders,
                name="get_purchase_orders",
                description="Retrieve a list of purchase orders from Workday"
            ),
            Tool.from_function(
                workday_tool.get_purchase_order_by_id,
                name="get_purchase_order_by_id",
                description="Get detailed information about a specific purchase order"
            )
        ]
    )

    return agent


def main():
    """Main entry point"""
    # Authenticate with Google Cloud
    os.system("gcloud auth application-default login")

    # Create agent
    agent = create_workday_agent()

    # Start interactive session
    print("Workday Purchase Order Agent started!")
    print("Example queries:")
    print("  - 'Show me the latest 5 purchase orders'")
    print("  - 'Get details for purchase order PO-00001'")
    print("  - 'Search for purchase orders from Supplier Inc'")
    print()

    # Run agent (this will trigger OAuth flow on first use)
    # For local testing, use: adk web
    # For production deployment, use Agent Engine

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        try:
            response = agent.run(user_input)
            print(f"Agent: {response}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
```

---

## Testing and Deployment

### Local Development with ADK Web UI

1. Start the ADK development server:

```bash
adk web
```

2. Navigate to `http://localhost:8000`

3. The UI will guide you through the OAuth flow when you first use an authenticated tool

4. Test your agent with sample queries:
   - "Show me the latest 10 purchase orders"
   - "Get details for purchase order PO-00001"

### OAuth Flow in Development

When you call an authenticated tool for the first time:

1. ADK detects missing credentials
2. User is presented with authorization URL
3. User authorizes in Workday
4. Authorization code is exchanged for tokens
5. ADK caches the access token
6. Tool executes with valid token

### Production Deployment

#### Deploy to Vertex AI Agent Engine

1. **Package your agent**:

```bash
# Ensure your code is production-ready
# Add all dependencies to requirements.txt
```

2. **Create Agent Engine configuration**:

```python
from google.cloud import aiplatform

aiplatform.init(
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION")
)

# Deploy agent to Agent Engine
# (Follow ADK deployment documentation)
```

3. **Configure OAuth in Production**:

- Store credentials in Google Secret Manager
- Configure OAuth redirect URIs for your production domain
- Set up proper scopes and permissions

4. **Monitor and maintain**:

```bash
# View agent logs
gcloud logging read "resource.type=adk_agent"

# Monitor token refresh
# ADK handles this automatically
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Fails

**Problem**: `401 Unauthorized` when calling Workday API

**Solutions**:
- Verify Client ID and Client Secret are correct
- Check that OAuth redirect URI matches exactly
- Ensure required scopes are configured in Workday
- Verify token hasn't expired (ADK should handle this)

#### 2. Token Refresh Issues

**Problem**: Access token expires and isn't refreshed

**Solutions**:
- Check that `refresh_token` is included in OAuth response
- Verify ADK version supports automatic refresh
- Ensure OAuth2 configuration includes token endpoint

#### 3. Workday API Returns 403 Forbidden

**Problem**: Authenticated but getting permission errors

**Solutions**:
- Verify API client has correct functional area scopes
- Check user/service account has Resource Management permissions
- Confirm API is enabled in your Workday tenant

#### 4. Local Development OAuth Flow Doesn't Complete

**Problem**: OAuth callback doesn't work locally

**Solutions**:
- Ensure redirect URI in Workday matches `http://localhost:8000/dev-ui`
- Check firewall/network settings
- Try using `adk web --port 8080` if port 8000 is occupied

#### 5. API Returns Empty Results

**Problem**: API call succeeds but returns no data

**Solutions**:
- Check search criteria and filters
- Verify data exists in Workday for the query
- Review API version compatibility
- Check pagination parameters

### Debug Mode

Enable verbose logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("workday_agent")

# Add debug statements in your tool methods
logger.debug(f"Requesting access token from context")
logger.debug(f"API URL: {url}")
logger.debug(f"Response: {response.json()}")
```

### Testing OAuth Flow

Test OAuth manually:

```bash
# Step 1: Get authorization URL
echo "Visit this URL:"
echo "https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:8000/dev-ui&scope=system"

# Step 2: After authorization, test token endpoint
curl -X POST https://wd2-impl-services1.workday.com/ccx/oauth2/{tenant}/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code={AUTHORIZATION_CODE}" \
  -d "client_id={CLIENT_ID}" \
  -d "client_secret={CLIENT_SECRET}" \
  -d "redirect_uri=http://localhost:8000/dev-ui"
```

---

## Best Practices

### Security

1. **Never hardcode credentials** - Use environment variables or secret management
2. **Use HTTPS in production** - Ensure all OAuth redirects use HTTPS
3. **Implement proper error handling** - Don't expose sensitive details in errors
4. **Rotate credentials regularly** - Follow your organization's security policies
5. **Use least-privilege scopes** - Only request necessary permissions

### Performance

1. **Cache tokens appropriately** - Use `tool_context.state` for session caching
2. **Implement pagination** - Don't fetch all records at once
3. **Add retry logic** - Handle transient API failures gracefully
4. **Monitor API rate limits** - Respect Workday's rate limiting

### Code Organization

1. **Separate concerns** - Keep OAuth logic separate from business logic
2. **Use type hints** - Make code more maintainable
3. **Write comprehensive docstrings** - Document OAuth requirements
4. **Add unit tests** - Mock OAuth flow for testing
5. **Version your API calls** - Use explicit API versions

---

## Additional Resources

### Google ADK Documentation

- [ADK Authentication Guide](https://google.github.io/adk-docs/tools/authentication/)
- [ADK Python SDK](https://github.com/google/adk-python)
- [ADK Samples](https://github.com/google/adk-samples)

### Workday API Documentation

- [Workday Community](https://community.workday.com) - Official API docs (requires login)
- [Workday REST API Directory](https://community.workday.com/sites/default/files/file-hosting/restapi/index.html)
- [Resource Management API](https://community.workday.com/api) - SOAP and REST references

### OAuth2 Specifications

- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [OAuth 2.0 Best Practices](https://tools.ietf.org/html/draft-ietf-oauth-security-topics)

---

## Conclusion

This guide provides a comprehensive foundation for integrating Workday's Purchase Order API with Google ADK using OAuth2 authentication. The ADK framework handles much of the OAuth complexity, allowing you to focus on building powerful agent capabilities.

Key takeaways:

1. **ADK simplifies OAuth** - Token management is automatic
2. **Workday requires proper setup** - Configure API clients correctly
3. **Use environment variables** - Keep credentials secure
4. **Test locally first** - Use `adk web` for development
5. **Monitor in production** - Track token refresh and API usage

With this integration, you can build sophisticated AI agents that securely interact with Workday's enterprise systems on behalf of users.
