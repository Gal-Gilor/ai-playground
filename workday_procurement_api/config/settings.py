"""Configuration management for Workday Procurement API.

This module handles configuration loading, validation, and management
using pydantic-settings for type safety and environment variable management.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkdayAuthConfig(BaseSettings):
    """Workday authentication configuration.

    Supports both username/password and certificate-based authentication
    for WS-Security.

    Attributes:
        username: Workday ISG user username (format: username@tenant).
        password: Workday ISG user password.
        tenant_name: Workday tenant name (e.g., 'acme_implementation').
        client_cert_path: Path to client certificate for cert-based auth.
        client_key_path: Path to client key for cert-based auth.
        auth_type: Authentication type ('password' or 'certificate').
    """

    username: str = Field(
        ...,
        description="Workday ISG user username (format: username@tenant)",
    )
    password: SecretStr = Field(
        ...,
        description="Workday ISG user password",
    )
    tenant_name: str = Field(
        ...,
        description="Workday tenant name",
    )
    client_cert_path: Optional[Path] = Field(
        default=None,
        description="Path to client certificate file",
    )
    client_key_path: Optional[Path] = Field(
        default=None,
        description="Path to client key file",
    )
    auth_type: str = Field(
        default="password",
        description="Authentication type: 'password' or 'certificate'",
    )

    model_config = SettingsConfigDict(
        env_prefix="WORKDAY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, value: str) -> str:
        """Validate username follows ISG format.

        Args:
            value: Username to validate.

        Returns:
            Validated username.

        Raises:
            ValueError: If username format is invalid.
        """
        if "@" not in value:
            raise ValueError(
                "Username must be in format 'username@tenant' for ISG users"
            )
        return value

    @field_validator("auth_type")
    @classmethod
    def validate_auth_type(cls, value: str) -> str:
        """Validate authentication type.

        Args:
            value: Authentication type to validate.

        Returns:
            Validated authentication type.

        Raises:
            ValueError: If authentication type is invalid.
        """
        allowed_types = {"password", "certificate"}
        if value not in allowed_types:
            raise ValueError(
                f"auth_type must be one of {allowed_types}, got '{value}'"
            )
        return value


class WorkdayAPIConfig(BaseSettings):
    """Workday SOAP API configuration.

    Attributes:
        base_url: Workday base URL.
        api_version: Workday Web Services version (e.g., 'v45.1').
        resource_management_wsdl: WSDL URL for Resource Management service.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_backoff_factor: Exponential backoff factor for retries.
    """

    base_url: str = Field(
        ...,
        description="Workday base URL (e.g., https://wd2-impl-services1.workday.com)",
    )
    api_version: str = Field(
        default="v45.1",
        description="Workday Web Services API version",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff factor",
    )

    model_config = SettingsConfigDict(
        env_prefix="WORKDAY_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resource_management_wsdl(self) -> str:
        """Get Resource Management WSDL URL.

        Returns:
            Full WSDL URL for Resource Management service.
        """
        return (
            f"{self.base_url}/ccx/service/"
            f"{self.auth_config.tenant_name}/Resource_Management/{self.api_version}"
            "?wsdl"
        )

    def set_auth_config(self, auth_config: WorkdayAuthConfig) -> None:
        """Set authentication config for WSDL URL generation.

        Args:
            auth_config: Authentication configuration instance.
        """
        self.auth_config = auth_config


class ApplicationConfig(BaseSettings):
    """Application-level configuration.

    Attributes:
        app_name: Application name.
        app_version: Application version.
        debug: Debug mode flag.
        log_level: Logging level.
        log_format: Log format ('json' or 'text').
    """

    app_name: str = Field(
        default="Workday Procurement API",
        description="Application name",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode flag",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        description="Log format: 'json' or 'text'",
    )

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Validate log level.

        Args:
            value: Log level to validate.

        Returns:
            Validated log level.

        Raises:
            ValueError: If log level is invalid.
        """
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        value_upper = value.upper()
        if value_upper not in allowed_levels:
            raise ValueError(
                f"log_level must be one of {allowed_levels}, got '{value}'"
            )
        return value_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        """Validate log format.

        Args:
            value: Log format to validate.

        Returns:
            Validated log format.

        Raises:
            ValueError: If log format is invalid.
        """
        allowed_formats = {"json", "text"}
        value_lower = value.lower()
        if value_lower not in allowed_formats:
            raise ValueError(
                f"log_format must be one of {allowed_formats}, got '{value}'"
            )
        return value_lower


class Settings(BaseSettings):
    """Main settings class combining all configuration sections.

    This class aggregates authentication, API, and application configurations
    and provides a cached instance for efficient access.
    """

    auth: WorkdayAuthConfig
    api: WorkdayAPIConfig
    app: ApplicationConfig

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Initialize settings and link auth config to API config."""
        super().__init__(**kwargs)
        self.api.set_auth_config(self.auth)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    This function provides a cached singleton instance of Settings
    for efficient access throughout the application.

    Returns:
        Settings instance.
    """
    return Settings(
        auth=WorkdayAuthConfig(),
        api=WorkdayAPIConfig(),
        app=ApplicationConfig(),
    )
