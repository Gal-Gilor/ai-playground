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


async def _download_one(bucket, sem, blob_name, dest_path):
    """Download a single blob from GCS under the semaphore concurrency limit.

    Args:
        bucket: AsyncStorageBucket instance to download from.
        sem (asyncio.Semaphore): Semaphore that caps concurrent downloads.
        blob_name (str): Blob name (path inside the bucket) to download.
        dest_path (Path): Local path where the file will be written.
    """
    async with sem:
        await bucket.download_blob(blob_name, str(dest_path))


async def main(
    output_dir: Path | None = None,
    source_prefix: str | None = None,
    file_type_suffix: str | None = None,
) -> None:
    """Download files from a GCS folder to a local directory.

    Reads defaults for output directory, source prefix, file suffix, and
    concurrency from config.yaml. Any argument passed directly overrides its
    config value.

    Args:
        output_dir: Local directory to write downloaded files into.
            Defaults to config's download-output-dir.
        source_prefix: GCS folder prefix to download from.
            Defaults to config's download-source-prefix.
        file_type_suffix: File extension filter (e.g. ".jpg"). Empty string
            or None downloads all files. Defaults to config's download-file-suffix.

    Raises:
        RuntimeError: If the configured GCS bucket is not accessible.
    """
    out_dir = Path(output_dir or config["download-output-dir"])
    prefix = source_prefix or config["download-source-prefix"]
    suffix = (
        file_type_suffix if file_type_suffix is not None else config["download-file-suffix"]
    )
    max_concurrent = config["download-max-concurrent"]

    async with aiohttp.ClientSession() as session:
        bucket = await get_storage_bucket(env_variables.GOOGLE_CLOUD_BUCKET, session)

        if not await bucket.exists():
            raise RuntimeError(f"Bucket '{env_variables.GOOGLE_CLOUD_BUCKET}' not accessible")

        blobs = await bucket.list_blobs(prefix=f"{prefix}/")

        # Strip the folder prefix to get bare filenames for local paths.
        downloads = [
            (blob["name"], out_dir / Path(blob["name"]).name)
            for blob in blobs
            if blob["name"] != f"{prefix}/"  # skip the folder placeholder blob
            and (not suffix or blob["name"].endswith(suffix))
        ]

        # Limit concurrent GCS connections to avoid overwhelming the API.
        sem = asyncio.Semaphore(max_concurrent)

        await tqdm.gather(
            *[_download_one(bucket, sem, blob_name, dest) for blob_name, dest in downloads],
            total=len(downloads),
            unit="file",
        )

    print(
        f"Done. {len(downloads)} files downloaded from "
        f"gs://{env_variables.GOOGLE_CLOUD_BUCKET}/{prefix}/ to {out_dir}/"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a GCS folder to a local directory.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Local directory to write files into. "
            "Overrides download-output-dir from config.yaml."
        ),
    )
    parser.add_argument(
        "--source-prefix",
        type=str,
        default=None,
        help="GCS folder prefix to download from. Overrides download-source-prefix.",
    )
    parser.add_argument(
        "--file-type-suffix",
        type=str,
        default=None,
        help='File extension filter (e.g. ".jpg"). Omit to download all files.',
    )
    args = parser.parse_args()

    asyncio.run(
        main(
            output_dir=args.output_dir,
            source_prefix=args.source_prefix,
            file_type_suffix=args.file_type_suffix,
        )
    )
