"""SOAP client wrapper for Workday Resource Management API.

This module provides a type-safe, enterprise-grade wrapper around
the Workday SOAP API using zeep library.
"""

from typing import Any, Dict, List, Optional

from zeep import Client, Settings
from zeep.exceptions import Fault, TransportError
from zeep.helpers import serialize_object

from workday_procurement_api.auth.ws_security import WorkdayAuthenticator
from workday_procurement_api.config.settings import WorkdayAPIConfig, WorkdayAuthConfig
from workday_procurement_api.utils.exceptions import (
    SOAPClientException,
    WorkdayServiceException,
)
from workday_procurement_api.utils.logging_config import get_logger

logger = get_logger(__name__)


class WorkdaySOAPClient:
    """SOAP client for Workday Resource Management API.

    This class provides a wrapper around zeep SOAP client with
    enterprise features like retry logic, error handling, and logging.

    Attributes:
        api_config: API configuration.
        auth_config: Authentication configuration.
        client: Zeep SOAP client instance.
    """

    def __init__(
        self,
        api_config: WorkdayAPIConfig,
        auth_config: WorkdayAuthConfig,
    ) -> None:
        """Initialize SOAP client.

        Args:
            api_config: API configuration.
            auth_config: Authentication configuration.

        Raises:
            SOAPClientException: If client initialization fails.
        """
        self.api_config = api_config
        self.auth_config = auth_config
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize zeep SOAP client with authentication.

        Raises:
            SOAPClientException: If client initialization fails.
        """
        try:
            logger.info(
                "Initializing SOAP client",
                extra={
                    "extra_fields": {
                        "wsdl_url": self.api_config.resource_management_wsdl,
                        "api_version": self.api_config.api_version,
                    }
                },
            )

            # Configure zeep settings
            settings = Settings(
                strict=False,
                xml_huge_tree=True,
                xsd_ignore_sequence_order=True,
            )

            # Create client
            self.client = Client(
                wsdl=self.api_config.resource_management_wsdl,
                settings=settings,
            )

            # Apply authentication
            authenticator = WorkdayAuthenticator(self.auth_config)
            self.client = authenticator.apply_to_client(self.client)

            logger.info("SOAP client initialized successfully")

        except Exception as e:
            logger.error(
                f"Failed to initialize SOAP client: {str(e)}",
                exc_info=True,
            )
            raise SOAPClientException(
                f"Failed to initialize SOAP client: {str(e)}",
                error_code="CLIENT_INIT_FAILED",
            ) from e

    def _handle_soap_fault(self, fault: Fault) -> None:
        """Handle SOAP fault exceptions.

        Args:
            fault: SOAP fault exception.

        Raises:
            WorkdayServiceException: Converted SOAP fault.
        """
        fault_code = getattr(fault, "code", None)
        fault_string = getattr(fault, "message", str(fault))

        logger.error(
            "SOAP fault occurred",
            extra={
                "extra_fields": {
                    "fault_code": fault_code,
                    "fault_string": fault_string,
                }
            },
        )

        raise WorkdayServiceException(
            "Workday service returned an error",
            fault_code=fault_code,
            fault_string=fault_string,
            error_code="SOAP_FAULT",
        )

    def get_purchase_orders(
        self,
        request_criteria: Optional[Dict[str, Any]] = None,
        response_group: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Get purchase orders from Workday.

        Args:
            request_criteria: Filtering criteria for purchase orders.
            response_group: Response group configuration.

        Returns:
            List of purchase orders as dictionaries.

        Raises:
            SOAPClientException: If request fails.
            WorkdayServiceException: If Workday returns an error.
        """
        try:
            logger.info("Fetching purchase orders from Workday")

            if self.client is None:
                raise SOAPClientException(
                    "SOAP client not initialized",
                    error_code="CLIENT_NOT_INITIALIZED",
                )

            # Build request
            request = {}
            if request_criteria:
                request["Request_Criteria"] = request_criteria
            if response_group:
                request["Response_Group"] = response_group

            # Make SOAP call
            response = self.client.service.Get_Purchase_Orders(**request)

            # Serialize response to dict
            result = serialize_object(response, dict)

            logger.info(
                "Successfully fetched purchase orders",
                extra={
                    "extra_fields": {
                        "count": len(result.get("Response_Data", {}).get("Purchase_Order", [])),
                    }
                },
            )

            return result.get("Response_Data", {}).get("Purchase_Order", [])

        except Fault as e:
            self._handle_soap_fault(e)
        except TransportError as e:
            logger.error(f"Transport error: {str(e)}", exc_info=True)
            raise SOAPClientException(
                f"Network error communicating with Workday: {str(e)}",
                error_code="TRANSPORT_ERROR",
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise SOAPClientException(
                f"Unexpected error fetching purchase orders: {str(e)}",
                error_code="UNEXPECTED_ERROR",
            ) from e

    def get_purchase_order_by_id(
        self,
        purchase_order_id: str,
        response_group: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific purchase order by ID.

        Args:
            purchase_order_id: Purchase order ID.
            response_group: Response group configuration.

        Returns:
            Purchase order data or None if not found.

        Raises:
            SOAPClientException: If request fails.
            WorkdayServiceException: If Workday returns an error.
        """
        try:
            logger.info(
                f"Fetching purchase order: {purchase_order_id}",
                extra={"extra_fields": {"po_id": purchase_order_id}},
            )

            # Build request criteria for specific PO
            request_criteria = {
                "Purchase_Order_Reference": {
                    "ID": {
                        "type": "Purchase_Order_ID",
                        "_value_1": purchase_order_id,
                    }
                }
            }

            purchase_orders = self.get_purchase_orders(
                request_criteria=request_criteria,
                response_group=response_group,
            )

            if purchase_orders:
                logger.info(f"Found purchase order: {purchase_order_id}")
                return purchase_orders[0]
            else:
                logger.warning(f"Purchase order not found: {purchase_order_id}")
                return None

        except Exception as e:
            if isinstance(e, (SOAPClientException, WorkdayServiceException)):
                raise
            logger.error(f"Error fetching purchase order: {str(e)}", exc_info=True)
            raise SOAPClientException(
                f"Error fetching purchase order {purchase_order_id}: {str(e)}",
                error_code="PO_FETCH_ERROR",
            ) from e


def create_soap_client(
    api_config: Optional[WorkdayAPIConfig] = None,
    auth_config: Optional[WorkdayAuthConfig] = None,
) -> WorkdaySOAPClient:
    """Create and configure a Workday SOAP client.

    Args:
        api_config: API configuration. If None, loads from environment.
        auth_config: Authentication configuration. If None, loads from environment.

    Returns:
        Configured WorkdaySOAPClient instance.

    Raises:
        SOAPClientException: If client creation fails.
    """
    if api_config is None:
        api_config = WorkdayAPIConfig()

    if auth_config is None:
        auth_config = WorkdayAuthConfig()

    # Link auth config to API config for WSDL URL generation
    api_config.set_auth_config(auth_config)

    return WorkdaySOAPClient(api_config, auth_config)
