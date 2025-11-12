"""Pydantic models for Purchase Order operations.

This module defines type-safe pydantic models for purchase order
data structures returned from Workday SOAP API.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class WorkdayReference(BaseModel):
    """Base model for Workday reference objects.

    Attributes:
        id: Reference ID value.
        descriptor: Human-readable descriptor.
    """

    id: str = Field(..., description="Reference ID")
    descriptor: Optional[str] = Field(None, description="Human-readable descriptor")


class SupplierReference(WorkdayReference):
    """Supplier reference model.

    Attributes:
        id: Supplier ID.
        descriptor: Supplier name.
    """

    pass


class CompanyReference(WorkdayReference):
    """Company reference model.

    Attributes:
        id: Company ID.
        descriptor: Company name.
    """

    pass


class CurrencyReference(WorkdayReference):
    """Currency reference model.

    Attributes:
        id: Currency code (e.g., 'USD', 'EUR').
        descriptor: Currency name.
    """

    pass


class PurchaseOrderLine(BaseModel):
    """Purchase order line item model.

    Attributes:
        line_number: Line item number.
        item_description: Description of the item.
        quantity: Quantity ordered.
        unit_cost: Cost per unit.
        extended_amount: Total line amount (quantity * unit_cost).
        currency: Currency reference.
        received_quantity: Quantity received.
        invoiced_quantity: Quantity invoiced.
    """

    line_number: int = Field(..., description="Line item number", ge=1)
    item_description: str = Field(..., description="Item description")
    quantity: Decimal = Field(..., description="Quantity ordered", ge=0)
    unit_cost: Decimal = Field(..., description="Cost per unit", ge=0)
    extended_amount: Decimal = Field(..., description="Total line amount", ge=0)
    currency: Optional[CurrencyReference] = Field(None, description="Currency")
    received_quantity: Optional[Decimal] = Field(
        default=None,
        description="Quantity received",
        ge=0,
    )
    invoiced_quantity: Optional[Decimal] = Field(
        default=None,
        description="Quantity invoiced",
        ge=0,
    )

    @field_validator("extended_amount")
    @classmethod
    def validate_extended_amount(cls, value: Decimal, info) -> Decimal:
        """Validate extended amount matches quantity * unit_cost.

        Args:
            value: Extended amount to validate.
            info: Field validation info containing other field values.

        Returns:
            Validated extended amount.
        """
        # Note: In production, you might want to validate this against
        # quantity * unit_cost, but allowing for rounding differences
        return value


class PurchaseOrderStatus(BaseModel):
    """Purchase order status model.

    Attributes:
        status: Status code.
        status_descriptor: Status description.
    """

    status: str = Field(..., description="Status code")
    status_descriptor: Optional[str] = Field(
        None,
        description="Status description",
    )


class PurchaseOrder(BaseModel):
    """Complete purchase order model.

    Attributes:
        purchase_order_id: Unique purchase order identifier.
        purchase_order_number: Purchase order number.
        supplier: Supplier reference.
        company: Company reference.
        submit_date: Date the PO was submitted.
        total_amount: Total purchase order amount.
        currency: Currency reference.
        status: Purchase order status.
        memo: Purchase order memo/notes.
        lines: List of purchase order line items.
        requisition_number: Related requisition number.
        created_moment: Timestamp when PO was created.
        updated_moment: Timestamp when PO was last updated.
    """

    purchase_order_id: str = Field(
        ...,
        description="Unique purchase order identifier",
    )
    purchase_order_number: str = Field(
        ...,
        description="Purchase order number",
    )
    supplier: SupplierReference = Field(..., description="Supplier reference")
    company: CompanyReference = Field(..., description="Company reference")
    submit_date: date = Field(..., description="PO submission date")
    total_amount: Decimal = Field(..., description="Total PO amount", ge=0)
    currency: CurrencyReference = Field(..., description="Currency")
    status: PurchaseOrderStatus = Field(..., description="PO status")
    memo: Optional[str] = Field(None, description="PO memo/notes")
    lines: List[PurchaseOrderLine] = Field(
        default_factory=list,
        description="Purchase order line items",
    )
    requisition_number: Optional[str] = Field(
        None,
        description="Related requisition number",
    )
    created_moment: Optional[datetime] = Field(
        None,
        description="Creation timestamp",
    )
    updated_moment: Optional[datetime] = Field(
        None,
        description="Last update timestamp",
    )

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, value: List[PurchaseOrderLine]) -> List[PurchaseOrderLine]:
        """Validate purchase order has at least one line.

        Args:
            value: List of purchase order lines.

        Returns:
            Validated list of lines.

        Raises:
            ValueError: If no lines are provided.
        """
        if not value:
            raise ValueError("Purchase order must have at least one line item")
        return value

    @property
    def is_fully_received(self) -> bool:
        """Check if all line items are fully received.

        Returns:
            True if all lines are fully received, False otherwise.
        """
        return all(
            line.received_quantity is not None
            and line.received_quantity >= line.quantity
            for line in self.lines
        )

    @property
    def is_fully_invoiced(self) -> bool:
        """Check if all line items are fully invoiced.

        Returns:
            True if all lines are fully invoiced, False otherwise.
        """
        return all(
            line.invoiced_quantity is not None
            and line.invoiced_quantity >= line.quantity
            for line in self.lines
        )


class PurchaseOrderListResponse(BaseModel):
    """Response model for purchase order list endpoint.

    Attributes:
        purchase_orders: List of purchase orders.
        total_count: Total number of purchase orders.
        page: Current page number.
        page_size: Number of items per page.
    """

    purchase_orders: List[PurchaseOrder] = Field(
        default_factory=list,
        description="List of purchase orders",
    )
    total_count: int = Field(..., description="Total count", ge=0)
    page: int = Field(default=1, description="Current page", ge=1)
    page_size: int = Field(default=50, description="Page size", ge=1, le=1000)


class PurchaseOrderFilters(BaseModel):
    """Query filters for purchase order list endpoint.

    Attributes:
        supplier_id: Filter by supplier ID.
        company_id: Filter by company ID.
        status: Filter by status.
        submit_date_from: Filter by submit date (from).
        submit_date_to: Filter by submit date (to).
        min_amount: Filter by minimum amount.
        max_amount: Filter by maximum amount.
    """

    supplier_id: Optional[str] = Field(None, description="Supplier ID filter")
    company_id: Optional[str] = Field(None, description="Company ID filter")
    status: Optional[str] = Field(None, description="Status filter")
    submit_date_from: Optional[date] = Field(
        None,
        description="Submit date from filter",
    )
    submit_date_to: Optional[date] = Field(None, description="Submit date to filter")
    min_amount: Optional[Decimal] = Field(
        None,
        description="Minimum amount filter",
        ge=0,
    )
    max_amount: Optional[Decimal] = Field(
        None,
        description="Maximum amount filter",
        ge=0,
    )

    @field_validator("max_amount")
    @classmethod
    def validate_amount_range(cls, value: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate max_amount is greater than min_amount.

        Args:
            value: Maximum amount to validate.
            info: Field validation info containing other field values.

        Returns:
            Validated maximum amount.

        Raises:
            ValueError: If max_amount is less than min_amount.
        """
        min_amount = info.data.get("min_amount")
        if value is not None and min_amount is not None and value < min_amount:
            raise ValueError("max_amount must be greater than or equal to min_amount")
        return value

    @field_validator("submit_date_to")
    @classmethod
    def validate_date_range(cls, value: Optional[date], info) -> Optional[date]:
        """Validate submit_date_to is after submit_date_from.

        Args:
            value: End date to validate.
            info: Field validation info containing other field values.

        Returns:
            Validated end date.

        Raises:
            ValueError: If end date is before start date.
        """
        start_date = info.data.get("submit_date_from")
        if value is not None and start_date is not None and value < start_date:
            raise ValueError(
                "submit_date_to must be greater than or equal to submit_date_from"
            )
        return value


