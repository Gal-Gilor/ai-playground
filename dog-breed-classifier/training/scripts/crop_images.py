"""Crop dog images from raw source images using bounding box annotations.

For each row in the exploded labels CSV, crops the dog(s) from the source image using the
annotated bounding boxes. Each crop is saved as a new JPEG with a UUID4 filename.
A new labels CSV is written mapping each crop ID back to its breed.

Usage (from project root):
    python -m training.scripts.crop_images
    python -m training.scripts.crop_images --help
"""

import argparse
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from PIL import Image
from pydantic import BaseModel
from tqdm import tqdm

from app.settings import config
from training.utils import get_image_path
from training.utils import load_labels

logger = logging.getLogger(__name__)


class BoundingBox(BaseModel):
    """Bounding box in pixel coordinates."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @classmethod
    def from_raw(cls, raw: list[float], image_width: int, image_height: int) -> "BoundingBox":
        """Build a BoundingBox from raw float coordinates, clamped to image bounds.

        Args:
            raw: Four floats [x_min, y_min, x_max, y_max].
            image_width: Width of the source image in pixels.
            image_height: Height of the source image in pixels.

        Returns:
            BoundingBox with coordinates rounded and clamped to [0, image_width/height].
        """
        x_min = max(0, min(round(raw[0]), image_width))
        y_min = max(0, min(round(raw[1]), image_height))
        x_max = max(0, min(round(raw[2]), image_width))
        y_max = max(0, min(round(raw[3]), image_height))
        return cls(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)

    @property
    def is_valid(self) -> bool:
        """Return True if the box has positive area."""
        return self.x_max > self.x_min and self.y_max > self.y_min


def crop_image(image: Image.Image, bounding_box: BoundingBox) -> Image.Image:
    """Return a cropped copy of image defined by bounding_box.

    Args:
        image: The source image to crop.
        bounding_box: Pixel coordinates of the crop region.

    Returns:
        A new Image containing only the cropped region.
    """
    return image.crop(
        (bounding_box.x_min, bounding_box.y_min, bounding_box.x_max, bounding_box.y_max)
    )


def process_row(
    row: pd.Series,
    images_directory: Path,
    output_directory: Path,
    resize: tuple[int, int] | None,
    source_id_column: str,
    breed_column: str,
    bounding_boxes_column: str,
    crop_id_column: str,
    output_id_column: str,
) -> list[dict]:
    """Open the source image and save one crop per bounding box.

    Args:
        row: A single row from the labels DataFrame.
        images_directory: Directory containing the source JPEG images.
        output_directory: Directory where cropped images will be saved.
        resize: (width, height) to resize each crop. None skips resizing.
        source_id_column: Column name for the source image ID.
        breed_column: Column name for the breed label.
        bounding_boxes_column: Column name for the bounding boxes list.
        crop_id_column: Column name for the pre-assigned crop UUID.
        output_id_column: Column name for the crop UUID in the output records.

    Returns:
        List of dicts with one entry per saved crop.
    """
    source_id: str = row[source_id_column]
    breed: str = row[breed_column]
    bounding_boxes: list[list[float]] = row[bounding_boxes_column]

    # Flat list means one box per exploded row; wrap it so iteration is uniform.
    if bounding_boxes and not isinstance(bounding_boxes[0], list):
        bounding_boxes = [bounding_boxes]

    if not bounding_boxes:
        logger.warning("Skipping %s (%s): no bounding boxes", source_id, breed)
        return []

    image_path = get_image_path(images_directory, source_id)
    if not image_path.exists():
        logger.warning("Skipping %s: image file not found at %s", source_id, image_path)
        return []

    results: list[dict] = []

    with Image.open(image_path) as image:
        image_width, image_height = image.size

        for i, raw_bounding_box in enumerate(bounding_boxes):
            bounding_box = BoundingBox.from_raw(raw_bounding_box, image_width, image_height)

            if not bounding_box.is_valid:
                logger.warning(
                    "Skipping box %d for %s: degenerate bbox %s", i, source_id, bounding_box
                )
                continue

            crop = crop_image(image, bounding_box)
            if resize:
                crop = crop.resize(resize, Image.LANCZOS)
            crop_id = row[crop_id_column]
            crop.save(output_directory / f"{crop_id}.jpg", format="JPEG")

            results.append({output_id_column: crop_id, breed_column: breed})

    return results


def crop_images(
    df: pd.DataFrame,
    images_directory: Path,
    output_directory: Path,
    resize: tuple[int, int] | None,
) -> list[dict]:
    """Iterate all label rows and extract crops for each annotated bounding box.

    Args:
        df: Labels DataFrame with parsed dog_bounding_boxes column.
        images_directory: Directory containing source JPEG images.
        output_directory: Directory where cropped images will be saved.
        resize: Optional (width, height) to resize each crop after cropping.

    Returns:
        List of crop records (id, breed).
    """
    output_directory.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    skipped = 0

    source_id_column = config.training.crop_images.source_id_column
    breed_column = config.training.crop_images.breed_column
    bounding_boxes_column = config.training.crop_images.bounding_boxes_column
    crop_id_column = config.training.crop_images.crop_id_column
    output_id_column = config.training.crop_images.output_id_column

    rows = [row for _, row in df.iterrows()]
    with ProcessPoolExecutor() as executor:
        for records in tqdm(
            executor.map(
                process_row,
                rows,
                [images_directory] * len(rows),
                [output_directory] * len(rows),
                [resize] * len(rows),
                [source_id_column] * len(rows),
                [breed_column] * len(rows),
                [bounding_boxes_column] * len(rows),
                [crop_id_column] * len(rows),
                [output_id_column] * len(rows),
            ),
            total=len(rows),
            desc="Cropping images",
        ):
            if records:
                all_records.extend(records)
            else:
                skipped += 1

    logger.info("Done. Crops saved: %d | Source rows skipped: %d", len(all_records), skipped)
    return all_records


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Crop dog images from raw source images using bounding box annotations."
    )
    parser.add_argument(
        "--images-directory",
        type=Path,
        default=Path(config.training.crop_images.raw_images_directory),
        help=f"Directory containing source JPEG images (default: {config.training.crop_images.raw_images_directory})",  # noqa: E501
    )
    parser.add_argument(
        "--labels-csv",
        type=Path,
        default=Path(config.training.exploded_labels_csv),
        help=f"Path to exploded labels CSV (default: {config.training.exploded_labels_csv})",  # noqa: E501
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(config.training.crop_images.cropped_images_directory),
        help=f"Output directory for cropped images (default: {config.training.crop_images.cropped_images_directory})",  # noqa: E501
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(config.training.crop_images.cropped_image_labels_csv),
        help=f"Output path for the new labels CSV (default: {config.training.crop_images.cropped_image_labels_csv})",  # noqa: E501
    )
    parser.add_argument(
        "--resize",
        type=int,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        default=list(config.training.crop_images.resize)
        if config.training.crop_images.resize
        else None,
        help="Resize each crop to WIDTH HEIGHT after cropping (default: no resizing)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and run the image cropping pipeline."""
    args = parse_args()

    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    resize: tuple[int, int] | None = tuple(args.resize) if args.resize else None

    df = load_labels(args.labels_csv)
    records = crop_images(df, args.images_directory, args.output_directory, resize)

    output_id_column = config.training.crop_images.output_id_column
    breed_column = config.training.crop_images.breed_column
    crops_df = pd.DataFrame(records, columns=[output_id_column, breed_column])
    crops_df.to_csv(args.output_csv, index=False)
    logger.info("Wrote %d rows to %s", len(crops_df), args.output_csv)


if __name__ == "__main__":
    main()
