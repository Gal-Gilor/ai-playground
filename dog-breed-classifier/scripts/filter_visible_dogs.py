"""Filter cropped images by dog visibility using Gemini.

Sends each cropped image to Gemini with a binary visibility question. Results are written
to an output CSV with an `is_visible` column. Supports resuming interrupted runs.

Usage (from project root):
    python -m scripts.filter_visible_dogs
    python -m scripts.filter_visible_dogs --help
"""

import argparse
import asyncio
import csv
import functools
import logging
import random
from pathlib import Path
from typing import IO

import pandas as pd
from aiolimiter import AsyncLimiter
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from tqdm.asyncio import tqdm

from config import FilterVisibleDogsConfig
from data_utils import get_image_path
from settings import config
from settings import env_variables

logger = logging.getLogger(__name__)

PROMPT = (
    "Is there a clearly discernible dog in this image? "
    "Answer True if a dog is present and clearly visible. "
    "Answer False if there is no dog, or if the dog is heavily obscured, blurry, or barely visible."  # noqa: E501
)


class DogVisibilityResponse(BaseModel):
    is_visible: bool


def retry_async(max_retries: int = 5, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except APIError as e:
                    if e.code in (429, 500, 503) and attempt < max_retries:
                        jitter = delay * (0.5 + random.random() * 0.5)
                        logger.warning(
                            "Attempt %d/%d (status %d), retry in %.2fs",
                            attempt,
                            max_retries,
                            e.code,
                            jitter,
                        )
                        await asyncio.sleep(jitter)
                        delay *= backoff_factor
                    else:
                        raise

        return wrapper

    return decorator


@retry_async()
async def classify_image(
    client: genai.Client,
    image_id: str,
    breed: str,
    image_path: Path,
    limiter: AsyncLimiter,
    model: str,
) -> dict:
    """Send a single image to Gemini and return its visibility classification.

    Args:
        client: Authenticated Gemini client.
        image_id: Crop UUID used to identify this image in the output.
        breed: Breed label for this crop.
        image_path: Path to the JPEG file on disk.
        limiter: Rate limiter to stay within API quota.
        model: Gemini model name.

    Returns:
        Dict with keys ``id``, ``breed``, and ``is_visible``.
    """
    image_bytes = image_path.read_bytes()
    async with limiter:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        response = await client.aio.models.generate_content(
            model=model,
            contents=[PROMPT, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DogVisibilityResponse,
            ),
        )
    result = DogVisibilityResponse.model_validate_json(response.text)
    return {"id": image_id, "breed": breed, "is_visible": result.is_visible}


async def _run_all(
    client: genai.Client,
    pending: list[tuple[str, str, Path]],
    limiter: AsyncLimiter,
    cfg: FilterVisibleDogsConfig,
    writer: csv.DictWriter,
    f: IO[str],
) -> int:
    """Dispatch all pending classification tasks concurrently, writing each row on completion.

    Args:
        client: Authenticated Gemini client.
        pending: List of (image_id, breed, image_path) tuples to classify.
        limiter: Rate limiter shared across all tasks.
        cfg: Pipeline configuration.
        writer: CSV writer to receive each result row immediately.
        f: Open file handle; flushed after every row.

    Returns:
        Count of successfully classified images.
    """
    tasks = [
        classify_image(client, image_id, breed, image_path, limiter, cfg.model)
        for image_id, breed, image_path in pending
    ]
    count = 0
    with tqdm(total=len(tasks), unit="img") as progress:
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                writer.writerow(result)
                f.flush()
                count += 1
            except Exception:
                logger.exception("Failed to classify an image; skipping")
            finally:
                progress.update(1)
    return count


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    cfg = config.training.filter_visible_dogs

    parser = argparse.ArgumentParser(
        description="Filter cropped images by dog visibility using Gemini."
    )
    parser.add_argument(
        "--cropped-images-directory",
        type=Path,
        default=Path(cfg.cropped_images_directory) if cfg else None,
        help="Directory of cropped JPEG images",
    )
    parser.add_argument(
        "--labels-csv",
        type=Path,
        default=Path(cfg.cropped_image_labels_csv) if cfg else None,
        help="CSV with id and breed columns (stage 2 output)",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(cfg.output_csv) if cfg else None,
        help="Output CSV path (id, breed, is_visible)",
    )
    parser.add_argument(
        "--model",
        default=cfg.model if cfg else "gemini-2.5-flash",
        help="Gemini model name",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=cfg.rate_limit if cfg else 10.0,
        help="Max requests per minute",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=cfg.max_retries if cfg else 5,
        help="Retry attempts on transient API errors",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and run the visibility classification pipeline."""
    args = parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("google_genai.models").setLevel(logging.WARNING)

    cfg = FilterVisibleDogsConfig(
        cropped_images_directory=str(args.cropped_images_directory),
        cropped_image_labels_csv=str(args.labels_csv),
        output_csv=str(args.output_csv),
        model=args.model,
        rate_limit=args.rate_limit,
        max_retries=args.max_retries,
    )

    labels = pd.read_csv(cfg.cropped_image_labels_csv)

    output_path = Path(cfg.output_csv)
    done_ids: set[str] = set()
    if output_path.exists():
        done_ids = set(pd.read_csv(output_path)["id"])

    pending = [
        (row.id, row.breed, get_image_path(Path(cfg.cropped_images_directory), row.id))
        for row in labels.itertuples()
        if row.id not in done_ids
    ]
    logger.info("%d images to classify (%d already done)", len(pending), len(done_ids))

    if not pending:
        logger.info("Nothing to do.")
        return

    client = genai.Client(
        vertexai=True,
        project=env_variables.GOOGLE_CLOUD_PROJECT,
        location=env_variables.GOOGLE_CLOUD_LOCATION,
    )
    limiter = AsyncLimiter(max_rate=cfg.rate_limit, time_period=60.0)

    write_header = not output_path.exists()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "breed", "is_visible"])
        if write_header:
            writer.writeheader()
        count = asyncio.run(_run_all(client, pending, limiter, cfg, writer, f))

    logger.info(
        "Classified %d new images; total in %s: %d",
        count,
        output_path,
        len(done_ids) + count,
    )


if __name__ == "__main__":
    main()
