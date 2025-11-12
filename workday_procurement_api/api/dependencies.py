"""FastAPI dependencies for dependency injection.

This module provides dependency injection functions for FastAPI
endpoints, including configuration and SOAP client management.
"""

from functools import lru_cache
from typing import Generator

from fastapi import Depends

from workday_procurement_api.config.settings import Settings, get_settings
from workday_procurement_api.soap.client import WorkdaySOAPClient, create_soap_client
from workday_procurement_api.utils.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_soap_client_cached(
    settings: Settings = Depends(get_settings),
) -> WorkdaySOAPClient:
    """Get cached SOAP client instance.

    This function creates a singleton SOAP client instance for
    efficient connection reuse across requests.

    Args:
        settings: Application settings.

    Returns:
        Configured WorkdaySOAPClient instance.
    """
    logger.info("Creating SOAP client instance")
    return create_soap_client(
        api_config=settings.api,
        auth_config=settings.auth,
    )


def get_soap_client(
    client: WorkdaySOAPClient = Depends(get_soap_client_cached),
) -> Generator[WorkdaySOAPClient, None, None]:
    """Get SOAP client for request.

    This dependency provides the SOAP client to route handlers
    with proper lifecycle management.

    Args:
        client: Cached SOAP client instance.

    Yields:
        WorkdaySOAPClient instance for the request.
    """
    try:
        yield client
    finally:
        # Cleanup if needed (connection pooling handles this)
        pass
