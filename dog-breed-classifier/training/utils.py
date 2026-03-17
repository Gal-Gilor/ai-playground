import ast
import logging
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
import torch

logger = logging.getLogger(__name__)


def get_device() -> torch.device:
    """Return the best available device, preferring CUDA over CPU.

    Returns:
        torch.device: ``cuda:0`` if a CUDA-capable GPU is available, otherwise ``cpu``.
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA confirmed: {device_name}")
        return torch.device("cuda:0")
    logger.info("No CUDA GPU found — using CPU")
    return torch.device("cpu")


def get_image_path(images_dir: Path, image_id: str, extension: str = ".jpg") -> Path:
    """Build the path to an image given its ID.

    Args:
        images_dir: Directory containing the images.
        image_id: Unique identifier for the image.
        extension: File extension including the dot.

    Returns:
        Full path to the image file.
    """
    return images_dir / f"{image_id}{extension}"


def load_labels(path: Path, bounding_boxes_column: str = "dog_bounding_boxes") -> pd.DataFrame:
    """Read labels CSV and parse the bounding boxes column with ast.literal_eval.

    Handles missing values (empty list fallback).

    Args:
        path: Path to the labels CSV file.
        bounding_boxes_column: Name of the column containing bounding box data.

    Returns:
        DataFrame with the bounding boxes column parsed into Python lists.
    """
    df = pd.read_csv(path)
    df[bounding_boxes_column] = df[bounding_boxes_column].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    return df


def create_breed_directories(directory: Path, breeds: Iterable[str]) -> None:
    """Create one subdirectory per breed under `directory`.

    Args:
        directory: Parent directory under which breed subdirectories are created.
        breeds: Iterable of breed names to create as subdirectories.
    """
    for breed in breeds:
        (directory / breed).mkdir(parents=True, exist_ok=True)
