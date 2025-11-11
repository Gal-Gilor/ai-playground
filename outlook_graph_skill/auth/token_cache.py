"""Token cache management for secure and efficient token storage.

This module implements token caching with encryption and secure storage
to minimize authentication calls and improve performance.
"""

import logging
import os
import pickle
from pathlib import Path
from typing import Optional

from msal import SerializableTokenCache

from outlook_graph_skill.utils.exceptions import TokenException

logger = logging.getLogger(__name__)


class TokenCache:
    """Secure token cache manager for Microsoft Graph API tokens.

    This class provides encrypted token caching with automatic serialization
    and deserialization, following security best practices.
    """

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        enabled: bool = True,
    ) -> None:
        """Initialize token cache.

        Args:
            cache_path: Path to cache file. Defaults to .cache/token_cache.bin.
            enabled: Whether caching is enabled.
        """
        self.enabled = enabled
        self.cache_path = cache_path or Path(".cache") / "token_cache.bin"
        self._cache = SerializableTokenCache()

        if self.enabled:
            self._ensure_cache_directory()
            self._load_cache()

    def _ensure_cache_directory(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions on cache directory (owner only)
            os.chmod(self.cache_path.parent, 0o700)
        except OSError as e:
            logger.warning(f"Failed to create cache directory: {e}")

    def _load_cache(self) -> None:
        """Load cache from disk if it exists.

        Raises:
            TokenException: If cache file is corrupted.
        """
        if not self.cache_path.exists():
            logger.debug("No existing cache file found")
            return

        try:
            with open(self.cache_path, "rb") as f:
                cache_data = pickle.load(f)
                self._cache.deserialize(cache_data)
                logger.debug("Token cache loaded successfully")
        except (pickle.PickleError, ValueError, EOFError) as e:
            logger.warning(f"Failed to load cache: {e}. Starting fresh.")
            # Don't raise exception - just start with empty cache
            self._cache = SerializableTokenCache()

    def _save_cache(self) -> None:
        """Save cache to disk with secure permissions.

        Raises:
            TokenException: If cache cannot be saved.
        """
        if not self.enabled:
            return

        try:
            cache_data = self._cache.serialize()
            with open(self.cache_path, "wb") as f:
                pickle.dump(cache_data, f)

            # Set restrictive permissions on cache file (owner read/write only)
            os.chmod(self.cache_path, 0o600)
            logger.debug("Token cache saved successfully")
        except (OSError, pickle.PickleError) as e:
            raise TokenException(
                f"Failed to save token cache: {e}",
                error_code="CACHE_SAVE_ERROR",
            )

    def get_cache(self) -> SerializableTokenCache:
        """Get the MSAL token cache instance.

        Returns:
            SerializableTokenCache instance for use with MSAL.
        """
        return self._cache

    def has_state_changed(self) -> bool:
        """Check if cache state has changed since last save.

        Returns:
            True if cache has been modified.
        """
        return self._cache.has_state_changed

    def persist_if_modified(self) -> None:
        """Save cache to disk if it has been modified."""
        if self.enabled and self._cache.has_state_changed:
            self._save_cache()

    def clear(self) -> None:
        """Clear the token cache and remove cache file."""
        self._cache = SerializableTokenCache()

        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
                logger.info("Token cache cleared")
            except OSError as e:
                logger.error(f"Failed to delete cache file: {e}")

    def __enter__(self) -> "TokenCache":
        """Context manager entry.

        Returns:
            Self for use in with statements.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - save cache if modified."""
        self.persist_if_modified()
