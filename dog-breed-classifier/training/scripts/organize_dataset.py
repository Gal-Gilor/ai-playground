"""Organize cropped images into per-breed subdirectories for PyTorch ImageFolder.

Usage (from project root):
    python -m training.scripts.organize_dataset
    python -m training.scripts.organize_dataset --help
"""

import argparse
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from app.settings import config

logger = logging.getLogger(__name__)


def _copy_file(src_dst: tuple[str, str]) -> str | None:
    """Copy src to dst. Returns src path string if source is missing, else None."""
    src, dst = src_dst
    if not Path(src).exists():
        return src
    shutil.copy2(src, dst)
    return None


def _create_breed_directories(train_directory: Path, breeds: pd.Series) -> None:
    for breed in breeds.unique():
        (train_directory / breed).mkdir(exist_ok=True)


def organize_dataset(
    labels_csv: Path,
    cropped_images_directory: Path,
    train_directory: Path,
    id_column: str = "id",
    breed_column: str = "breed",
) -> tuple[int, int]:
    """Copy cropped images into {train_directory}/{breed}/{id}.jpg.

    Returns:
        (copied, skipped) counts.
    """
    df = pd.read_csv(labels_csv)
    train_directory.mkdir(parents=True, exist_ok=True)
    _create_breed_directories(train_directory, df[breed_column])

    # Vectorized path construction — no DataFrame iteration
    src_paths = str(cropped_images_directory) + "/" + df[id_column].astype(str) + ".jpg"
    dst_paths = (
        str(train_directory) + "/" + df[breed_column].astype(str)
        + "/" + df[id_column].astype(str) + ".jpg"
    )
    pairs = list(zip(src_paths, dst_paths))

    with ThreadPoolExecutor() as executor:
        results = list(
            tqdm(executor.map(_copy_file, pairs), total=len(pairs), desc="Organizing images")
        )

    missing = [r for r in results if r is not None]
    for src in missing:
        logger.warning(f"Missing source image: {src}")

    copied = len(pairs) - len(missing)
    skipped = len(missing)
    logger.info(f"Done. Copied: {copied} | Skipped: {skipped}")
    return copied, skipped


def parse_args() -> argparse.Namespace:
    cfg = config.training.organize_dataset
    parser = argparse.ArgumentParser(
        description="Organize cropped images into per-breed subdirectories."
    )
    parser.add_argument(
        "--labels-csv",
        type=Path,
        default=Path(cfg.cropped_image_labels_csv),
    )
    parser.add_argument(
        "--cropped-images-directory",
        type=Path,
        default=Path(cfg.cropped_images_directory),
    )
    parser.add_argument(
        "--train-directory",
        type=Path,
        default=Path(cfg.train_directory),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cfg_crop = config.training.crop_images
    organize_dataset(
        args.labels_csv,
        args.cropped_images_directory,
        args.train_directory,
        id_column=cfg_crop.output_id_column,
        breed_column=cfg_crop.breed_column,
    )


if __name__ == "__main__":
    main()
