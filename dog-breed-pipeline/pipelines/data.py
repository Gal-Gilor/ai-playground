"""The data pipeline: raw images and labels in, a dataset out."""

from kfp import dsl
from kfp.dsl.graph_component import GraphComponent

from pipelines.components import detect_dogs
from pipelines.components import gcs_to_fuse
from pipelines.components import unpack_bounding_boxes
from pipelines.components import use_gpu
from settings import config


def build_data_pipeline(detection_image: str, classifier_image: str) -> GraphComponent:
    """Build the data pipeline for the given step image.

    Args:
        detection_image (str): Full URI of the dog-detection image.
        classifier_image (str): Full URI of the dog-breed-classifier image.

    Returns:
        GraphComponent: The pipeline, ready to compile.
    """

    @dsl.pipeline(name="dog-breed-data")
    def data_pipeline() -> None:
        detect_task = detect_dogs(
            raw_labels_csv=gcs_to_fuse(config.cloud_storage.raw_labels_csv),
            raw_images=gcs_to_fuse(config.cloud_storage.raw_images),
        )
        use_gpu(detect_task, cpu_limit="4", memory_limit="15G").set_container_image(
            detection_image
        )

        unpack_task = unpack_bounding_boxes(labels=detect_task.outputs["labels"])
        unpack_task.set_container_image(classifier_image)

    return data_pipeline
