"""Usage examples for Workday Procurement API.

This module demonstrates how to use the Workday Procurement API
in various scenarios.
"""

import asyncio
from datetime import date
from decimal import Decimal

from workday_procurement_api.config.settings import (
    WorkdayAPIConfig,
    WorkdayAuthConfig,
    get_settings,
)
from workday_procurement_api.models.purchase_order import (
    PurchaseOrderFilters,
    parse_workday_purchase_order,
)
from workday_procurement_api.soap.client import create_soap_client
from workday_procurement_api.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def example_basic_usage():
    """Example: Basic usage of SOAP client.

    This example demonstrates how to create a SOAP client and fetch
    purchase orders using default configuration from environment variables.
    """
    print("=== Example 1: Basic Usage ===\n")

    # Load settings from environment
    settings = get_settings()
    setup_logging(settings.app)

    # Create SOAP client
    client = create_soap_client(
        api_config=settings.api,
        auth_config=settings.auth,
    )

    # Fetch all purchase orders
    logger.info("Fetching all purchase orders...")
    purchase_orders = client.get_purchase_orders()

    print(f"Found {len(purchase_orders)} purchase orders")

    # Display first purchase order
    if purchase_orders:
        po = parse_workday_purchase_order(purchase_orders[0])
        print(f"\nFirst Purchase Order:")
        print(f"  ID: {po.purchase_order_id}")
        print(f"  Number: {po.purchase_order_number}")
        print(f"  Supplier: {po.supplier.descriptor}")
        print(f"  Total: {po.currency.id} {po.total_amount}")
        print(f"  Status: {po.status.status}")
        print(f"  Lines: {len(po.lines)}")


def example_fetch_by_id():
    """Example: Fetch specific purchase order by ID.

    This example demonstrates how to fetch a specific purchase order
    using its ID.
    """
    print("\n=== Example 2: Fetch by ID ===\n")

    # Create client
    settings = get_settings()
    client = create_soap_client(
        api_config=settings.api,
        auth_config=settings.auth,
    )

    # Fetch specific purchase order
    po_id = "PO-001"  # Replace with actual PO ID
    logger.info(f"Fetching purchase order: {po_id}")

    raw_po = client.get_purchase_order_by_id(po_id)

    if raw_po:
        po = parse_workday_purchase_order(raw_po)
        print(f"Purchase Order Found:")
        print(f"  ID: {po.purchase_order_id}")
        print(f"  Number: {po.purchase_order_number}")
        print(f"  Total: {po.currency.id} {po.total_amount}")

        # Display line items
        print(f"\n  Line Items:")
        for line in po.lines:
            print(f"    {line.line_number}. {line.item_description}")
            print(f"       Qty: {line.quantity} @ {line.unit_cost} = {line.extended_amount}")
    else:
        print(f"Purchase order {po_id} not found")


def example_with_filters():
    """Example: Fetch purchase orders with filters.

    This example demonstrates how to filter purchase orders by
    supplier, company, and other criteria.
    """
    print("\n=== Example 3: Using Filters ===\n")

    # Create client
    settings = get_settings()
    client = create_soap_client(
        api_config=settings.api,
        auth_config=settings.auth,
    )

    # Build request criteria
    request_criteria = {
        "Supplier_Reference": {
            "ID": {"type": "Supplier_ID", "_value_1": "SUP-123"}
        },
        "Submit_Date_Range": {
            "From": "2024-01-01",
            "To": "2024-12-31",
        },
    }

    logger.info("Fetching purchase orders with filters...")
    purchase_orders = client.get_purchase_orders(request_criteria=request_criteria)

    print(f"Found {len(purchase_orders)} purchase orders matching criteria")

    # Calculate total value
    total_value = Decimal("0")
    for raw_po in purchase_orders:
        po = parse_workday_purchase_order(raw_po)
        total_value += po.total_amount
        print(f"  - {po.purchase_order_number}: {po.currency.id} {po.total_amount}")

    print(f"\nTotal Value: {total_value}")


def example_custom_configuration():
    """Example: Using custom configuration.

    This example demonstrates how to create a client with custom
    configuration instead of using environment variables.
    """
    print("\n=== Example 4: Custom Configuration ===\n")

    # Create custom auth config
    auth_config = WorkdayAuthConfig(
        username="integration_user@acme_implementation",
        password="your_password",
        tenant_name="acme_implementation",
        auth_type="password",
    )

    # Create custom API config
    api_config = WorkdayAPIConfig(
        base_url="https://wd2-impl-services1.workday.com",
        api_version="v45.1",
        timeout=60,
        max_retries=5,
    )

    # Link configs
    api_config.set_auth_config(auth_config)

    # Create client
    client = create_soap_client(api_config=api_config, auth_config=auth_config)

    print("Client created with custom configuration")
    print(f"  Tenant: {auth_config.tenant_name}")
    print(f"  API Version: {api_config.api_version}")
    print(f"  Timeout: {api_config.timeout}s")
    print(f"  Max Retries: {api_config.max_retries}")


