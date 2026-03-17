"""Copy cropped images into per-breed subdirectories for PyTorch ImageFolder.

Usage (from project root):
    python -m training.scripts.create_train_split
    python -m training.scripts.create_train_split --help
"""

import argparse
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from app.settings import config
from training.utils import create_breed_directories

logger = logging.getLogger(__name__)


def _copy_file(src_dst: tuple[str, str]) -> str | None:
    """Copy src to dst.

    Args:
        src_dst: A ``(src, dst)`` pair of path strings.

    Returns:
        The source path string if the source file is missing, otherwise ``None``.
    """
    src, dst = src_dst
    if not Path(src).exists():
        return src
    shutil.copy2(src, dst)
    return None


def create_train_split(
    labels_csv: Path,
    cropped_images_directory: Path,
    train_directory: Path,
    id_column: str = "id",
    breed_column: str = "breed",
) -> tuple[int, int]:
    """Copy cropped images into {train_directory}/{breed}/{id}.jpg.

    Args:
        labels_csv: Path to the CSV containing image IDs and breed labels.
        cropped_images_directory: Directory containing the cropped source images.
        train_directory: Destination root; images land at {train_directory}/{breed}/{id}.jpg.
        id_column: Column name for the image ID.
        breed_column: Column name for the breed label.

    Returns:
        A ``(copied, skipped)`` tuple where ``skipped`` is the count of missing source images.
    """
    df = pd.read_csv(labels_csv)
    train_directory.mkdir(parents=True, exist_ok=True)
    create_breed_directories(train_directory, df[breed_column].unique())

    # Vectorized path construction
    src_paths = str(cropped_images_directory) + "/" + df[id_column].astype(str) + ".jpg"
    dst_paths = (
        str(train_directory)
        + "/"
        + df[breed_column].astype(str).str.cat(df[id_column].astype(str) + ".jpg", sep="/")
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
    """Parse command-line arguments, defaulting to values from config."""
    cfg = config.training.create_train_split
    cfg_crop = config.training.crop_images
    parser = argparse.ArgumentParser(
        description="Copy cropped images into per-breed subdirectories."
    )
    parser.add_argument(
        "--labels-csv",
        type=Path,
        default=Path(cfg_crop.cropped_image_labels_csv),
    )
    parser.add_argument(
        "--cropped-images-directory",
        type=Path,
        default=Path(cfg_crop.cropped_images_directory),
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
    """Entry point: parse arguments and run the train split."""
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cfg_crop = config.training.crop_images
    create_train_split(
        args.labels_csv,
        args.cropped_images_directory,
        args.train_directory,
        id_column=cfg_crop.output_id_column,
        breed_column=cfg_crop.breed_column,
    )


if __name__ == "__main__":
    main()
