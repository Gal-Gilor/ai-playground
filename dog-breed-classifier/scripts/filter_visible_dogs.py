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
import logging
import sys
from pathlib import Path
from typing import IO

import pandas as pd
from aiolimiter import AsyncLimiter
from google import genai
from google.genai import errors
from google.genai import types
from pydantic import BaseModel
from tqdm.asyncio import tqdm

from config import FilterVisibleDogsConfig
from data_utils import get_image_path
from settings import config
from settings import env_variables

logger = logging.getLogger(__name__)

PROGRESS_EVERY = 500

PROMPT = (
    "Is there a clearly discernible dog in this image? "
    "Answer True if a dog is present and clearly visible. "
    "Answer False if there is no dog, or if the dog is heavily obscured, blurry, or barely visible."  # noqa: E501
)


class DogVisibilityResponse(BaseModel):
    """Structured Gemini response saying whether a dog is clearly visible."""

    is_visible: bool


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
        client (genai.Client): Authenticated Gemini client.
        image_id (str): Crop UUID used to identify this image in the output.
        breed (str): Breed label for this crop.
        image_path (Path): Path to the JPEG file on disk.
        limiter (AsyncLimiter): Rate limiter to stay within API quota.
        model (str): Gemini model name.

    Returns:
        dict: Dict with keys `id`, `breed`, and `is_visible`.
    """
    async with limiter:
        image_bytes = await asyncio.to_thread(image_path.read_bytes)
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


async def _run_pass(
    client: genai.Client,
    pending: list[tuple[str, str, Path]],
    limiter: AsyncLimiter,
    cfg: FilterVisibleDogsConfig,
    writer: csv.DictWriter,
    f: IO[str],
) -> tuple[int, list[tuple[str, str, Path]]]:
    """Classify the pending crops concurrently, writing each row on completion.

    Args:
        client (genai.Client): Authenticated Gemini client.
        pending (list[tuple[str, str, Path]]): List of (image_id, breed, image_path) tuples to
            classify.
        limiter (AsyncLimiter): Rate limiter shared across all tasks.
        cfg (FilterVisibleDogsConfig): Pipeline configuration.
        writer (csv.DictWriter): CSV writer to receive each result row immediately.
        f (IO[str]): Open file handle; flushed after every row.

    Returns:
        tuple[int, list[tuple[str, str, Path]]]: Count of classified crops, and the crops
            that failed with a 429 error. Other failures are logged and dropped.
    """
    tasks = {
        asyncio.create_task(classify_image(client, *crop, limiter, cfg.model)): crop
        for crop in pending
    }
    total = len(tasks)
    interactive = sys.stderr.isatty()
    count = 0
    processed = 0
    rate_limited = []
    remaining = set(tasks)
    with tqdm(total=total, unit="img", disable=not interactive) as progress:
        while remaining:
            done, remaining = await asyncio.wait(
                remaining, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                crop = tasks[task]
                error = task.exception()
                if error is None:
                    writer.writerow(task.result())
                    f.flush()
                    count += 1
                elif isinstance(error, errors.ClientError) and error.code == 429:
                    logger.warning("Rate limited on %s", crop[0])
                    rate_limited.append(crop)
                else:
                    logger.error("Failed to classify %s: %s", crop[0], error)
                processed += 1
                progress.update(1)
                if not interactive and (processed % PROGRESS_EVERY == 0 or processed == total):
                    logger.info("Processed %d/%d images", processed, total)
    return count, rate_limited


async def _run_passes(
    client: genai.Client,
    pending: list[tuple[str, str, Path]],
    cfg: FilterVisibleDogsConfig,
    writer: csv.DictWriter,
    f: IO[str],
) -> tuple[int, list[tuple[str, str, Path]]]:
    """Run up to `cfg.passes` passes, each retrying only the crops that got 429 errors.

    Args:
        client (genai.Client): Authenticated Gemini client.
        pending (list[tuple[str, str, Path]]): List of (image_id, breed, image_path) tuples to
            classify.
        cfg (FilterVisibleDogsConfig): Pipeline configuration.
        writer (csv.DictWriter): CSV writer to receive each result row immediately.
        f (IO[str]): Open file handle; flushed after every row.

    Returns:
        tuple[int, list[tuple[str, str, Path]]]: Count of classified crops, and the crops
            still rate limited after the last pass.
    """
    limiter = AsyncLimiter(max_rate=cfg.rate_limit, time_period=60.0)
    classified = 0
    for attempt in range(1, cfg.passes + 1):
        logger.info("Pass %d of %d: %d images", attempt, cfg.passes, len(pending))
        count, pending = await _run_pass(client, pending, limiter, cfg, writer, f)
        classified += count
        if not pending:
            break
    return classified, pending


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments, using `config.toml` values as defaults.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
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
        help="Attempts per request, including the first, on transient API errors",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=cfg.passes if cfg else 2,
        help="Passes over the crops; later passes retry only 429 failures",
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
    logging.getLogger("google_genai").setLevel(logging.WARNING)

    cfg = FilterVisibleDogsConfig(
        cropped_images_directory=str(args.cropped_images_directory),
        cropped_image_labels_csv=str(args.labels_csv),
        output_csv=str(args.output_csv),
        model=args.model,
        rate_limit=args.rate_limit,
        max_retries=args.max_retries,
        passes=args.passes,
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
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=cfg.max_retries)
        ),
    )
    write_header = not output_path.exists()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "breed", "is_visible"])
        if write_header:
            writer.writeheader()
        count, rate_limited = asyncio.run(_run_passes(client, pending, cfg, writer, f))

    logger.info(
        "Classified %d new images; total in %s: %d",
        count,
        output_path,
        len(done_ids) + count,
    )
    failed = len(pending) - count
    if failed:
        logger.warning(
            "%d images were not classified (%d still rate limited after %d passes): %s",
            failed,
            len(rate_limited),
            cfg.passes,
            [image_id for image_id, _, _ in rate_limited],
        )


if __name__ == "__main__":
    main()
