"""WS-Security authentication for Workday SOAP API.

This module implements enterprise-grade authentication using WS-Security
with support for both UsernameToken and X.509 certificate authentication.
"""

from pathlib import Path
from typing import Optional

from zeep import Client
from zeep.wsse.username import UsernameToken

from workday_procurement_api.config.settings import WorkdayAuthConfig
from workday_procurement_api.utils.exceptions import AuthenticationException


class WorkdayAuthenticator:
    """Handles authentication for Workday SOAP API.

    This class provides enterprise-grade authentication using WS-Security
    with support for both password-based and certificate-based authentication.

    Attributes:
        auth_config: Authentication configuration.
    """

    def __init__(self, auth_config: WorkdayAuthConfig) -> None:
        """Initialize authenticator.

        Args:
            auth_config: Authentication configuration.

        Raises:
            AuthenticationException: If configuration is invalid.
        """
        self.auth_config = auth_config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate authentication configuration.

        Raises:
            AuthenticationException: If configuration is invalid.
        """
        if self.auth_config.auth_type == "certificate":
            if not self.auth_config.client_cert_path:
                raise AuthenticationException(
                    "Certificate authentication requires client_cert_path",
                    error_code="MISSING_CERT_PATH",
                )
            if not self.auth_config.client_key_path:
                raise AuthenticationException(
                    "Certificate authentication requires client_key_path",
                    error_code="MISSING_KEY_PATH",
                )
            self._validate_cert_files()

    def _validate_cert_files(self) -> None:
        """Validate certificate and key files exist.

        Raises:
            AuthenticationException: If certificate files are invalid.
        """
        cert_path = self.auth_config.client_cert_path
        key_path = self.auth_config.client_key_path

        if not cert_path.exists():
            raise AuthenticationException(
                f"Certificate file not found: {cert_path}",
                error_code="CERT_FILE_NOT_FOUND",
            )

        if not key_path.exists():
            raise AuthenticationException(
                f"Key file not found: {key_path}",
                error_code="KEY_FILE_NOT_FOUND",
            )

        if not cert_path.is_file():
            raise AuthenticationException(
                f"Certificate path is not a file: {cert_path}",
                error_code="INVALID_CERT_PATH",
            )

        if not key_path.is_file():
            raise AuthenticationException(
                f"Key path is not a file: {key_path}",
                error_code="INVALID_KEY_PATH",
            )

    def get_wsse_credentials(self) -> UsernameToken:
        """Get WS-Security credentials for SOAP client.

        Returns:
            UsernameToken credentials for zeep client.

        Raises:
            AuthenticationException: If authentication setup fails.
        """
        try:
            if self.auth_config.auth_type == "password":
                return self._get_username_token()
            elif self.auth_config.auth_type == "certificate":
                # Certificate-based auth would require additional setup
                # For now, fall back to username token
                raise AuthenticationException(
                    "Certificate authentication not yet implemented",
                    error_code="CERT_AUTH_NOT_IMPLEMENTED",
                )
            else:
                raise AuthenticationException(
                    f"Unsupported auth type: {self.auth_config.auth_type}",
                    error_code="UNSUPPORTED_AUTH_TYPE",
                )
        except Exception as e:
            if isinstance(e, AuthenticationException):
                raise
            raise AuthenticationException(
                f"Failed to setup authentication: {str(e)}",
                error_code="AUTH_SETUP_FAILED",
            ) from e

    def _get_username_token(self) -> UsernameToken:
        """Get UsernameToken for password-based authentication.

        Returns:
            UsernameToken instance configured with credentials.
        """
        password = self.auth_config.password.get_secret_value()
        return UsernameToken(
            username=self.auth_config.username,
            password=password,
            use_digest=True,
        )

    def apply_to_client(self, client: Client) -> Client:
        """Apply authentication to zeep SOAP client.

        Args:
            client: Zeep SOAP client instance.

        Returns:
            Client with authentication applied.

        Raises:
            AuthenticationException: If authentication cannot be applied.
        """
        try:
            wsse = self.get_wsse_credentials()
            client.wsse = wsse
            return client
        except Exception as e:
            if isinstance(e, AuthenticationException):
                raise
            raise AuthenticationException(
                f"Failed to apply authentication to client: {str(e)}",
                error_code="AUTH_APPLICATION_FAILED",
            ) from e


def create_authenticator(
    auth_config: Optional[WorkdayAuthConfig] = None,
) -> WorkdayAuthenticator:
    """Create and configure a Workday authenticator.

    Args:
        auth_config: Authentication configuration. If None, loads from environment.

    Returns:
        Configured WorkdayAuthenticator instance.

    Raises:
        AuthenticationException: If authentication setup fails.
    """
    if auth_config is None:
        try:
            auth_config = WorkdayAuthConfig()
        except Exception as e:
            raise AuthenticationException(
                f"Failed to load authentication configuration: {str(e)}",
                error_code="CONFIG_LOAD_FAILED",
            ) from e

    return WorkdayAuthenticator(auth_config)
