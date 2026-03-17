"""Move a configurable fraction of training images per breed into a test split.

Usage (from project root):
    python -m training.scripts.create_test_split
    python -m training.scripts.create_test_split --help
"""

import argparse
import logging
import shutil
from math import floor
from pathlib import Path

from tqdm import tqdm

from app.settings import config

logger = logging.getLogger(__name__)


def create_test_split(train_directory: Path, test_size: float = 0.25) -> tuple[int, int]:
    """Move a fraction of each breed's images into a sibling test directory.

    Idempotent: counts images already in the test directory so repeated runs converge
    to the same split rather than moving an additional fraction each time.

    Args:
        train_directory: Directory containing per-breed subdirectories of training images.
        test_size: Target fraction of each breed's total images (train + test) to place
            in the test split. Breeds where floor(total * test_size) is zero are skipped.

    Returns:
        A ``(moved, skipped)`` tuple where ``skipped`` is the number of breeds with
        too few images to contribute any test examples.
    """
    test_directory = train_directory.parent / "test"
    test_directory.mkdir(parents=True, exist_ok=True)

    breed_dirs = sorted(p for p in train_directory.iterdir() if p.is_dir())
    moved = 0
    skipped = 0

    for breed_dir in tqdm(breed_dirs, desc="Processing breeds"):
        train_images = sorted(breed_dir.glob("*.jpg"))
        test_breed_dir = test_directory / breed_dir.name
        already_in_test = (
            len(list(test_breed_dir.glob("*.jpg"))) if test_breed_dir.exists() else 0
        )
        total = len(train_images) + already_in_test
        target = floor(total * test_size)
        n = max(0, target - already_in_test)
        if n == 0:
            if target == 0:
                logger.warning(
                    f"Skipping {breed_dir.name}: only {total} image(s), none to move"
                )
                skipped += 1
            continue

        test_breed_dir.mkdir(parents=True, exist_ok=True)
        for img in train_images[:n]:
            shutil.move(str(img), test_breed_dir / img.name)
        moved += n

    logger.info(f"Done. Moved: {moved} images | Breeds skipped: {skipped}")
    return moved, skipped


def parse_args() -> argparse.Namespace:
    cfg = config.training.create_train_split
    cfg_test = config.training.create_test_split
    parser = argparse.ArgumentParser(
        description="Move a fraction of images per breed from train/ into a sibling test/."
    )
    parser.add_argument(
        "--train-directory",
        type=Path,
        default=Path(cfg.train_directory),
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=cfg_test.test_size,
        help="Fraction of each breed's images to move to the test split.",
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
    create_test_split(args.train_directory, test_size=args.test_size)


if __name__ == "__main__":
    main()
