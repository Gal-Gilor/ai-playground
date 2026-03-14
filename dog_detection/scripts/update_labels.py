import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from ultralytics import YOLO

from src.settings import config
from src.settings import model
from src.utils import _extract_class_bounding_boxes
from src.utils import _get_class_mapping
from src.utils import create_batches
from src.utils import get_device_name
from src.utils import get_image_path


def _dog_detection_record(image_id: str, dog_bounding_boxes: list[list[float]]) -> dict:
    """Build a detection record for a single image.

    Args:
        image_id (str): The image identifier.
        dog_bounding_boxes (list[list[float]]): Bounding boxes for detected dogs.

    Returns:
        dict: Detection record with id, single_dog, multiple_dogs, and
            dog_bounding_boxes fields.
    """
    dog_count = len(dog_bounding_boxes)
    return {
        "id": image_id,
        "single_dog": dog_count == 1,
        "multiple_dogs": dog_count > 1,
        "dog_bounding_boxes": json.dumps(dog_bounding_boxes),
    }


def process_single_image(
    image_id: str,
    images_dir: Path,
    yolo_model: YOLO,
    class_mapping: dict[int, str],
    device: str,
) -> dict:
    """Run YOLO inference on a single image and return its detection record.

    Args:
        image_id (str): The image identifier.
        images_dir (Path): Directory containing the image files.
        yolo_model (YOLO): Loaded YOLO model instance.
        class_mapping (dict[int, str]): A class IDs to class names mapping.
        device (str): Device string to run inference on (e.g. "cuda:0").

    Returns:
        dict: Detection record for the image.
    """
    dog_id = next(k for k, v in class_mapping.items() if v == "dog")
    yolo_result = yolo_model.predict(
        str(get_image_path(images_dir, image_id)), device=device, verbose=False
    )[0]
    dog_bounding_boxes = _extract_class_bounding_boxes(yolo_result, dog_id)
    return _dog_detection_record(image_id, dog_bounding_boxes)


def load_checkpoint(path: Path) -> dict[str, dict]:
    """Load previously completed detections from a JSONL checkpoint file.

    Args:
        path (Path): Path to the checkpoint file.

    Returns:
        dict[str, dict]: Mapping of image ID to its detection record.
    """
    if not path.exists():
        return {}
    with path.open() as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {str(row["id"]): row for row in rows}


def append_checkpoint(path: Path, detection: dict) -> None:
    """Append a single detection record to a JSONL checkpoint file.

    Args:
        path (Path): Path to the checkpoint file.
        detection (dict): Detection record to append.
    """
    with path.open("a") as f:
        f.write(json.dumps(detection) + "\n")


def run_inference(
    image_ids: list[str],
    images_dir: Path,
    yolo_model: YOLO,
    class_mapping: dict[int, str],
    device: str,
    batch_size: int = 4,
    checkpoint_path: Path = Path(".yolo_checkpoint.jsonl"),
) -> list[dict]:
    """Run YOLO inference over a list of images, resuming from checkpoint if available.

    Args:
        image_ids (list[str]): Image identifiers to process.
        images_dir (Path): Directory containing the image files.
        yolo_model (YOLO): Loaded YOLO model instance.
        class_mapping (dict[int, str]): A mapping from class IDs to class names.
        device (str): Device string to run inference on (e.g. "cuda:0").
        batch_size (int): Number of images per inference batch. Defaults to 32.
        checkpoint_path (Path): Path to the JSONL checkpoint file.
            Defaults to ".yolo_checkpoint.jsonl".

    Returns:
        list[dict]: Detection records for all images.
    """
    completed = load_checkpoint(checkpoint_path)
    pending_ids = [image_id for image_id in image_ids if str(image_id) not in completed]

    if completed:
        print(f"Resuming: {len(completed)} done, {len(pending_ids)} remaining.")

    dog_id = next(k for k, v in class_mapping.items() if v == "dog")

    with tqdm(total=len(pending_ids), unit="img") as pbar:
        for batch_ids in create_batches(pending_ids, batch_size):
            batch_paths = [str(get_image_path(images_dir, image_id)) for image_id in batch_ids]
            for image_id, yolo_result in zip(
                batch_ids,
                yolo_model.predict(batch_paths, device=device, stream=True, verbose=False),
            ):
                dog_bounding_boxes = _extract_class_bounding_boxes(yolo_result, dog_id)
                detection = _dog_detection_record(image_id, dog_bounding_boxes)
                append_checkpoint(checkpoint_path, detection)
                completed[str(image_id)] = detection
                pbar.update(1)

    return list(completed.values())


def update_labels(
    df: pd.DataFrame,
    detections: list[dict],
    labels_path: Path,
) -> None:
    """Join detection results onto the labels DataFrame and write to CSV.

    Args:
        df (pd.DataFrame): Original labels DataFrame with an "id" column.
        detections (list[dict]): Detection records to join in.
        labels_path (Path): Path to write the updated CSV.
    """
    detections_df = pd.DataFrame(detections).set_index("id")
    updated_df = df.join(detections_df, on="id")
    updated_df.to_csv(labels_path, index=False)


def main() -> None:
    """Run the full dog-detection pipeline and update the labels CSV."""
    device = get_device_name()
    images_dir = Path(config["path-to-images"])
    labels_path = Path(config["path-to-labels"])
    checkpoint_path = labels_path.with_suffix(".checkpoint.jsonl")

    df = pd.read_csv(labels_path)
    class_mapping = _get_class_mapping(config)

    detections = run_inference(
        list(df["id"].astype(str)),
        images_dir,
        model,
        class_mapping,
        device,
        checkpoint_path=checkpoint_path,
    )
    update_labels(df, detections, labels_path)
    checkpoint_path.unlink(missing_ok=True)
    print(f"Done. Updated {labels_path} ({len(df)} rows).")


if __name__ == "__main__":
    main()
