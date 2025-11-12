"""FastAPI application entry point for Workday Procurement API.

This module initializes and configures the FastAPI application
with all routes, middleware, and error handlers.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from workday_procurement_api.api.routes import router as purchase_order_router
from workday_procurement_api.config.settings import get_settings
from workday_procurement_api.utils.logging_config import get_logger, setup_logging

# Initialize settings and logging
settings = get_settings()
setup_logging(settings.app)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler.

    Handles startup and shutdown events for the application.

    Args:
        app: FastAPI application instance.

    Yields:
        Control during application runtime.
    """
    # Startup
    logger.info(
        f"Starting {settings.app.app_name} v{settings.app.app_version}",
        extra={
            "extra_fields": {
                "debug": settings.app.debug,
                "log_level": settings.app.log_level,
            }
        },
    )
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app.app_name,
    version=settings.app.app_version,
    description=(
        "Enterprise-grade FastAPI application for interacting with "
        "Workday Purchase Order procurement endpoints via SOAP API"
    ),
    lifespan=lifespan,
    debug=settings.app.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors.

    Args:
        request: The request that caused the error.
        exc: The validation error.

    Returns:
        JSON response with error details.
    """
    logger.warning(
        "Request validation error",
        extra={"extra_fields": {"errors": exc.errors(), "body": exc.body}},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general unhandled exceptions.

    Args:
        request: The request that caused the error.
        exc: The exception.

    Returns:
        JSON response with error details.
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"extra_fields": {"path": request.url.path, "method": request.method}},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        },
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Check if the API is running and healthy.",
)
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status information.
    """
    return {
        "status": "healthy",
        "service": settings.app.app_name,
        "version": settings.app.app_version,
    }


@app.get(
    "/",
    tags=["Root"],
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    description="Get API information.",
)
async def root() -> dict:
    """Root endpoint with API information.

    Returns:
        API information.
    """
    return {
        "name": settings.app.app_name,
        "version": settings.app.app_version,
        "description": "Workday Purchase Order Procurement API",
        "docs_url": "/docs",
        "health_url": "/health",
    }


# Include routers
app.include_router(purchase_order_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "workday_procurement_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
        log_level=settings.app.log_level.lower(),
    )
