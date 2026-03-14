import argparse
import asyncio
import logging
from pathlib import Path

import aiohttp
from tqdm.asyncio import tqdm

from src.settings import config
from src.settings import env_variables
from src.storage import get_storage_bucket

logger = logging.getLogger(__name__)


async def _upload_one(bucket, sem, file_path, destination):
    """Upload a single file to GCS under the semaphore concurrency limit.

    Args:
        bucket: AsyncStorageBucket instance to upload to.
        sem (asyncio.Semaphore): Semaphore that caps concurrent uploads.
        file_path (Path): Local path of the file to upload.
        destination (str): Blob name (path inside the bucket) for the upload.
    """
    async with sem:
        await bucket.upload_blob(str(file_path), destination, content_type=None)


async def main(
    folder_to_upload: Path | None = None,
    destination_prefix: str | None = None,
    file_type_suffix: str | None = None,
) -> None:
    """Upload files from a local folder to GCS, skipping files already present.

    Reads defaults for folder, destination prefix, file suffix, and concurrency
    from config.yaml. Any argument passed directly overrides its config value.
    Lists existing blobs once so the run is resumable after an interruption.

    Args:
        folder_to_upload: Local directory containing files to upload.
            Defaults to config's path-to-images.
        destination_prefix: Bucket path prefix for uploaded blobs.
            Defaults to config's upload-destination-prefix.
        file_type_suffix: File extension filter (e.g. ".jpg"). Empty string
            or None uploads all files. Defaults to config's upload-file-suffix.

    Raises:
        RuntimeError: If the configured GCS bucket is not accessible.
    """
    folder = Path(folder_to_upload or config["path-to-images"])
    prefix = destination_prefix or config["upload-destination-prefix"]
    suffix = file_type_suffix if file_type_suffix is not None else config["upload-file-suffix"]
    max_concurrent = config["upload-max-concurrent"]

    file_paths = sorted(folder.glob(f"*{suffix}"))

    async with aiohttp.ClientSession() as session:
        bucket = await get_storage_bucket(env_variables.GOOGLE_CLOUD_BUCKET, session)

        if not await bucket.exists():
            raise RuntimeError(f"Bucket '{env_variables.GOOGLE_CLOUD_BUCKET}' not accessible")

        # Fetch already-uploaded blob names to make the run resumable.
        existing = {blob["name"] for blob in await bucket.list_blobs(prefix=f"{prefix}/")}

        pending = [p for p in file_paths if f"{prefix}/{p.name}" not in existing]

        if existing:
            print(f"Resuming: {len(existing)} done, {len(pending)} remaining.")

        # Limit concurrent GCS connections to avoid overwhelming the API.
        sem = asyncio.Semaphore(max_concurrent)

        await tqdm.gather(
            *[_upload_one(bucket, sem, p, f"{prefix}/{p.name}") for p in pending],
            total=len(pending),
            unit="file",
        )

    print(
        f"Done. {len(pending)} files uploaded to "
        f"gs://{env_variables.GOOGLE_CLOUD_BUCKET}/{prefix}/"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a local folder to a GCS bucket.")
    parser.add_argument(
        "--folder-to-upload",
        type=Path,
        default=None,
        help="Local directory to upload. Overrides path-to-images from config.yaml.",
    )
    parser.add_argument(
        "--destination-prefix",
        type=str,
        default=None,
        help="Bucket path prefix for uploaded blobs. Overrides upload-destination-prefix.",
    )
    parser.add_argument(
        "--file-type-suffix",
        type=str,
        default=None,
        help='File extension filter (e.g. ".jpg"). Omit to upload all files.',
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            folder_to_upload=args.folder_to_upload,
            destination_prefix=args.destination_prefix,
            file_type_suffix=args.file_type_suffix,
        )
    )