def example_data_validation():
    """Example: Pydantic model validation.

    This example demonstrates how pydantic models validate data
    and enforce business rules.
    """
    print("\n=== Example 5: Data Validation ===\n")

    from workday_procurement_api.models.purchase_order import (
        PurchaseOrder,
        PurchaseOrderLine,
        PurchaseOrderStatus,
        SupplierReference,
        CompanyReference,
        CurrencyReference,
    )

    # Create a purchase order programmatically
    try:
        po = PurchaseOrder(
            purchase_order_id="PO-TEST-001",
            purchase_order_number="TEST-2024-001",
            supplier=SupplierReference(id="SUP-123", descriptor="Test Supplier"),
            company=CompanyReference(id="COM-456", descriptor="Test Company"),
            submit_date=date.today(),
            total_amount=Decimal("1500.00"),
            currency=CurrencyReference(id="USD", descriptor="US Dollar"),
            status=PurchaseOrderStatus(status="Draft", status_descriptor="Draft PO"),
            lines=[
                PurchaseOrderLine(
                    line_number=1,
                    item_description="Test Item",
                    quantity=Decimal("10"),
                    unit_cost=Decimal("150.00"),
                    extended_amount=Decimal("1500.00"),
                )
            ],
        )

        print("Purchase Order created successfully:")
        print(f"  ID: {po.purchase_order_id}")
        print(f"  Number: {po.purchase_order_number}")
        print(f"  Total: {po.currency.id} {po.total_amount}")
        print(f"  Fully Received: {po.is_fully_received}")
        print(f"  Fully Invoiced: {po.is_fully_invoiced}")

    except Exception as e:
        print(f"Validation error: {e}")


def example_error_handling():
    """Example: Error handling.

    This example demonstrates how to handle various errors that
    may occur when interacting with Workday API.
    """
    print("\n=== Example 6: Error Handling ===\n")

    from workday_procurement_api.utils.exceptions import (
        AuthenticationException,
        SOAPClientException,
        WorkdayServiceException,
    )

    try:
        # Create client
        settings = get_settings()
        client = create_soap_client(
            api_config=settings.api,
            auth_config=settings.auth,
        )

        # Try to fetch purchase orders
        purchase_orders = client.get_purchase_orders()
        print(f"Successfully fetched {len(purchase_orders)} purchase orders")

    except AuthenticationException as e:
        print(f"Authentication failed: {e}")
        print(f"Error code: {e.error_code}")
        print("Please check your credentials")

    except WorkdayServiceException as e:
        print(f"Workday service error: {e}")
        print(f"Fault code: {e.fault_code}")
        print(f"Fault string: {e.fault_string}")

    except SOAPClientException as e:
        print(f"SOAP client error: {e}")
        print(f"Error code: {e.error_code}")

    except Exception as e:
        print(f"Unexpected error: {e}")


async def example_async_usage():
    """Example: Async usage pattern.

    This example demonstrates how to use the API in an async context,
    which is useful for FastAPI endpoints.
    """
    print("\n=== Example 7: Async Usage ===\n")

    # Note: The current SOAP client is synchronous
    # In production, consider wrapping in asyncio.to_thread for true async

    def fetch_purchase_orders():
        settings = get_settings()
        client = create_soap_client(
            api_config=settings.api,
            auth_config=settings.auth,
        )
        return client.get_purchase_orders()

    # Run in thread pool
    purchase_orders = await asyncio.to_thread(fetch_purchase_orders)

    print(f"Async fetch completed: {len(purchase_orders)} purchase orders")


def main():
    """Run all examples.

    Execute all example functions to demonstrate the API capabilities.
    """
    print("=" * 70)
    print("WORKDAY PROCUREMENT API - USAGE EXAMPLES")
    print("=" * 70)

    # Note: These examples require valid Workday credentials
    # Update .env file before running

    try:
        # Example 1: Basic usage
        # example_basic_usage()

        # Example 2: Fetch by ID
        # example_fetch_by_id()

        # Example 3: Using filters
        # example_with_filters()

        # Example 4: Custom configuration
        example_custom_configuration()

        # Example 5: Data validation
        example_data_validation()

        # Example 6: Error handling
        # example_error_handling()

        # Example 7: Async usage
        # asyncio.run(example_async_usage())

        print("\n" + "=" * 70)
        print("Examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\nError running examples: {e}")
        logger.error("Example execution failed", exc_info=True)


if __name__ == "__main__":
    main()
