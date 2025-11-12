"""Logging configuration for Workday Procurement API.

This module provides enterprise-grade structured logging with support
for both JSON and text formats.
"""

import logging
import sys
from typing import Any, Dict

from workday_procurement_api.config.settings import ApplicationConfig


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Formats log records as JSON for easier parsing and analysis
    in log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON-formatted log string.
        """
        import json
        from datetime import datetime

        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def setup_logging(app_config: ApplicationConfig) -> None:
    """Configure application logging.

    Args:
        app_config: Application configuration.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(app_config.log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(app_config.log_level)

    # Set formatter based on config
    if app_config.log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("zeep").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
