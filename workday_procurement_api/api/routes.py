"""FastAPI routes for Workday Procurement API.

This module defines all API endpoints for purchase order operations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from workday_procurement_api.api.dependencies import get_soap_client
from workday_procurement_api.models.purchase_order import (
    PurchaseOrder,
    PurchaseOrderFilters,
    PurchaseOrderListResponse,
    parse_workday_purchase_order,
)
from workday_procurement_api.soap.client import WorkdaySOAPClient
from workday_procurement_api.utils.exceptions import (
    PurchaseOrderNotFoundException,
    SOAPClientException,
    ValidationException,
    WorkdayServiceException,
)
from workday_procurement_api.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/purchase-orders",
    tags=["Purchase Orders"],
)


@router.get(
    "",
    response_model=PurchaseOrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List purchase orders",
    description="Retrieve a list of purchase orders with optional filtering.",
)
async def list_purchase_orders(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=1000, description="Items per page"),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier ID"),
    company_id: Optional[str] = Query(None, description="Filter by company ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    soap_client: WorkdaySOAPClient = Depends(get_soap_client),
) -> PurchaseOrderListResponse:
    """List purchase orders with optional filtering.

    Args:
        page: Page number for pagination.
        page_size: Number of items per page.
        supplier_id: Optional supplier ID filter.
        company_id: Optional company ID filter.
        status: Optional status filter.
        soap_client: Injected SOAP client.

    Returns:
        List of purchase orders with pagination info.

    Raises:
        HTTPException: If request fails.
    """
    try:
        logger.info(
            "Listing purchase orders",
            extra={
                "extra_fields": {
                    "page": page,
                    "page_size": page_size,
                    "supplier_id": supplier_id,
                    "company_id": company_id,
                    "status": status,
                }
            },
        )

        # Build request criteria
        request_criteria = {}
        if supplier_id:
            request_criteria["Supplier_Reference"] = {
                "ID": {"type": "Supplier_ID", "_value_1": supplier_id}
            }
        if company_id:
            request_criteria["Company_Reference"] = {
                "ID": {"type": "Company_ID", "_value_1": company_id}
            }
        if status:
            request_criteria["Status"] = status

        # Fetch from Workday
        raw_purchase_orders = soap_client.get_purchase_orders(
            request_criteria=request_criteria if request_criteria else None,
        )

        # Parse purchase orders
        purchase_orders: List[PurchaseOrder] = []
        for raw_po in raw_purchase_orders:
            try:
                po = parse_workday_purchase_order(raw_po)
                purchase_orders.append(po)
            except ValidationException as e:
                logger.warning(f"Failed to parse purchase order: {e}")
                continue

        # Apply pagination (in production, push this to Workday API)
        total_count = len(purchase_orders)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_pos = purchase_orders[start_idx:end_idx]

        logger.info(
            f"Successfully retrieved {len(paginated_pos)} purchase orders",
            extra={"extra_fields": {"total_count": total_count}},
        )

        return PurchaseOrderListResponse(
            purchase_orders=paginated_pos,
            total_count=total_count,
            page=page,
            page_size=page_size,
        )

    except WorkdayServiceException as e:
        logger.error(f"Workday service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Workday service error",
                "message": str(e),
                "error_code": e.error_code,
            },
        )
    except SOAPClientException as e:
        logger.error(f"SOAP client error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal service error",
                "message": str(e),
                "error_code": e.error_code,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            },
        )


@router.get(
    "/{purchase_order_id}",
    response_model=PurchaseOrder,
    status_code=status.HTTP_200_OK,
    summary="Get purchase order by ID",
    description="Retrieve a specific purchase order by its ID.",
)
async def get_purchase_order(
    purchase_order_id: str,
    soap_client: WorkdaySOAPClient = Depends(get_soap_client),
) -> PurchaseOrder:
    """Get a specific purchase order by ID.

    Args:
        purchase_order_id: Purchase order ID.
        soap_client: Injected SOAP client.

    Returns:
        Purchase order details.

    Raises:
        HTTPException: If purchase order not found or request fails.
    """
    try:
        logger.info(
            f"Fetching purchase order: {purchase_order_id}",
            extra={"extra_fields": {"po_id": purchase_order_id}},
        )

        # Fetch from Workday
        raw_po = soap_client.get_purchase_order_by_id(purchase_order_id)

        if raw_po is None:
            logger.warning(f"Purchase order not found: {purchase_order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Purchase order not found",
                    "message": f"Purchase order {purchase_order_id} does not exist",
                    "error_code": "PO_NOT_FOUND",
                },
            )

        # Parse purchase order
        purchase_order = parse_workday_purchase_order(raw_po)

        logger.info(f"Successfully retrieved purchase order: {purchase_order_id}")

        return purchase_order

    except HTTPException:
        raise
    except ValidationException as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Data validation error",
                "message": str(e),
                "error_code": e.error_code,
            },
        )
    except WorkdayServiceException as e:
        logger.error(f"Workday service error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Workday service error",
                "message": str(e),
                "error_code": e.error_code,
            },
        )
    except SOAPClientException as e:
        logger.error(f"SOAP client error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal service error",
                "message": str(e),
                "error_code": e.error_code,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            },
        )
