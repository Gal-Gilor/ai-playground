"""Configuration management for Outlook Graph API Skill.

This module handles configuration loading, validation, and management
using Pydantic Settings for robust type validation and automatic .env loading.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    computed_field,
    SecretStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from outlook_graph_skill.utils.exceptions import ConfigurationException


class AuthConfig(BaseModel):
    """Authentication configuration settings.

    Attributes:
        client_id: Microsoft Entra ID application (client) ID.
        tenant_id: Microsoft Entra ID tenant (directory) ID.
        client_secret: Application client secret (sensitive).
        authority: Authentication authority URL (computed if not provided).
        scopes: List of Microsoft Graph API scopes.
    """

    client_id: str = Field(
        ...,
        min_length=1,
        description="Microsoft Entra ID application (client) ID",
    )
    tenant_id: str = Field(
        ...,
        min_length=1,
        description="Microsoft Entra ID tenant (directory) ID",
    )
    client_secret: SecretStr = Field(
        ...,
        description="Application client secret (sensitive)",
    )
    authority: Optional[str] = Field(
        default=None,
        description="Authentication authority URL",
    )
    scopes: List[str] = Field(
        default_factory=lambda: ["https://graph.microsoft.com/.default"],
        description="List of Microsoft Graph API scopes",
    )

    @computed_field
    @property
    def authority_url(self) -> str:
        """Get the authentication authority URL.

        Returns:
            The complete authority URL for authentication.
        """
        if self.authority:
            return self.authority
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @field_validator("client_id", "tenant_id")
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Validate that required fields are not empty.

        Args:
            v: Field value to validate.
            info: Field validation info.

        Returns:
            The validated value.

        Raises:
            ValueError: If field is empty.
        """
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} cannot be empty")
        return v.strip()

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Validate scopes list.

        Args:
            v: List of scopes to validate.

        Returns:
            The validated scopes list.

        Raises:
            ValueError: If scopes list is invalid.
        """
        if not v:
            return ["https://graph.microsoft.com/.default"]
        return [scope.strip() for scope in v if scope.strip()]

    def get_client_secret_value(self) -> str:
        """Get the client secret as plain string.

        Returns:
            The client secret value.
        """
        return self.client_secret.get_secret_value()


class GraphAPIConfig(BaseModel):
    """Microsoft Graph API configuration settings.

    Attributes:
        base_url: Base URL for Microsoft Graph API.
        api_version: API version to use.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_backoff_factor: Exponential backoff factor for retries.
    """

    base_url: str = Field(
        default="https://graph.microsoft.com",
        description="Base URL for Microsoft Graph API",
    )
    api_version: str = Field(
        default="v1.0",
        description="API version to use",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff factor for retries",
    )

    @computed_field
    @property
    def endpoint(self) -> str:
        """Get the full API endpoint URL.

        Returns:
            The complete base endpoint URL.
        """
        return f"{self.base_url}/{self.api_version}"


class CacheConfig(BaseModel):
    """Token cache configuration settings.

    Attributes:
        enabled: Whether token caching is enabled.
        cache_dir: Directory for storing cached tokens.
        cache_file_name: Name of the cache file.
    """

    enabled: bool = Field(
        default=True,
        description="Whether token caching is enabled",
    )
    cache_dir: str = Field(
        default=".cache",
        description="Directory for storing cached tokens",
    )
    cache_file_name: str = Field(
        default="token_cache.bin",
        description="Name of the cache file",
    )

    @computed_field
    @property
    def cache_path(self) -> Path:
        """Get the full cache file path.

        Returns:
            Path object for the cache file.
        """
        return Path(self.cache_dir) / self.cache_file_name


class SkillConfig(BaseSettings):
    """Main configuration class for Outlook Graph API Skill.

    This class uses Pydantic Settings to manage configuration from multiple
    sources including environment variables, .env files, and direct initialization.
    It automatically loads from .env files and provides robust validation.

    Environment Variables:
        AZURE_CLIENT_ID: Microsoft Entra ID application ID
        AZURE_TENANT_ID: Microsoft Entra ID tenant ID
        AZURE_CLIENT_SECRET: Application client secret
        AZURE_AUTHORITY: Optional authentication authority URL
        GRAPH_API_SCOPES: Comma-separated list of scopes
        API__BASE_URL: Optional API base URL
        API__TIMEOUT: Optional API timeout
        CACHE__ENABLED: Optional cache enabled flag

    Examples:
        # Automatic loading from .env file
        config = SkillConfig()

        # Override specific values
        config = SkillConfig(azure_client_id="custom-id")

        # Nested configuration using double underscore
        config = SkillConfig(api__timeout=60)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        validate_default=True,
    )

    # Authentication settings
    azure_client_id: str = Field(
        ...,
        description="Microsoft Entra ID application (client) ID",
    )
    azure_tenant_id: str = Field(
        ...,
        description="Microsoft Entra ID tenant (directory) ID",
    )
    azure_client_secret: SecretStr = Field(
        ...,
        description="Application client secret",
    )
    azure_authority: Optional[str] = Field(
        default=None,
        description="Optional authentication authority URL",
    )
    graph_api_scopes: str = Field(
        default="https://graph.microsoft.com/.default",
        description="Comma-separated list of Microsoft Graph API scopes",
    )

    # Nested configurations
    api: GraphAPIConfig = Field(
        default_factory=GraphAPIConfig,
        description="Microsoft Graph API configuration",
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Token cache configuration",
    )

    @computed_field
    @property
    def auth(self) -> AuthConfig:
        """Get AuthConfig from settings.

        Returns:
            AuthConfig instance built from settings.
        """
        scopes = [
            s.strip()
            for s in self.graph_api_scopes.split(",")
            if s.strip()
        ]
        return AuthConfig(
            client_id=self.azure_client_id,
            tenant_id=self.azure_tenant_id,
            client_secret=self.azure_client_secret,
            authority=self.azure_authority,
            scopes=scopes,
        )

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "SkillConfig":
        """Load configuration from environment variables and .env file.

        This method provides backwards compatibility with the previous API.
        The new recommended way is to simply instantiate SkillConfig(),
        which automatically loads from .env.

        Args:
            env_file: Path to .env file (default: '.env').

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If required environment variables are missing.

        Examples:
            config = SkillConfig.from_env()
            config = SkillConfig.from_env('.env.production')
        """
        try:
            return cls(_env_file=env_file)
        except Exception as e:
            raise ConfigurationException(
                f"Failed to load configuration from environment: {e}",
                error_code="ENV_LOAD_ERROR",
            )

    @classmethod
    def from_json(cls, file_path: str) -> "SkillConfig":
        """Load configuration from JSON file.

        Args:
            file_path: Path to JSON configuration file.

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If file cannot be read or parsed.

        Examples:
            config = SkillConfig.from_json('config.json')
        """
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
        except FileNotFoundError:
            raise ConfigurationException(
                f"Configuration file not found: {file_path}",
                error_code="CONFIG_FILE_NOT_FOUND",
            )
        except json.JSONDecodeError as e:
            raise ConfigurationException(
                f"Invalid JSON in configuration file: {e}",
                error_code="INVALID_JSON",
            )

        return cls.from_dict(config_data)

    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> "SkillConfig":
        """Load configuration from dictionary.

        Args:
            config_data: Dictionary containing configuration data.

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If configuration data is invalid.

        Examples:
            config = SkillConfig.from_dict({
                'azure_client_id': 'id',
                'azure_tenant_id': 'tenant',
                'azure_client_secret': 'secret',
            })
        """
        try:
            # Handle nested auth structure from old format
            if "auth" in config_data:
                auth_data = config_data["auth"]
                config_data["azure_client_id"] = auth_data.get("client_id")
                config_data["azure_tenant_id"] = auth_data.get("tenant_id")
                config_data["azure_client_secret"] = auth_data.get(
                    "client_secret"
                )
                config_data["azure_authority"] = auth_data.get("authority")
                if "scopes" in auth_data:
                    config_data["graph_api_scopes"] = ",".join(
                        auth_data["scopes"]
                    )

            return cls(**config_data)
        except Exception as e:
            raise ConfigurationException(
                f"Invalid configuration data: {e}",
                error_code="INVALID_CONFIG_DATA",
            )

    def validate(self) -> bool:
        """Validate the complete configuration.

        This method is provided for backwards compatibility.
        Pydantic automatically validates on instantiation.

        Returns:
            True if configuration is valid.

        Examples:
            config = SkillConfig()
            if config.validate():
                print("Configuration is valid")
        """
        # Validation happens automatically in Pydantic
        return True

    def to_dict(self, exclude_secrets: bool = True) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Args:
            exclude_secrets: Whether to exclude sensitive data (default: True).

        Returns:
            Dictionary representation of configuration.

        Examples:
            config = SkillConfig()
            config_dict = config.to_dict()
            config_dict_with_secrets = config.to_dict(exclude_secrets=False)
        """
        data = self.model_dump(mode="json")

        if exclude_secrets:
            # Redact sensitive information
            data["azure_client_secret"] = "***REDACTED***"

        # Convert to old format for backwards compatibility
        result = {
            "auth": {
                "client_id": data["azure_client_id"],
                "tenant_id": data["azure_tenant_id"],
                "client_secret": data["azure_client_secret"],
                "authority": data.get("azure_authority"),
                "scopes": data["graph_api_scopes"].split(","),
            },
            "api": data["api"],
            "cache": data["cache"],
        }

        return result

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
