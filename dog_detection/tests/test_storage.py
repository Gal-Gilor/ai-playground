from unittest.mock import AsyncMock
from unittest.mock import patch

import aiohttp
import pytest

from src.storage import AsyncStorageBucket
from src.storage import get_storage_bucket


@pytest.mark.asyncio
async def test_create_storage_client_success():
    """Test successful creation of storage client."""
    # Arrange
    mock_session = AsyncMock(spec=aiohttp.ClientSession)

    # Act
    with patch("src.storage.Storage") as mock_storage_class:
        mock_storage_instance = AsyncMock()
        mock_storage_class.return_value = mock_storage_instance

        from src.storage import create_storage_client

        client = await create_storage_client(mock_session)

    # Assert
    mock_storage_class.assert_called_once_with(session=mock_session)
    assert client == mock_storage_instance


@pytest.mark.asyncio
async def test_create_storage_client_error():
    """Test error handling during storage client creation."""
    # Arrange
    mock_session = AsyncMock(spec=aiohttp.ClientSession)

    # Act
    with patch("src.storage.Storage") as mock_storage_class:
        mock_storage_class.side_effect = Exception("Authentication failed")

        from src.storage import create_storage_client

        # Assert
        with pytest.raises(Exception, match="Authentication failed"):
            await create_storage_client(mock_session)


@pytest.mark.asyncio
async def test_bucket_exists_success(mock_storage_client):
    """Test bucket exists method when bucket is accessible."""
    # Arrange
    # The mock is already configured to return a successful response
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    result = await bucket.exists()

    # Assert
    assert result is True
    mock_storage_client.list_objects.assert_called_once_with("test-bucket")


@pytest.mark.asyncio
async def test_bucket_exists_failure(mock_storage_client):
    """Test bucket exists method when bucket is not accessible."""
    # Arrange
    mock_storage_client.list_objects = AsyncMock(side_effect=Exception("Bucket not found"))
    bucket = AsyncStorageBucket(mock_storage_client, "nonexistent-bucket")

    # Act
    result = await bucket.exists()

    # Assert
    assert result is False
    mock_storage_client.list_objects.assert_called_once_with("nonexistent-bucket")


