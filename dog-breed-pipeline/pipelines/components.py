"""Container components shared by the pipelines.

Each component names an untagged image. The pipeline sets the built image on each task with
`set_container_image`.
"""

from kfp import dsl
from kfp.dsl import Dataset
from kfp.dsl import Input
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
def detect_dogs(raw_labels_csv: str, raw_images: str, labels: Output[Dataset]):
    """Detect dogs with YOLO and write the labels CSV with bounding boxes.

    Args:
        raw_labels_csv (str): Mounted path to the raw labels CSV.
        raw_images (str): Mounted path to the folder of raw JPEG images.
        labels (Output[Dataset]): Output labels CSV with single_dog, multiple_dogs and
            dog_bounding_boxes.
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
def unpack_bounding_boxes(labels: Input[Dataset], exploded_labels: Output[Dataset]):
    """Explode the labels to one row per bounding box and assign each row a crop ID.

    Args:
        labels (Input[Dataset]): Labels CSV from detection, with one row per image.
        exploded_labels (Output[Dataset]): Output CSV with one row per bounding box.
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
):
    """Crop each bounding box from its raw image and resize it.

    Args:
        exploded_labels (Input[Dataset]): Labels CSV with one row per bounding box.
        raw_images (str): Mounted path to the folder of raw JPEG images.
        cropped_images (Output[Dataset]): Output folder of cropped JPEG images.
        cropped_labels (Output[Dataset]): Output CSV with the id and breed of each crop.
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
