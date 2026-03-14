from __future__ import annotations

import itertools
import json
import logging
from pathlib import Path
from typing import Any
from typing import AsyncIterator
from typing import Iterable
from typing import Iterator
from typing import TypeVar

import aiofiles
import torch
import ultralytics

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_device_name() -> str:
    """Return the CUDA device string after confirming GPU availability.

    Raises:
        RuntimeError: If no CUDA-capable GPU is found.

    Returns:
        str: The CUDA device string (e.g. "cuda:0").
    """
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available. Cannot proceed.")
    print(f"CUDA confirmed: {torch.cuda.get_device_name(0)}")
    return "cuda:0"


def get_image_path(images_dir: Path, image_id: str) -> Path:
    """Build the path to a JPEG image given its ID.

    Args:
        images_dir (Path): Directory containing the image files.
        image_id (str): Image identifier used as the filename stem.

    Returns:
        Path: Full path to the image file (<images_dir>/<image_id>.jpg).
    """
    return images_dir / f"{image_id}.jpg"


def _extract_bounding_box(
    yolo_result: ultralytics.engine.results.Results,
    index: int,
) -> list[float]:
    """Extract a single bounding box from a YOLO result by index.

    Args:
        yolo_result (ultralytics.engine.results.Results): A YOLO model result object.
        index (int): Index of the bounding box to extract.

    Returns:
        list[float]: Bounding box coordinates in [x1, y1, x2, y2] format.
    """
    return yolo_result.boxes.xyxy[index].tolist()


def _extract_class_bounding_boxes(
    yolo_result: ultralytics.engine.results.Results,
    class_id: int,
) -> list[list[float]]:
    """Extract all bounding boxes for a given class from a YOLO result.

    Args:
        yolo_result (ultralytics.engine.results.Results): A YOLO model result object.
        class_id (int): The class ID to filter detections by.

    Returns:
        list[list[float]]: List of bounding boxes in [x1, y1, x2, y2] format.
    """
    detected_class_ids = yolo_result.boxes.cls.int().tolist()
    return [
        _extract_bounding_box(yolo_result, i)
        for i, cid in enumerate(detected_class_ids)
        if cid == class_id
    ]


def _get_class_mapping(
    config: dict,
    class_name_key: str = "name",
    class_id_key: str = "id",
    class_mapping_key: str = "class-detection-ids",
) -> dict[int, str]:
    """Build a mapping from class IDs to class names.

    Args:
        config (dict): Configuration dict with class objects listed under `class_mapping_key`.
        class_name_key (str): Key for the class name within each class object.
            Defaults to "name".
        class_id_key (str): Key for the class ID within each class object.
            Defaults to "id".
        class_mapping_key (str): `config` key for the list of class objects.
            Defaults to "class-detection-ids".

    Returns:
        dict[int, str]: A mapping from class IDs to class names.
    """
    return {c[class_id_key]: c[class_name_key] for c in config.get(class_mapping_key, {})}


def _single_dog_no_person_image(
    yolo_result: ultralytics.engine.results.Results,
    class_mapping: dict[int, str],
) -> bool:
    """Check if the detection result contains at most one dog and no person.

    Args:
        yolo_result (ultralytics.engine.results.Results): A YOLO model result object.
        class_mapping (dict[int, str]): A mapping from class IDs to class names.

    Returns:
        bool: True if the image contains at most one dog and no person, False otherwise.
    """

    detections = [class_mapping[cls.item()] for cls in yolo_result.boxes.cls.int()]

    person_detected = "person" in detections
    number_of_dogs = detections.count("dog")

    return (number_of_dogs <= 1) and not person_detected


def create_batches(iterable: Iterable[T], batch_size: int = 20) -> Iterator[tuple[T, ...]]:
    """Break an iterable into fixed-size chunks.

    Args:
        iterable: The iterable to batch.
        batch_size: Size of each batch. Must be >= 1. Defaults to 20.

    Returns:
        Iterator yielding tuples of items from the iterable.

    Raises:
        ValueError: If batch_size is less than 1.
        TypeError: If batch_size is not an integer.
    """
    if not isinstance(batch_size, int):
        raise TypeError(f"batch_size must be an integer, got {type(batch_size).__name__}")
    if batch_size < 1:
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")
    it = iter(iterable)
    chunk = tuple(itertools.islice(it, batch_size))
    while chunk:
        yield chunk
        chunk = tuple(itertools.islice(it, batch_size))


def _any_dog_no_person_image(
    yolo_result: ultralytics.engine.results.Results,
    class_mapping: dict[int, str],
) -> bool:
    """Check if the detection result contains at least one dog and no person.

    Args:
        yolo_result (ultralytics.engine.results.Results): A YOLO model result object.
        class_mapping (dict[int, str]): A mapping from class IDs to class names.

    Returns:
        bool: True if the image contains dogs and no persons, False otherwise.
    """

    detections = [class_mapping[cls.item()] for cls in yolo_result.boxes.cls.int()]

    person_detected = "person" in detections
    dog_detected = "dog" in detections

    return dog_detected and not person_detected


async def read_chunks_in_batches(
    file_path: str | Path, batch_size: int = 10, strict: bool = False
) -> AsyncIterator[list[dict[str, Any]]]:
    """Read JSONL file and yield batches of chunk objects in a streaming manner.

    This function processes the file line-by-line without loading the entire
    file into memory, making it suitable for large files.

    Args:
        file_path: Path to the JSONL file containing chunk data.
        batch_size: Number of chunks per batch. Must be >= 1. Defaults to 10.
        strict: If True, raise exception on JSON parse errors. If False, log
            and skip invalid lines. Defaults to False.

    Yields:
        Lists of chunk dictionaries with keys: section_header, section_text,
        header_level, metadata.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If batch_size is less than 1.
        json.JSONDecodeError: If strict=True and a line contains invalid JSON.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if batch_size < 1:
        raise ValueError(f"batch_size must be at least 1, got {batch_size}")

    current_batch: list[dict[str, Any]] = []
    line_number = 0

    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        async for line in f:
            line_number += 1
            line = line.strip()

            if not line:
                continue

            try:
                chunk = json.loads(line)
                current_batch.append(chunk)

                if len(current_batch) >= batch_size:
                    yield current_batch
                    current_batch = []

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse JSON at line {line_number} in {file_path}: {e}"

                if strict:
                    raise json.JSONDecodeError(error_msg, e.doc, e.pos) from e

                logger.error(error_msg)
                continue

    if current_batch:
        yield current_batch
