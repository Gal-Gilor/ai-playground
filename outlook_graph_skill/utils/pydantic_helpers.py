"""Pydantic helper utilities for Outlook Graph API Skill.

This module provides utilities for working with Pydantic validation,
including error mapping and conversion helpers.
"""

from typing import Dict, List

from pydantic import ValidationError

from outlook_graph_skill.utils.exceptions import ConfigurationException


def handle_pydantic_validation_error(
    error: ValidationError,
) -> ConfigurationException:
    """Convert Pydantic ValidationError to ConfigurationException.

    This function transforms Pydantic validation errors into our custom
    ConfigurationException format, preserving error details and providing
    user-friendly error messages.

    Args:
        error: The Pydantic ValidationError to convert.

    Returns:
        ConfigurationException with mapped error details.

    Examples:
        try:
            config = SkillConfig()
        except ValidationError as e:
            raise handle_pydantic_validation_error(e)
    """
    errors = error.errors()

    if not errors:
        return ConfigurationException(
            f"Configuration validation failed: {str(error)}",
            error_code="VALIDATION_ERROR",
        )

    # Get the first error for the main message
    first_error = errors[0]
    field_path = ".".join(str(loc) for loc in first_error["loc"])
    error_msg = first_error["msg"]
    error_type = first_error["type"]

    # Create detailed error message
    message = f"Configuration validation failed for '{field_path}': {error_msg}"

    # Map common Pydantic error types to user-friendly messages
    if error_type == "missing":
        message = f"Required configuration field '{field_path}' is missing"
    elif error_type == "string_type":
        message = f"Field '{field_path}' must be a string"
    elif error_type == "int_type":
        message = f"Field '{field_path}' must be an integer"
    elif error_type == "value_error":
        message = f"Invalid value for '{field_path}': {error_msg}"

    # Include all errors in details
    error_details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in errors
    ]

    return ConfigurationException(
        message,
        error_code="VALIDATION_ERROR",
        details={
            "validation_errors": error_details,
            "error_count": len(errors),
        },
    )


def format_validation_errors(error: ValidationError) -> List[str]:
    """Format Pydantic validation errors as readable strings.

    Args:
        error: The Pydantic ValidationError.

    Returns:
        List of formatted error messages.

    Examples:
        try:
            config = SkillConfig()
        except ValidationError as e:
            for msg in format_validation_errors(e):
                print(f"  - {msg}")
    """
    formatted_errors = []

    for err in error.errors():
        field_path = ".".join(str(loc) for loc in err["loc"])
        message = err["msg"]
        formatted_errors.append(f"{field_path}: {message}")

    return formatted_errors


def get_validation_error_summary(error: ValidationError) -> Dict[str, any]:
    """Get a summary of validation errors.

    Args:
        error: The Pydantic ValidationError.

    Returns:
        Dictionary with error summary information.

    Examples:
        try:
            config = SkillConfig()
        except ValidationError as e:
            summary = get_validation_error_summary(e)
            print(f"Found {summary['count']} validation errors")
    """
    errors = error.errors()

    return {
        "count": len(errors),
        "errors": [
            {
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
                "input": err.get("input"),
            }
            for err in errors
        ],
        "fields": list(
            set(".".join(str(loc) for loc in err["loc"]) for err in errors)
        ),
    }
