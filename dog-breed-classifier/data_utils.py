"""Helpers for locating images and reading the labels CSV."""

import ast
import logging
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def get_image_path(images_dir: Path, image_id: str, extension: str = ".jpg") -> Path:
    """Build the path to an image given its ID.

    Args:
        images_dir (Path): Directory containing the images.
        image_id (str): Unique identifier for the image.
        extension (str): File extension including the dot.

    Returns:
        Path: Full path to the image file.
    """
    return images_dir / f"{image_id}{extension}"


def load_labels(path: Path, bounding_boxes_column: str = "dog_bounding_boxes") -> pd.DataFrame:
    """Read labels CSV and parse the bounding boxes column with ast.literal_eval.

    Handles missing values (empty list fallback).

    Args:
        path (Path): Path to the labels CSV file.
        bounding_boxes_column (str): Name of the column containing bounding box data.

    Returns:
        pd.DataFrame: DataFrame with the bounding boxes column parsed into Python lists.
    """
    df = pd.read_csv(path)
    df[bounding_boxes_column] = df[bounding_boxes_column].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    return df


def create_breed_directories(directory: Path, breeds: Iterable[str]) -> None:
    """Create one subdirectory per breed under `directory`.

    Args:
        directory (Path): Parent directory under which breed subdirectories are created.
        breeds (Iterable[str]): Iterable of breed names to create as subdirectories.
    """
    for breed in breeds:
        (directory / breed).mkdir(parents=True, exist_ok=True)
