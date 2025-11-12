# Workday Procurement API

Enterprise-grade FastAPI application for interacting with Workday Purchase Order procurement endpoints via SOAP API.

## Features

- **Enterprise-Grade Authentication**: WS-Security with UsernameToken support
- **Type Safety**: Full pydantic models for request/response validation
- **Modern Python**: Python 3.10+ with type hints throughout
- **SOAP Integration**: Zeep-based SOAP client with retry logic
- **Structured Logging**: JSON-formatted logs for easy parsing
- **FastAPI**: High-performance async API with automatic OpenAPI documentation
- **Configuration Management**: pydantic-settings for environment variable management
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes

## Architecture

```
workday_procurement_api/
├── config/          # Configuration management (pydantic-settings)
├── auth/            # WS-Security authentication
├── soap/            # SOAP client wrapper (zeep)
├── models/          # Pydantic data models
├── api/             # FastAPI routes and dependencies
├── utils/           # Utilities (exceptions, logging)
└── examples/        # Usage examples
```

## Requirements

- Python 3.10+
- Workday tenant with Integration Security Group (ISG) user
- Access to Workday Resource Management WSDL

## Installation

1. **Clone the repository**:
   ```bash
   cd workday_procurement_api
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Workday credentials
   ```

## Configuration

### Required Environment Variables

```bash
# Workday ISG User (format: username@tenant)
WORKDAY_USERNAME=integration_user@acme_implementation
WORKDAY_PASSWORD=your_secure_password
WORKDAY_TENANT_NAME=acme_implementation

# Workday Instance URL
WORKDAY_API_BASE_URL=https://wd2-impl-services1.workday.com

# API Version
WORKDAY_API_API_VERSION=v45.1
```

See `.env.example` for all available configuration options.

## Usage

### Starting the Server

```bash
# Development mode
python -m workday_procurement_api.main

# Production mode with uvicorn
uvicorn workday_procurement_api.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status.

### List Purchase Orders

```bash
GET /api/v1/purchase-orders?page=1&page_size=50
```

Query parameters:
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 50, max: 1000)
- `supplier_id` (string, optional): Filter by supplier ID
- `company_id` (string, optional): Filter by company ID
- `status` (string, optional): Filter by status

**Example Response**:
```json
{
  "purchase_orders": [
    {
      "purchase_order_id": "PO-001",
      "purchase_order_number": "PO-2024-001",
      "supplier": {
        "id": "SUP-123",
        "descriptor": "Acme Supplies Inc."
      },
      "company": {
        "id": "COM-456",
        "descriptor": "Acme Corporation"
      },
      "submit_date": "2024-01-15",
      "total_amount": "15000.00",
      "currency": {
        "id": "USD",
        "descriptor": "US Dollar"
      },
      "status": {
        "status": "Approved",
        "status_descriptor": "Purchase Order Approved"
      },
      "lines": [
        {
          "line_number": 1,
          "item_description": "Office Supplies",
          "quantity": "100.00",
          "unit_cost": "150.00",
          "extended_amount": "15000.00"
        }
      ]
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50
}
```

### Get Purchase Order by ID

```bash
GET /api/v1/purchase-orders/{purchase_order_id}
```

Path parameters:
- `purchase_order_id` (string): Purchase order ID

**Example**:
```bash
curl http://localhost:8000/api/v1/purchase-orders/PO-001
```

## Code Examples

### Direct SOAP Client Usage

```python
from workday_procurement_api.soap.client import create_soap_client
from workday_procurement_api.config.settings import WorkdayAuthConfig, WorkdayAPIConfig

# Create client
auth_config = WorkdayAuthConfig()
api_config = WorkdayAPIConfig()
api_config.set_auth_config(auth_config)

client = create_soap_client(api_config, auth_config)

# Fetch purchase orders
purchase_orders = client.get_purchase_orders()
print(f"Found {len(purchase_orders)} purchase orders")

# Fetch specific purchase order
po = client.get_purchase_order_by_id("PO-001")
if po:
    print(f"Purchase Order: {po}")
```

### Using Configuration

```python
from workday_procurement_api.config.settings import get_settings

settings = get_settings()
print(f"Tenant: {settings.auth.tenant_name}")
print(f"API Version: {settings.api.api_version}")
print(f"Debug Mode: {settings.app.debug}")
```

## Development

### Running Tests

```bash
pytest tests/ -v --cov=workday_procurement_api
```

### Code Formatting

```bash
black workday_procurement_api/
```

### Linting

```bash
flake8 workday_procurement_api/
mypy workday_procurement_api/
```

## Error Handling

The API provides structured error responses:

```json
{
  "error": "Error category",
  "message": "Detailed error message",
  "error_code": "UNIQUE_ERROR_CODE"
}
```

Common HTTP status codes:
- `200`: Success
- `404`: Purchase order not found
- `422`: Validation error
- `500`: Internal server error
- `502`: Workday service error

## Logging

The application uses structured JSON logging:

```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "level": "INFO",
  "logger": "workday_procurement_api.soap.client",
  "message": "Successfully fetched purchase orders",
  "module": "client",
  "function": "get_purchase_orders",
  "line": 123,
  "extra_fields": {
    "count": 10
  }
}
```

Configure logging via environment variables:
- `APP_LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `APP_LOG_FORMAT`: json or text

## Security Considerations

1. **Credentials**: Never commit `.env` file or credentials to version control
2. **HTTPS**: Always use HTTPS in production
3. **API Keys**: Consider adding API key authentication for the FastAPI endpoints
4. **Rate Limiting**: Implement rate limiting for production deployments
5. **CORS**: Configure CORS appropriately for your environment

## Production Deployment

### Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY workday_procurement_api/ ./workday_procurement_api/

EXPOSE 8000

CMD ["uvicorn", "workday_procurement_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment-Specific Configuration

Create environment-specific `.env` files:
- `.env.development`
- `.env.staging`
- `.env.production`

### Monitoring

Integrate with monitoring tools:
- Prometheus metrics
- ELK stack for log aggregation
- APM tools (New Relic, Datadog)

## Troubleshooting

### Connection Issues

```
SOAPClientException: Failed to initialize SOAP client
```

**Solution**: Verify `WORKDAY_API_BASE_URL` and network connectivity.

### Authentication Errors

```
AuthenticationException: Authentication failed
```

**Solution**: Verify ISG user credentials and username format (`username@tenant`).

### SOAP Fault Errors

```
WorkdayServiceException: SOAP Fault
```

**Solution**: Check Workday service logs and verify API permissions.

## Contributing

1. Follow Google Pydocstring style for documentation
2. Maintain PEP8 compliance
3. Add type hints to all functions
4. Write tests for new features
5. Update documentation

## License

MIT License

## Support

For issues and questions:
- Check Workday Community: https://community.workday.com
- Review SOAP API Reference: https://community.workday.com/api

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [Zeep](https://docs.python-zeep.org/)
