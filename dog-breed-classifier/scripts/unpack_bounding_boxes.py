"""Explode a labels CSV to one row per bounding box and assign each row a crop ID.

Usage (from project root):
    python -m scripts.unpack_bounding_boxes
    python -m scripts.unpack_bounding_boxes --help
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from data_utils import load_labels
from settings import config

logger = logging.getLogger(__name__)


def unpack_bounding_boxes(df: pd.DataFrame) -> pd.DataFrame:
    """Explode df to one row per bounding box and prepend a crop_id column.

    Crop IDs are `<source image id>_<box index>`, with the index counting from 0 within each
    image, so reruns give the same IDs.

    Args:
        df (pd.DataFrame): Labels DataFrame with one row per source image and a list of
            bounding boxes per row.

    Returns:
        pd.DataFrame: Exploded DataFrame with one row per bounding box and a new crop_id column
            prepended.
    """
    bounding_boxes_column = config.training.unpack_bounding_boxes.bounding_boxes_column
    crop_id_column = config.training.crop_images.crop_id_column
    source_id_column = config.training.crop_images.source_id_column
    df = df.explode(bounding_boxes_column, ignore_index=True)
    box_index = df.groupby(source_id_column).cumcount()
    df.insert(
        0, crop_id_column, df[source_id_column].astype(str) + "_" + box_index.astype(str)
    )
    return df


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Unpack bounding boxes to one row per bbox.")
    parser.add_argument(
        "--source-labels-csv",
        type=Path,
        default=Path(config.training.unpack_bounding_boxes.source_labels_csv),
    )
    parser.add_argument(
        "--exploded-csv",
        type=Path,
        default=Path(config.training.exploded_labels_csv),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and run the bounding box unpacking pipeline."""
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level), format="%(levelname)s: %(message)s"
    )

    df = load_labels(args.source_labels_csv)
    logger.info(f"Loaded {len(df)} rows from {args.source_labels_csv}")

    df = unpack_bounding_boxes(df)

    args.exploded_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.exploded_csv, index=False)
    logger.info(f"Wrote {len(df)} rows to {args.exploded_csv}")


if __name__ == "__main__":
    main()
