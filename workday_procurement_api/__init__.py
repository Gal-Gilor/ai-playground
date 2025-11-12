"""Workday Procurement API.

Enterprise-grade FastAPI application for interacting with Workday
Purchase Order procurement endpoints via SOAP API.

This package provides:
- FastAPI REST endpoints for purchase order operations
- SOAP client wrapper for Workday Resource Management API
- Type-safe pydantic models for data validation
- Enterprise-grade authentication (WS-Security)
- Comprehensive error handling and logging
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__license__ = "MIT"

from workday_procurement_api.config.settings import get_settings
from workday_procurement_api.soap.client import create_soap_client
from workday_procurement_api.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderFilters,
)

__all__ = [
    "get_settings",
    "create_soap_client",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderFilters",
]
