"""Microsoft Graph API authentication using MSAL (Microsoft Authentication Library).

This module implements enterprise-grade OAuth2 authentication with support
for confidential client applications, token caching, and automatic refresh.
"""

import logging
from typing import Dict, Optional

from msal import ConfidentialClientApplication

from outlook_graph_skill.auth.token_cache import TokenCache
from outlook_graph_skill.config.settings import SkillConfig
from outlook_graph_skill.utils.exceptions import (
    AuthenticationException,
    TokenException,
)

logger = logging.getLogger(__name__)


class GraphAuthenticator:
    """Authenticator for Microsoft Graph API using OAuth2 and MSAL.

    This class implements the OAuth2 Client Credentials flow for server-to-server
    authentication, suitable for background services and automated operations.

    Attributes:
        config: Skill configuration instance.
        _app: MSAL ConfidentialClientApplication instance.
        _token_cache: Token cache manager.
        _access_token: Currently valid access token (cached in memory).
    """

    def __init__(self, config: SkillConfig) -> None:
        """Initialize the Graph authenticator.

        Args:
            config: Configuration instance with auth settings.

        Raises:
            AuthenticationException: If configuration is invalid.
        """
        if not config.auth:
            raise AuthenticationException(
                "Authentication configuration is required",
                error_code="MISSING_AUTH_CONFIG",
            )

        self.config = config
        self._access_token: Optional[str] = None

        # Initialize token cache
        self._token_cache = TokenCache(
            cache_path=config.cache.cache_path,
            enabled=config.cache.enabled,
        )

        # Initialize MSAL Confidential Client Application
        try:
            self._app = ConfidentialClientApplication(
                client_id=config.auth.client_id,
                client_credential=config.auth.get_client_secret_value(),
                authority=config.auth.authority_url,
                token_cache=self._token_cache.get_cache(),
            )
            logger.info("Graph authenticator initialized successfully")
        except Exception as e:
            raise AuthenticationException(
                f"Failed to initialize MSAL application: {e}",
                error_code="MSAL_INIT_ERROR",
            )

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token for Microsoft Graph API.

        This method first attempts to retrieve a token from the cache.
        If no valid cached token exists, it acquires a new token using
        the client credentials flow.

        Args:
            force_refresh: Force token refresh even if cached token is valid.

        Returns:
            Valid access token string.

        Raises:
            TokenException: If token acquisition fails.
        """
        # Return cached in-memory token if available and not forcing refresh
        if self._access_token and not force_refresh:
            logger.debug("Using in-memory cached access token")
            return self._access_token

        # Try to get token from cache first
        if not force_refresh:
            cached_token = self._get_cached_token()
            if cached_token:
                self._access_token = cached_token
                return cached_token

        # Acquire new token
        new_token = self._acquire_new_token()
        self._access_token = new_token

        # Persist cache if modified
        self._token_cache.persist_if_modified()

        return new_token

    def _get_cached_token(self) -> Optional[str]:
        """Attempt to retrieve a valid token from cache.

        Returns:
            Access token if valid cached token exists, None otherwise.
        """
        try:
            accounts = self._app.get_accounts()
            if accounts:
                logger.debug("Found cached accounts, attempting silent token acquisition")
                result = self._app.acquire_token_silent(
                    scopes=self.config.auth.scopes,
                    account=accounts[0],
                )

                if result and "access_token" in result:
                    logger.info("Successfully acquired token from cache")
                    return result["access_token"]
                else:
                    logger.debug("No valid cached token found")
                    return None
            else:
                logger.debug("No cached accounts found")
                return None
        except Exception as e:
            logger.warning(f"Error retrieving cached token: {e}")
            return None

    def _acquire_new_token(self) -> str:
        """Acquire a new access token using client credentials flow.

        Returns:
            New access token string.

        Raises:
            TokenException: If token acquisition fails.
        """
        try:
            logger.info("Acquiring new access token via client credentials flow")
            result = self._app.acquire_token_for_client(
                scopes=self.config.auth.scopes
            )

            if "access_token" in result:
                logger.info("Successfully acquired new access token")
                return result["access_token"]
            else:
                # Handle error response
                error = result.get("error", "unknown_error")
                error_description = result.get(
                    "error_description",
                    "No error description provided",
                )
                correlation_id = result.get("correlation_id", "N/A")

                raise TokenException(
                    f"Token acquisition failed: {error}",
                    error_code=error.upper(),
                    details={
                        "description": error_description,
                        "correlation_id": correlation_id,
                    },
                )
        except TokenException:
            raise
        except Exception as e:
            raise TokenException(
                f"Unexpected error during token acquisition: {e}",
                error_code="TOKEN_ACQUISITION_ERROR",
            )

    def refresh_token(self) -> str:
        """Force refresh of the access token.

        Returns:
            New access token string.

        Raises:
            TokenException: If token refresh fails.
        """
        logger.info("Forcing token refresh")
        return self.get_access_token(force_refresh=True)

    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        logger.info("Clearing token cache")
        self._access_token = None
        self._token_cache.clear()

    def get_authorization_header(self) -> Dict[str, str]:
        """Get authorization header with Bearer token.

        Returns:
            Dictionary with Authorization header.

        Raises:
            TokenException: If token acquisition fails.
        """
        token = self.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def validate_token(self) -> bool:
        """Validate that a token can be acquired.

        Returns:
            True if authentication is working correctly.

        Raises:
            AuthenticationException: If authentication fails.
        """
        try:
            self.get_access_token()
            logger.info("Token validation successful")
            return True
        except Exception as e:
            raise AuthenticationException(
                f"Token validation failed: {e}",
                error_code="TOKEN_VALIDATION_ERROR",
            )

    def __enter__(self) -> "GraphAuthenticator":
        """Context manager entry.

        Returns:
            Self for use in with statements.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - persist cache if modified."""
        self._token_cache.persist_if_modified()
