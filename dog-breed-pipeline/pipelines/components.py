"""Container components shared by the pipelines.

Each component names an untagged image. The pipeline sets the built image on each task with
`set_container_image`.
"""

from kfp import dsl
from kfp.dsl import Artifact
from kfp.dsl import Dataset
from kfp.dsl import Input
from kfp.dsl import Metrics
from kfp.dsl import Model
from kfp.dsl import Output
from kfp.dsl import PipelineTask

from settings import config

GPU_CPU_LIMIT = "8"
GPU_MEMORY_LIMIT = "32G"


def gcs_to_fuse(uri: str) -> str:
    """Convert a gs:// URI to its path on the Cloud Storage FUSE mount.

    Args:
        uri (str): A URI such as `gs://bucket/path`.

    Returns:
        str: The mounted path, such as `/gcs/bucket/path`.
    """
    return f"/gcs/{uri.removeprefix('gs://')}"


def use_gpu(
    task: PipelineTask, cpu_limit: str = GPU_CPU_LIMIT, memory_limit: str = GPU_MEMORY_LIMIT
) -> PipelineTask:
    """Run a task on a GPU machine.

    Args:
        task (PipelineTask): The pipeline task to configure.
        cpu_limit (str): CPU limit; the default suits training with 4 DataLoader workers.
        memory_limit (str): Memory limit; the default suits training.

    Returns:
        PipelineTask: The same task, for chaining.
    """
    return (
        task.set_cpu_limit(cpu_limit)
        .set_memory_limit(memory_limit)
        .set_accelerator_type(config.vertex_ai.accelerator_type)
        .set_accelerator_limit(config.vertex_ai.accelerator_count)
    )


@dsl.container_component
def detect_dogs(
    raw_labels_csv: str, raw_images: str, labels: Output[Dataset]
) -> dsl.ContainerSpec:
    """Detect dogs with YOLO and write the labels CSV with bounding boxes.

    Args:
        raw_labels_csv (str): Mounted path to the raw labels CSV.
        raw_images (str): Mounted path to the folder of raw JPEG images.
        labels (Output[Dataset]): Output labels CSV with single_dog, multiple_dogs and
            dog_bounding_boxes.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    return dsl.ContainerSpec(
        image="dog-detection",
        command=["python", "scripts/update_labels.py"],
        args=[
            "--images-directory",
            raw_images,
            "--labels-csv",
            raw_labels_csv,
            "--output-csv",
            labels.path,
            "--checkpoint-path",
            "/tmp/detections.checkpoint.jsonl",
        ],
    )


@dsl.container_component
def unpack_bounding_boxes(
    labels: Input[Dataset], exploded_labels: Output[Dataset]
) -> dsl.ContainerSpec:
    """Explode the labels to one row per bounding box and assign each row a crop ID.

    Args:
        labels (Input[Dataset]): Labels CSV from detection, with one row per image.
        exploded_labels (Output[Dataset]): Output CSV with one row per bounding box.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    return dsl.ContainerSpec(
        image="dog-breed-classifier",
        command=["python", "-m", "scripts.unpack_bounding_boxes"],
        args=[
            "--source-labels-csv",
            labels.path,
            "--exploded-csv",
            exploded_labels.path,
        ],
    )


@dsl.container_component
def crop_images(
    exploded_labels: Input[Dataset],
    raw_images: str,
    cropped_images: Output[Dataset],
    cropped_labels: Output[Dataset],
) -> dsl.ContainerSpec:
    """Crop each bounding box from its raw image and resize it.

    Args:
        exploded_labels (Input[Dataset]): Labels CSV with one row per bounding box.
        raw_images (str): Mounted path to the folder of raw JPEG images.
        cropped_images (Output[Dataset]): Output folder of cropped JPEG images.
        cropped_labels (Output[Dataset]): Output CSV with the id and breed of each crop.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    return dsl.ContainerSpec(
        image="dog-breed-classifier",
        command=["python", "-m", "scripts.crop_images"],
        args=[
            "--labels-csv",
            exploded_labels.path,
            "--images-directory",
            raw_images,
            "--output-directory",
            cropped_images.path,
            "--output-csv",
            cropped_labels.path,
        ],
    )


@dsl.container_component
def filter_visible_dogs(
    cropped_images: Input[Dataset],
    cropped_labels: Input[Dataset],
    visible_labels: Output[Dataset],
) -> dsl.ContainerSpec:
    """Ask Gemini whether each crop shows a clearly visible dog.

    Args:
        cropped_images (Input[Dataset]): Folder of cropped JPEG images.
        cropped_labels (Input[Dataset]): CSV with the id and breed of each crop.
        visible_labels (Output[Dataset]): Output CSV with id, breed and is_visible.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    return dsl.ContainerSpec(
        image="dog-breed-classifier",
        command=["python", "-m", "scripts.filter_visible_dogs"],
        args=[
            "--cropped-images-directory",
            cropped_images.path,
            "--labels-csv",
            cropped_labels.path,
            "--output-csv",
            visible_labels.path,
            "--model",
            config.gemini.model,
            "--rate-limit",
            str(config.gemini.rate_limit),
            "--max-retries",
            str(config.gemini.max_retries),
            "--passes",
            str(config.gemini.passes),
        ],
    )


