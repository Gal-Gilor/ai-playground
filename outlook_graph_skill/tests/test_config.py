"""Comprehensive tests for Pydantic-based configuration.

This module tests the configuration management system including
Pydantic Settings, validation, and various loading methods.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from outlook_graph_skill.config.settings import (
    AuthConfig,
    CacheConfig,
    GraphAPIConfig,
    SkillConfig,
)
from outlook_graph_skill.utils.exceptions import ConfigurationException


class TestAuthConfig:
    """Tests for AuthConfig Pydantic model."""

    def test_auth_config_valid(self):
        """Test creating valid AuthConfig."""
        config = AuthConfig(
            client_id="test-client-id",
            tenant_id="test-tenant-id",
            client_secret="test-secret",
        )

        assert config.client_id == "test-client-id"
        assert config.tenant_id == "test-tenant-id"
        assert config.get_client_secret_value() == "test-secret"

    def test_auth_config_default_scopes(self):
        """Test AuthConfig with default scopes."""
        config = AuthConfig(
            client_id="test-id",
            tenant_id="test-tenant",
            client_secret="test-secret",
        )

        assert config.scopes == ["https://graph.microsoft.com/.default"]

    def test_auth_config_custom_scopes(self):
        """Test AuthConfig with custom scopes."""
        custom_scopes = ["Mail.Read", "Mail.Send"]
        config = AuthConfig(
            client_id="test-id",
            tenant_id="test-tenant",
            client_secret="test-secret",
            scopes=custom_scopes,
        )

        assert config.scopes == custom_scopes

    def test_auth_config_authority_url(self):
        """Test computed authority_url property."""
        config = AuthConfig(
            client_id="test-id",
            tenant_id="my-tenant-id",
            client_secret="test-secret",
        )

        expected_url = "https://login.microsoftonline.com/my-tenant-id"
        assert config.authority_url == expected_url

    def test_auth_config_custom_authority(self):
        """Test AuthConfig with custom authority."""
        custom_authority = "https://login.custom.com/tenant"
        config = AuthConfig(
            client_id="test-id",
            tenant_id="test-tenant",
            client_secret="test-secret",
            authority=custom_authority,
        )

        assert config.authority_url == custom_authority

    def test_auth_config_validation_empty_client_id(self):
        """Test validation fails for empty client_id."""
        with pytest.raises(ValidationError) as exc_info:
            AuthConfig(
                client_id="",
                tenant_id="test-tenant",
                client_secret="test-secret",
            )

        errors = exc_info.value.errors()
        assert any("client_id" in str(err["loc"]) for err in errors)

    def test_auth_config_validation_empty_tenant_id(self):
        """Test validation fails for empty tenant_id."""
        with pytest.raises(ValidationError) as exc_info:
            AuthConfig(
                client_id="test-id",
                tenant_id="   ",  # Whitespace only
                client_secret="test-secret",
            )

        errors = exc_info.value.errors()
        assert any("tenant_id" in str(err["loc"]) for err in errors)


class TestGraphAPIConfig:
    """Tests for GraphAPIConfig Pydantic model."""

    def test_graph_api_config_defaults(self):
        """Test GraphAPIConfig with default values."""
        config = GraphAPIConfig()

        assert config.base_url == "https://graph.microsoft.com"
        assert config.api_version == "v1.0"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 2.0

    def test_graph_api_config_endpoint(self):
        """Test computed endpoint property."""
        config = GraphAPIConfig()
        assert config.endpoint == "https://graph.microsoft.com/v1.0"

    def test_graph_api_config_custom_values(self):
        """Test GraphAPIConfig with custom values."""
        config = GraphAPIConfig(
            base_url="https://custom.api.com",
            api_version="v2.0",
            timeout=60,
            max_retries=5,
            retry_backoff_factor=3.0,
        )

        assert config.base_url == "https://custom.api.com"
        assert config.api_version == "v2.0"
        assert config.timeout == 60
        assert config.endpoint == "https://custom.api.com/v2.0"

    def test_graph_api_config_validation_timeout_range(self):
        """Test timeout validation."""
        # Valid timeout
        config = GraphAPIConfig(timeout=30)
        assert config.timeout == 30

        # Too small
        with pytest.raises(ValidationError):
            GraphAPIConfig(timeout=0)

        # Too large
        with pytest.raises(ValidationError):
            GraphAPIConfig(timeout=700)

    def test_graph_api_config_validation_max_retries(self):
        """Test max_retries validation."""
        # Valid values
        GraphAPIConfig(max_retries=0)
        GraphAPIConfig(max_retries=10)

        # Invalid - negative
        with pytest.raises(ValidationError):
            GraphAPIConfig(max_retries=-1)

        # Invalid - too large
        with pytest.raises(ValidationError):
            GraphAPIConfig(max_retries=11)


class TestCacheConfig:
    """Tests for CacheConfig Pydantic model."""

    def test_cache_config_defaults(self):
        """Test CacheConfig with default values."""
        config = CacheConfig()

        assert config.enabled is True
        assert config.cache_dir == ".cache"
        assert config.cache_file_name == "token_cache.bin"

    def test_cache_config_cache_path(self):
        """Test computed cache_path property."""
        config = CacheConfig()

        expected_path = Path(".cache") / "token_cache.bin"
        assert config.cache_path == expected_path

    def test_cache_config_custom_values(self):
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            enabled=False,
            cache_dir="/tmp/custom_cache",
            cache_file_name="custom.bin",
        )

        assert config.enabled is False
        assert config.cache_dir == "/tmp/custom_cache"
        assert config.cache_file_name == "custom.bin"
        assert config.cache_path == Path("/tmp/custom_cache") / "custom.bin"


class TestSkillConfig:
    """Tests for SkillConfig Pydantic Settings."""

    @pytest.fixture
    def valid_env_vars(self):
        """Provide valid environment variables."""
        return {
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_TENANT_ID": "test-tenant-id",
            "AZURE_CLIENT_SECRET": "test-secret",
        }

    @pytest.fixture
    def temp_env_file(self, valid_env_vars):
        """Create a temporary .env file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as f:
            for key, value in valid_env_vars.items():
                f.write(f"{key}={value}\n")
            env_file_path = f.name

        yield env_file_path

        # Cleanup
        os.unlink(env_file_path)

    def test_skill_config_from_env_vars(self, valid_env_vars, monkeypatch):
        """Test SkillConfig loading from environment variables."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig()

        assert config.azure_client_id == "test-client-id"
        assert config.azure_tenant_id == "test-tenant-id"
        assert config.azure_client_secret.get_secret_value() == "test-secret"

    def test_skill_config_from_env_method(
        self, valid_env_vars, temp_env_file, monkeypatch
    ):
        """Test SkillConfig.from_env() backwards compatible method."""
        # Clear environment to ensure we're loading from file
        for key in valid_env_vars.keys():
            monkeypatch.delenv(key, raising=False)

        config = SkillConfig.from_env(temp_env_file)

        assert config.azure_client_id == "test-client-id"
        assert config.azure_tenant_id == "test-tenant-id"

    def test_skill_config_auth_property(self, valid_env_vars, monkeypatch):
        """Test computed auth property."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig()
        auth = config.auth

        assert isinstance(auth, AuthConfig)
        assert auth.client_id == "test-client-id"
        assert auth.tenant_id == "test-tenant-id"

    def test_skill_config_nested_configuration(
        self, valid_env_vars, monkeypatch
    ):
        """Test nested configuration with double underscore."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("API__TIMEOUT", "60")
        monkeypatch.setenv("API__MAX_RETRIES", "5")
        monkeypatch.setenv("CACHE__ENABLED", "false")

        config = SkillConfig()

        assert config.api.timeout == 60
        assert config.api.max_retries == 5
        assert config.cache.enabled is False

    def test_skill_config_from_dict(self):
        """Test SkillConfig.from_dict() method."""
        data = {
            "azure_client_id": "dict-client-id",
            "azure_tenant_id": "dict-tenant-id",
            "azure_client_secret": "dict-secret",
        }

        config = SkillConfig.from_dict(data)

        assert config.azure_client_id == "dict-client-id"
        assert config.azure_tenant_id == "dict-tenant-id"

    def test_skill_config_from_dict_old_format(self):
        """Test from_dict with old nested auth format."""
        data = {
            "auth": {
                "client_id": "old-client-id",
                "tenant_id": "old-tenant-id",
                "client_secret": "old-secret",
                "scopes": ["Mail.Read", "Mail.Send"],
            }
        }

        config = SkillConfig.from_dict(data)

        assert config.azure_client_id == "old-client-id"
        assert config.azure_tenant_id == "old-tenant-id"
        assert config.auth.scopes == ["Mail.Read", "Mail.Send"]

    def test_skill_config_from_json(self, tmp_path):
        """Test SkillConfig.from_json() method."""
        json_file = tmp_path / "config.json"
        data = {
            "azure_client_id": "json-client-id",
            "azure_tenant_id": "json-tenant-id",
            "azure_client_secret": "json-secret",
        }

        with open(json_file, "w") as f:
            json.dump(data, f)

        config = SkillConfig.from_json(str(json_file))

        assert config.azure_client_id == "json-client-id"

    def test_skill_config_to_dict(self, valid_env_vars, monkeypatch):
        """Test to_dict() method."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig()
        config_dict = config.to_dict()

        assert config_dict["auth"]["client_id"] == "test-client-id"
        assert config_dict["auth"]["client_secret"] == "***REDACTED***"
        assert "api" in config_dict
        assert "cache" in config_dict

    def test_skill_config_to_dict_with_secrets(
        self, valid_env_vars, monkeypatch
    ):
        """Test to_dict() without redacting secrets."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig()
        config_dict = config.to_dict(exclude_secrets=False)

        # Secrets should be included (but still as SecretStr in JSON mode)
        assert "client_secret" in config_dict["auth"]

    def test_skill_config_validation(self, valid_env_vars, monkeypatch):
        """Test validate() method."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig()

        # Should not raise exception
        assert config.validate() is True

    def test_skill_config_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises((ValidationError, ConfigurationException)):
            SkillConfig()  # Missing all required fields

    def test_skill_config_programmatic_override(
        self, valid_env_vars, monkeypatch
    ):
        """Test programmatic override of configuration."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)

        config = SkillConfig(api__timeout=120)

        assert config.api.timeout == 120  # Overridden
        assert config.azure_client_id == "test-client-id"  # From env

    def test_skill_config_scopes_parsing(self, valid_env_vars, monkeypatch):
        """Test scopes parsing from comma-separated string."""
        for key, value in valid_env_vars.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("GRAPH_API_SCOPES", "Mail.Read, Mail.Send, User.Read")

        config = SkillConfig()

        assert len(config.auth.scopes) == 3
        assert "Mail.Read" in config.auth.scopes
        assert "Mail.Send" in config.auth.scopes


class TestConfigurationExceptionHandling:
    """Tests for configuration exception handling."""

    def test_from_json_file_not_found(self):
        """Test ConfigurationException for missing JSON file."""
        with pytest.raises(ConfigurationException) as exc_info:
            SkillConfig.from_json("nonexistent.json")

        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "CONFIG_FILE_NOT_FOUND"

    def test_from_json_invalid_json(self, tmp_path):
        """Test ConfigurationException for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{ invalid json }")

        with pytest.raises(ConfigurationException) as exc_info:
            SkillConfig.from_json(str(json_file))

        assert "invalid json" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "INVALID_JSON"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
