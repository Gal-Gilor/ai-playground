import ast
from pathlib import Path

import pandas as pd


def get_image_path(images_dir: Path, image_id: str) -> Path:
    """Build the path to a JPEG image given its ID."""
    return images_dir / f"{image_id}.jpg"


def load_labels(path: Path) -> pd.DataFrame:
    """Read labels CSV and parse dog_bounding_boxes with ast.literal_eval.
    Handles missing values (empty list fallback).
    """
    df = pd.read_csv(path)
    df["dog_bounding_boxes"] = df["dog_bounding_boxes"].apply(
        lambda x: ast.literal_eval(x) if pd.notna(x) else []
    )
    return df