@dsl.container_component
def split_dataset(
    cropped_images: Input[Dataset],
    cropped_labels: Input[Dataset],
    visible_labels: Input[Dataset],
    dataset: Output[Dataset],
) -> dsl.ContainerSpec:
    """Sort the visible crops into train/<breed>/ and move a share of each breed to test/.

    Args:
        cropped_images (Input[Dataset]): Folder of cropped JPEG images.
        cropped_labels (Input[Dataset]): CSV with the id and breed of each crop.
        visible_labels (Input[Dataset]): CSV with id, breed and is_visible.
        dataset (Output[Dataset]): Output folder with train/<breed>/ and test/<breed>/.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    train_directory = f"{dataset.path}/train"
    return dsl.ContainerSpec(
        image="dog-breed-classifier",
        command=[
            "sh",
            "-c",
            f"python -m scripts.create_train_split"
            f" --labels-csv {cropped_labels.path}"
            f" --cropped-images-directory {cropped_images.path}"
            f" --visible-csv {visible_labels.path}"
            f" --train-directory {train_directory}"
            f" && python -m scripts.create_test_split"
            f" --train-directory {train_directory}"
            f" --test-size {config.split.test_size}"
            f" --seed {config.split.seed}",
        ],
    )


@dsl.container_component
def train_head(
    dataset: Input[Dataset],
    epochs: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    hidden_units: int,
    dropout_rate: float,
    early_stopping_patience: int,
    model: Output[Model],
) -> dsl.ContainerSpec:
    """Train the classification head on a frozen EfficientNet-B4 backbone.

    Args:
        dataset (Input[Dataset]): Folder with train/<breed>/ images.
        epochs (int): Maximum number of epochs.
        batch_size (int): Training batch size.
        learning_rate (float): Adam learning rate.
        weight_decay (float): Adam weight decay.
        hidden_units (int): Units in the head's hidden layer.
        dropout_rate (float): Dropout rate after the head's hidden layer.
        early_stopping_patience (int): Epochs without validation improvement before stopping.
        model (Output[Model]): Output run folder with the checkpoints, curves, params.yaml
            and metrics.json.

    Returns:
        dsl.ContainerSpec: The image, command and arguments that run the step.
    """
    return dsl.ContainerSpec(
        image="dog-breed-classifier",
        command=["python", "-m", "scripts.train_classification_head"],
        args=[
            "--train-directory",
            f"{dataset.path}/train",
            "--run-directory",
            model.path,
            "--epochs",
            epochs,
            "--batch-size",
            batch_size,
            "--learning-rate",
            learning_rate,
            "--weight-decay",
            weight_decay,
            "--head-hidden-units",
            hidden_units,
            "--head-dropout-rate",
            dropout_rate,
            "--early-stopping-patience",
            early_stopping_patience,
        ],
    )


@dsl.component(base_image="python:3.12-slim")
def log_metrics(run: Input[Artifact], prefix: str, metrics: Output[Metrics]) -> None:
    """Log the entries of a run's metrics.json as metrics, named `<prefix>_<name>`.

    Args:
        run (Input[Artifact]): Run folder that holds metrics.json.
        prefix (str): Prefix that keeps metric names from different steps distinct.
        metrics (Output[Metrics]): Output metrics artifact.
    """
    import json
    from pathlib import Path

    for name, value in json.loads((Path(run.path) / "metrics.json").read_text()).items():
        metrics.log_metric(f"{prefix}_{name}", value)