@pytest.mark.asyncio
async def test_list_blobs_success(mock_storage_client):
    """Test list_blobs method when successful."""
    # Arrange
    mock_storage_client.list_objects = AsyncMock(
        return_value={
            "items": [
                {"name": "file1.txt", "size": "100", "contentType": "text/plain"},
                {"name": "file2.pdf", "size": "2048", "contentType": "application/pdf"},
            ]
        }
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    result = await bucket.list_blobs()

    # Assert
    assert len(result) == 2
    assert result[0]["name"] == "file1.txt"
    assert result[1]["name"] == "file2.pdf"
    mock_storage_client.list_objects.assert_called_once_with(bucket="test-bucket", params={})


@pytest.mark.asyncio
async def test_list_blobs_with_prefix(mock_storage_client):
    """Test list_blobs method with prefix filter."""
    # Arrange
    mock_storage_client.list_objects = AsyncMock(
        return_value={
            "items": [
                {
                    "name": "documents/report.pdf",
                    "size": "2048",
                    "contentType": "application/pdf",
                }
            ]
        }
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")
    prefix = "documents/"

    # Act
    result = await bucket.list_blobs(prefix=prefix)

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == "documents/report.pdf"
    mock_storage_client.list_objects.assert_called_once_with(
        bucket="test-bucket", params={"prefix": prefix}
    )


@pytest.mark.asyncio
async def test_list_blobs_empty_result(mock_storage_client):
    """Test list_blobs method when bucket is empty."""
    # Arrange
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    result = await bucket.list_blobs()

    # Assert
    assert result == []
    mock_storage_client.list_objects.assert_called_once_with(bucket="test-bucket", params={})


@pytest.mark.asyncio
async def test_list_blobs_error(mock_storage_client):
    """Test list_blobs method when API call fails."""
    # Arrange
    mock_storage_client.list_objects = AsyncMock(
        side_effect=Exception("Failed to list objects")
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act & Assert
    with pytest.raises(Exception, match="Failed to list objects"):
        await bucket.list_blobs()


@pytest.mark.asyncio
async def test_upload_blob_from_file(mock_storage_client, tmp_path):
    """Test uploading a blob from a file."""
    # Arrange
    test_file = tmp_path / "test_upload.txt"
    test_file.write_text("Test content")

    mock_storage_client.upload = AsyncMock(
        return_value={
            "name": "uploads/test_upload.txt",
            "bucket": "test-bucket",
            "size": "12",
            "contentType": "text/plain",
        }
    )

    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")
    destination_blob_name = "uploads/test_upload.txt"

    # Act
    result = await bucket.upload_blob(test_file, destination_blob_name)

    # Assert
    assert result["name"] == "uploads/test_upload.txt"
    mock_storage_client.upload.assert_called_once_with(
        bucket="test-bucket",
        object_name=destination_blob_name,
        file_data=b"Test content",  # The actual bytes content
        content_type=None,
    )


@pytest.mark.asyncio
async def test_upload_blob_with_content_type(mock_storage_client, tmp_path):
    """Test uploading a blob with specific content type."""
    # Arrange
    test_file = tmp_path / "test_upload.json"
    test_file.write_text('{"key": "value"}')

    mock_storage_client.upload = AsyncMock(
        return_value={
            "name": "data/config.json",
            "bucket": "test-bucket",
            "contentType": "application/json",
        }
    )

    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")
    destination_blob_name = "data/config.json"
    content_type = "application/json"

    # Act
    result = await bucket.upload_blob(
        test_file, destination_blob_name, content_type=content_type
    )

    # Assert
    assert result["name"] == "data/config.json"
    assert result["contentType"] == "application/json"
    mock_storage_client.upload.assert_called_once_with(
        bucket="test-bucket",
        object_name=destination_blob_name,
        file_data=b'{"key": "value"}',
        content_type=content_type,
    )


@pytest.mark.asyncio
async def test_upload_blob_error(mock_storage_client, tmp_path):
    """Test error handling during blob upload."""
    # Arrange
    test_file = tmp_path / "test_upload.txt"
    test_file.write_text("Test content")

    mock_storage_client.upload = AsyncMock(
        side_effect=Exception("Upload failed: Permission denied")
    )

    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")
    destination_blob_name = "uploads/test_upload.txt"

    # Act & Assert
    with pytest.raises(Exception, match="Upload failed: Permission denied"):
        await bucket.upload_blob(test_file, destination_blob_name)


@pytest.mark.asyncio
async def test_download_blob_success(mock_storage_client, tmp_path):
    """Test successful blob download."""
    # Arrange
    blob_name = "documents/report.pdf"
    destination = tmp_path / "downloaded_report.pdf"
    destination_str = str(destination)

    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    await bucket.download_blob(blob_name, destination_str)

    # Assert
    assert destination.exists()
    assert destination.read_bytes() == b"test file content"
    mock_storage_client.download.assert_called_once_with(
        bucket="test-bucket",
        object_name=blob_name,
    )


@pytest.mark.asyncio
async def test_download_blob_to_existing_file(mock_storage_client, temp_file):
    """Test downloading a blob to an existing file (overwrite)."""
    # Arrange
    blob_name = "test-blob.txt"
    initial_content = temp_file.read_text()
    destination_str = str(temp_file)

    mock_storage_client.download = AsyncMock(return_value=b"new content")
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    await bucket.download_blob(blob_name, destination_str)

    # Assert
    assert temp_file.read_text() == "new content"  # Content should be overwritten
    assert temp_file.read_text() != initial_content
    mock_storage_client.download.assert_called_once_with(
        bucket="test-bucket",
        object_name=blob_name,
    )


@pytest.mark.asyncio
async def test_download_blob_create_parent_dirs(mock_storage_client, tmp_path):
    """Test downloading a blob to a path with non-existent parent directories."""
    # Arrange
    blob_name = "images/logo.png"
    destination = tmp_path / "nested" / "dir" / "structure" / "logo.png"
    destination_str = str(destination)

    # Verify parent directories don't exist yet
    assert not destination.parent.exists()

    mock_storage_client.download = AsyncMock(return_value=b"image data")
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    await bucket.download_blob(blob_name, destination_str)

    # Assert
    assert destination.parent.exists()  # Parent directories should be created
    assert destination.exists()
    assert destination.read_bytes() == b"image data"


@pytest.mark.asyncio
async def test_download_blob_error(mock_storage_client, tmp_path):
    """Test error handling when blob download fails."""
    # Arrange
    blob_name = "nonexistent.txt"
    destination = tmp_path / "should-not-exist.txt"
    destination_str = str(destination)

    mock_storage_client.download = AsyncMock(
        side_effect=Exception("Blob not found or access denied")
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act & Assert
    with pytest.raises(Exception, match="Blob not found or access denied"):
        await bucket.download_blob(blob_name, destination_str)

    # Verify the destination file wasn't created
    assert not destination.exists()


@pytest.mark.asyncio
async def test_delete_blob_success(mock_storage_client):
    """Test successful blob deletion."""
    # Arrange
    blob_name = "documents/old-report.pdf"
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    await bucket.delete_blob(blob_name)

    # Assert
    mock_storage_client.delete.assert_called_once_with(
        bucket="test-bucket",
        object_name=blob_name,
    )


@pytest.mark.asyncio
async def test_delete_blob_error(mock_storage_client):
    """Test error handling during blob deletion."""
    # Arrange
    blob_name = "protected-file.txt"

    mock_storage_client.delete = AsyncMock(
        side_effect=Exception("Delete failed: Permission denied")
    )

    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act & Assert
    with pytest.raises(Exception, match="Delete failed: Permission denied"):
        await bucket.delete_blob(blob_name)

    mock_storage_client.delete.assert_called_once_with(
        bucket="test-bucket",
        object_name=blob_name,
    )


@pytest.mark.asyncio
async def test_delete_nonexistent_blob(mock_storage_client):
    """Test deleting a blob that doesn't exist."""
    # Arrange
    blob_name = "nonexistent-file.txt"
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    await bucket.delete_blob(blob_name)

    # Assert
    mock_storage_client.delete.assert_called_once_with(
        bucket="test-bucket",
        object_name=blob_name,
    )


@pytest.mark.asyncio
async def test_get_blob_metadata_success(mock_storage_client):
    """Test successful retrieval of blob metadata."""
    # Arrange
    blob_name = "documents/report.pdf"
    expected_metadata = {
        "name": blob_name,
        "size": "1024",
        "contentType": "application/pdf",
        "updated": "2025-05-30T12:00:00Z",
    }

    mock_storage_client.download_metadata = AsyncMock(return_value=expected_metadata)
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act
    metadata = await bucket.get_blob_metadata(blob_name)

    # Assert
    assert metadata == expected_metadata
    assert metadata["size"] == "1024"
    assert metadata["contentType"] == "application/pdf"
    mock_storage_client.download_metadata.assert_called_once_with(
        bucket="test-bucket", object_name=blob_name
    )


@pytest.mark.asyncio
async def test_get_blob_metadata_error(mock_storage_client):
    """Test error handling when retrieving blob metadata fails."""
    # Arrange
    blob_name = "inaccessible-file.txt"

    mock_storage_client.download_metadata = AsyncMock(
        side_effect=Exception("Failed to retrieve metadata: Permission denied")
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act & Assert
    with pytest.raises(Exception, match="Failed to retrieve metadata: Permission denied"):
        await bucket.get_blob_metadata(blob_name)

    mock_storage_client.download_metadata.assert_called_once_with(
        bucket="test-bucket", object_name=blob_name
    )


@pytest.mark.asyncio
async def test_get_nonexistent_blob_metadata(mock_storage_client):
    """Test retrieving metadata for a non-existent blob."""
    # Arrange
    blob_name = "nonexistent-file.txt"

    # Most cloud storage APIs throw a specific exception for non-existent blobs
    mock_storage_client.download_metadata = AsyncMock(
        side_effect=Exception("Blob does not exist")
    )
    bucket = AsyncStorageBucket(mock_storage_client, "test-bucket")

    # Act & Assert
    with pytest.raises(Exception, match="Blob does not exist"):
        await bucket.get_blob_metadata(blob_name)

    mock_storage_client.download_metadata.assert_called_once_with(
        bucket="test-bucket", object_name=blob_name
    )


@pytest.mark.asyncio
async def test_get_storage_bucket():
    """Test getting a storage bucket instance."""
    # Arrange
    bucket_name = "test-bucket"

    # Act
    with patch("src.storage.create_storage_client") as mock_create_client:
        mock_client = AsyncMock()
        mock_create_client.return_value = mock_client

        bucket = await get_storage_bucket(bucket_name)

    # Assert
    mock_create_client.assert_called_once_with(None)  # Session defaulted to None
    assert isinstance(bucket, AsyncStorageBucket)
    assert bucket.client == mock_client
    assert bucket.name == bucket_name


@pytest.mark.asyncio
async def test_get_storage_bucket_with_session():
    """Test getting a storage bucket instance with a custom session."""
    # Arrange
    bucket_name = "test-bucket"
    mock_session = AsyncMock(spec=aiohttp.ClientSession)

    # Act
    with patch("src.storage.create_storage_client") as mock_create_client:
        mock_client = AsyncMock()
        mock_create_client.return_value = mock_client

        bucket = await get_storage_bucket(bucket_name, mock_session)

    # Assert
    mock_create_client.assert_called_once_with(mock_session)
    assert isinstance(bucket, AsyncStorageBucket)
    assert bucket.name == bucket_name
