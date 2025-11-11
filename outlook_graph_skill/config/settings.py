"""Configuration management for Outlook Graph API Skill.

This module handles configuration loading, validation, and management
with security best practices.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from outlook_graph_skill.utils.exceptions import ConfigurationException


@dataclass
class AuthConfig:
    """Authentication configuration settings.

    Attributes:
        client_id: Azure AD application (client) ID.
        tenant_id: Azure AD tenant (directory) ID.
        client_secret: Application client secret (sensitive).
        authority: Authentication authority URL.
        scopes: List of Microsoft Graph API scopes.
    """

    client_id: str
    tenant_id: str
    client_secret: str
    authority: Optional[str] = None
    scopes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and set default values after initialization."""
        if not self.authority:
            self.authority = (
                f"https://login.microsoftonline.com/{self.tenant_id}"
            )

        if not self.scopes:
            self.scopes = ["https://graph.microsoft.com/.default"]

        self._validate()

    def _validate(self) -> None:
        """Validate authentication configuration.

        Raises:
            ConfigurationException: If configuration is invalid.
        """
        if not self.client_id:
            raise ConfigurationException(
                "Client ID is required",
                error_code="MISSING_CLIENT_ID",
            )

        if not self.tenant_id:
            raise ConfigurationException(
                "Tenant ID is required",
                error_code="MISSING_TENANT_ID",
            )

        if not self.client_secret:
            raise ConfigurationException(
                "Client secret is required",
                error_code="MISSING_CLIENT_SECRET",
            )


@dataclass
class GraphAPIConfig:
    """Microsoft Graph API configuration settings.

    Attributes:
        base_url: Base URL for Microsoft Graph API.
        api_version: API version to use.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        retry_backoff_factor: Exponential backoff factor for retries.
    """

    base_url: str = "https://graph.microsoft.com"
    api_version: str = "v1.0"
    timeout: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    @property
    def endpoint(self) -> str:
        """Get the full API endpoint URL.

        Returns:
            The complete base endpoint URL.
        """
        return f"{self.base_url}/{self.api_version}"


@dataclass
class CacheConfig:
    """Token cache configuration settings.

    Attributes:
        enabled: Whether token caching is enabled.
        cache_dir: Directory for storing cached tokens.
        cache_file_name: Name of the cache file.
    """

    enabled: bool = True
    cache_dir: str = ".cache"
    cache_file_name: str = "token_cache.bin"

    @property
    def cache_path(self) -> Path:
        """Get the full cache file path.

        Returns:
            Path object for the cache file.
        """
        return Path(self.cache_dir) / self.cache_file_name


class SkillConfig:
    """Main configuration class for Outlook Graph API Skill.

    This class manages all configuration aspects including authentication,
    API settings, and caching. It supports loading from environment variables,
    JSON files, and direct initialization.
    """

    def __init__(
        self,
        auth_config: Optional[AuthConfig] = None,
        api_config: Optional[GraphAPIConfig] = None,
        cache_config: Optional[CacheConfig] = None,
    ) -> None:
        """Initialize skill configuration.

        Args:
            auth_config: Authentication configuration.
            api_config: Graph API configuration.
            cache_config: Cache configuration.
        """
        self.auth = auth_config
        self.api = api_config or GraphAPIConfig()
        self.cache = cache_config or CacheConfig()

    @classmethod
    def from_env(cls) -> "SkillConfig":
        """Load configuration from environment variables.

        Environment variables:
            AZURE_CLIENT_ID: Azure AD application ID.
            AZURE_TENANT_ID: Azure AD tenant ID.
            AZURE_CLIENT_SECRET: Application client secret.
            GRAPH_API_SCOPES: Comma-separated list of scopes (optional).

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If required environment variables are missing.
        """
        try:
            client_id = os.environ["AZURE_CLIENT_ID"]
            tenant_id = os.environ["AZURE_TENANT_ID"]
            client_secret = os.environ["AZURE_CLIENT_SECRET"]
        except KeyError as e:
            raise ConfigurationException(
                f"Missing required environment variable: {e.args[0]}",
                error_code="MISSING_ENV_VAR",
            )

        scopes_str = os.getenv("GRAPH_API_SCOPES", "")
        scopes = (
            [s.strip() for s in scopes_str.split(",") if s.strip()]
            if scopes_str
            else []
        )

        auth_config = AuthConfig(
            client_id=client_id,
            tenant_id=tenant_id,
            client_secret=client_secret,
            scopes=scopes,
        )

        return cls(auth_config=auth_config)

    @classmethod
    def from_json(cls, file_path: str) -> "SkillConfig":
        """Load configuration from JSON file.

        Args:
            file_path: Path to JSON configuration file.

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If file cannot be read or parsed.
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
    def from_dict(cls, config_data: Dict) -> "SkillConfig":
        """Load configuration from dictionary.

        Args:
            config_data: Dictionary containing configuration data.

        Returns:
            Configured SkillConfig instance.

        Raises:
            ConfigurationException: If configuration data is invalid.
        """
        try:
            auth_data = config_data.get("auth", {})
            auth_config = AuthConfig(
                client_id=auth_data["client_id"],
                tenant_id=auth_data["tenant_id"],
                client_secret=auth_data["client_secret"],
                authority=auth_data.get("authority"),
                scopes=auth_data.get("scopes", []),
            )

            api_data = config_data.get("api", {})
            api_config = GraphAPIConfig(**api_data) if api_data else None

            cache_data = config_data.get("cache", {})
            cache_config = CacheConfig(**cache_data) if cache_data else None

            return cls(
                auth_config=auth_config,
                api_config=api_config,
                cache_config=cache_config,
            )
        except KeyError as e:
            raise ConfigurationException(
                f"Missing required configuration key: {e.args[0]}",
                error_code="MISSING_CONFIG_KEY",
            )
        except TypeError as e:
            raise ConfigurationException(
                f"Invalid configuration data: {e}",
                error_code="INVALID_CONFIG_DATA",
            )

    def validate(self) -> bool:
        """Validate the complete configuration.

        Returns:
            True if configuration is valid.

        Raises:
            ConfigurationException: If configuration is invalid.
        """
        if not self.auth:
            raise ConfigurationException(
                "Authentication configuration is required",
                error_code="MISSING_AUTH_CONFIG",
            )

        # Auth config validation happens in AuthConfig.__post_init__
        return True

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary (excluding sensitive data).

        Returns:
            Dictionary representation of configuration.
        """
        return {
            "auth": {
                "client_id": self.auth.client_id if self.auth else None,
                "tenant_id": self.auth.tenant_id if self.auth else None,
                "client_secret": "***REDACTED***",
                "authority": self.auth.authority if self.auth else None,
                "scopes": self.auth.scopes if self.auth else [],
            },
            "api": {
                "base_url": self.api.base_url,
                "api_version": self.api.api_version,
                "timeout": self.api.timeout,
                "max_retries": self.api.max_retries,
                "retry_backoff_factor": self.api.retry_backoff_factor,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "cache_dir": self.cache.cache_dir,
                "cache_file_name": self.cache.cache_file_name,
            },
        }