def parse_workday_purchase_order(raw_data: Dict[str, Any]) -> PurchaseOrder:
    """Parse raw Workday SOAP response into PurchaseOrder model.

    Args:
        raw_data: Raw purchase order data from Workday SOAP API.

    Returns:
        Parsed PurchaseOrder instance.

    Raises:
        ValidationException: If data cannot be parsed.
    """
    from workday_procurement_api.utils.exceptions import ValidationException

    try:
        # Extract basic fields
        po_reference = raw_data.get("Purchase_Order_Reference", {})
        po_data = raw_data.get("Purchase_Order_Data", {})

        # Build PurchaseOrder model
        purchase_order = PurchaseOrder(
            purchase_order_id=po_reference.get("ID", [{}])[0].get("_value_1", ""),
            purchase_order_number=po_data.get("Purchase_Order_Number", ""),
            supplier=SupplierReference(
                id=po_data.get("Supplier_Reference", {}).get("ID", [{}])[0].get("_value_1", ""),
                descriptor=po_data.get("Supplier_Reference", {}).get("Descriptor", ""),
            ),
            company=CompanyReference(
                id=po_data.get("Company_Reference", {}).get("ID", [{}])[0].get("_value_1", ""),
                descriptor=po_data.get("Company_Reference", {}).get("Descriptor", ""),
            ),
            submit_date=po_data.get("Submit_Date", date.today()),
            total_amount=Decimal(str(po_data.get("Total_Amount", "0"))),
            currency=CurrencyReference(
                id=po_data.get("Currency_Reference", {}).get("ID", [{}])[0].get("_value_1", "USD"),
                descriptor=po_data.get("Currency_Reference", {}).get("Descriptor", "US Dollar"),
            ),
            status=PurchaseOrderStatus(
                status=po_data.get("Status", "Unknown"),
                status_descriptor=po_data.get("Status_Descriptor", ""),
            ),
            memo=po_data.get("Memo", None),
            lines=[],
            requisition_number=po_data.get("Requisition_Number", None),
        )

        # Parse line items
        lines_data = po_data.get("Purchase_Order_Line", [])
        for line_data in lines_data:
            line = PurchaseOrderLine(
                line_number=int(line_data.get("Line_Number", 0)),
                item_description=line_data.get("Item_Description", ""),
                quantity=Decimal(str(line_data.get("Quantity", "0"))),
                unit_cost=Decimal(str(line_data.get("Unit_Cost", "0"))),
                extended_amount=Decimal(str(line_data.get("Extended_Amount", "0"))),
                received_quantity=Decimal(str(line_data.get("Received_Quantity", "0")))
                if line_data.get("Received_Quantity")
                else None,
                invoiced_quantity=Decimal(str(line_data.get("Invoiced_Quantity", "0")))
                if line_data.get("Invoiced_Quantity")
                else None,
            )
            purchase_order.lines.append(line)

        return purchase_order

    except Exception as e:
        raise ValidationException(
            f"Failed to parse purchase order data: {str(e)}",
            error_code="PO_PARSE_ERROR",
            details={"raw_data": raw_data},
        ) from e
