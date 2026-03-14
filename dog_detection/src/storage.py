import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from gcloud.aio.storage import Storage

logger = logging.getLogger(__name__)


async def extract_file_path_from_gsutil_url(url_or_path: str) -> str:
    """Extract file path from gsutil URL or return input if already a path.

    Args:
        url_or_path: A gsutil URL (gs://bucket/path/to/file) or file path.

    Returns:
        The file path portion (without bucket) or the original input if not
        a gs:// URL.

    Examples:
        >>> extract_file_path_from_gsutil_url("gs://my-bucket/folder/file.txt")
        'folder/file.txt'
        >>> extract_file_path_from_gsutil_url("gs://my-bucket/file.txt")
        'file.txt'
        >>> extract_file_path_from_gsutil_url("/local/path/file.txt")
        '/local/path/file.txt'
        >>> extract_file_path_from_gsutil_url("relative/path/file.txt")
        'relative/path/file.txt'
        >>> extract_file_path_from_gsutil_url("gs://bucket-only/")
        ''
    """
    if not url_or_path.startswith("gs://"):
        # Assume that the URL is a filepath
        return url_or_path

    parsed_url = urlparse(url_or_path)

    return parsed_url.path.lstrip("/")


async def create_storage_client(
    session: Optional[aiohttp.ClientSession] = None,
) -> Storage:
    """Create an async Google Cloud Storage client.

    Args:
        session: Optional aiohttp session. If None, client will create its own.

    Returns:
        Storage: Configured async Google Cloud Storage client instance.

    Raises:
        Exception: If client creation fails.
    """
    try:
        client = Storage(session=session)
        logger.info("Async Google Cloud Storage client created successfully.")
        return client

    except Exception as e:
        logger.error(f"Failed to create async Google Cloud Storage client: {e}", exc_info=True)
        raise


class AsyncStorageBucket:
    """Custom async storage bucket class for Google Cloud Storage.

    Provides async functionality for Google Cloud Storage bucket operations.
    """

    def __init__(self, client: Storage, name: str):
        """Initialize the async storage bucket.

        Args:
            client: Async Google Cloud Storage client instance.
            name: Name of the storage bucket.
        """
        self.client = client
        self.name = name

    async def exists(self) -> bool:
        """Check if the bucket exists.

        Returns:
            bool: True if bucket exists, False otherwise.

        Raises:
            Exception: If the check operation fails.
        """
        try:
            # Try to list objects to check if bucket exists and is accessible
            await self.client.list_objects(self.name)
            return True

        except Exception as e:
            logger.warning(
                f"Bucket '{self.name}' does not exist or is not accessible: {e}",
                exc_info=True,
            )
            return False

    async def list_blobs(self, prefix: Optional[str] = None) -> list:
        """List all blobs in the bucket.

        Args:
            prefix: Optional prefix to filter blobs.

        Returns:
            list: List of blob items in the bucket.

        Raises:
            Exception: If listing operation fails.
        """
        try:
            params = {}
            if prefix:
                params["prefix"] = prefix

            result = await self.client.list_objects(bucket=self.name, params=params)

            return result.get("items", [])

        except Exception as e:
            logger.error(f"Failed to list blobs in bucket '{self.name}': {e}", exc_info=True)
            raise

    async def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists in the bucket.

        Args:
            blob_name: Name of the blob to check.

        Returns:
            bool: True if blob exists, False otherwise."""
        try:
            # This only downloads metadata (~1KB), NOT the blob content
            await self.client.download_metadata(bucket=self.name, object_name=blob_name)
            return True

        except Exception:
            return False

    async def upload_blob(
        self,
        source_file_path: str,
        destination_blob_name: str,
        content_type: Optional[str] = None,
    ) -> dict:
        """Upload a file to the bucket.

        Args:
            source_file_path: Path to the local file to upload.
            destination_blob_name: Name for the blob in the bucket.
            content_type: MIME type of the file. If None, will be auto-detected.

        Returns:
            dict: Upload response containing metadata about the uploaded object.

        Raises:
            Exception: If upload operation fails.
        """
        try:
            with open(source_file_path, "rb") as file_obj:
                file_data = file_obj.read()

            result = await self.client.upload(
                bucket=self.name,
                object_name=destination_blob_name,
                file_data=file_data,
                content_type=content_type,
            )

            logger.info(
                f"File '{source_file_path}' uploaded to "
                f"'{self.name}/{destination_blob_name}' successfully."
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to upload file '{source_file_path}' to bucket '{self.name}': {e}",
                exc_info=True,
            )
            raise

    async def download_blob(self, source_blob_name: str, destination_file_path: str) -> None:
        """Download a blob from the bucket.

        Args:
            source_blob_name: Name of the blob to download.
            destination_file_path: Path where the file should be saved.

        Raises:
            Exception: If download operation fails.
        """
        try:
            blob_data = await self.client.download(
                bucket=self.name, object_name=source_blob_name
            )

            # Create parent directory if it doesn't exist
            destination_path = Path(destination_file_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)

            with open(destination_file_path, "wb") as file_obj:
                file_obj.write(blob_data)

            logger.info(
                f"Blob '{source_blob_name}' downloaded from "
                f"bucket '{self.name}' to '{destination_file_path}' successfully."
            )

        except Exception as e:
            logger.error(
                f"Failed to download blob '{source_blob_name}' from bucket '{self.name}': {e}",
                exc_info=True,
            )
            raise

    async def delete_blob(self, blob_name: str) -> None:
        """Delete a blob from the bucket.

        Args:
            blob_name: Name of the blob to delete.

        Raises:
            Exception: If deletion operation fails.
        """
        try:
            await self.client.delete(bucket=self.name, object_name=blob_name)
            logger.info(f"Blob '{blob_name}' deleted from bucket '{self.name}' successfully.")

        except Exception as e:
            logger.error(
                f"Failed to delete blob '{blob_name}' from bucket '{self.name}': {e}",
                exc_info=True,
            )
            raise

    async def get_blob_metadata(self, blob_name: str) -> dict:
        """Get metadata for a blob in the bucket.

        Args:
            blob_name: Name of the blob to get metadata for.

        Returns:
            dict: Blob metadata.

        Raises:
            Exception: If metadata retrieval fails.
        """
        try:
            metadata = await self.client.download_metadata(
                bucket=self.name, object_name=blob_name
            )
            logger.info(f"Retrieved metadata for blob '{blob_name}' successfully.")
            return metadata

        except Exception as e:
            logger.error(
                f"Failed to get metadata for blob '{blob_name}' from "
                f"bucket '{self.name}': {e}",
                exc_info=True,
            )
            raise


async def get_storage_bucket(
    bucket_name: str,
    session: Optional[aiohttp.ClientSession] = None,
) -> AsyncStorageBucket:
    """Get an async storage bucket instance.

    Args:
        bucket_name: Name of the storage bucket.
        session: Optional aiohttp session. If None, client will create its own.

    Returns:
        AsyncStorageBucket: Configured async storage bucket instance.

    Raises:
        Exception: If client creation fails.
    """
    client = await create_storage_client(session)

    return AsyncStorageBucket(client, bucket_name)
