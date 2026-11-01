"""The data pipeline: raw images and labels in, a dataset out."""

from kfp import dsl
from kfp.dsl.graph_component import GraphComponent

from pipelines.components import crop_images
from pipelines.components import detect_dogs
from pipelines.components import filter_visible_dogs
from pipelines.components import gcs_to_fuse
from pipelines.components import split_dataset
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
        """Detect dogs in the raw images, crop and filter them, and split them into train/test.

        Takes no parameters; the inputs come from the `[cloud_storage]` config section.
        """
        raw_images = gcs_to_fuse(config.cloud_storage.raw_images)
        detect_task = detect_dogs(
            raw_labels_csv=gcs_to_fuse(config.cloud_storage.raw_labels_csv),
            raw_images=raw_images,
        )
        use_gpu(detect_task, cpu_limit="4", memory_limit="15G").set_container_image(
            detection_image
        )

        unpack_task = unpack_bounding_boxes(labels=detect_task.outputs["labels"])
        unpack_task.set_container_image(classifier_image)

        crop_task = crop_images(
            exploded_labels=unpack_task.outputs["exploded_labels"],
            raw_images=raw_images,
        )
        crop_task.set_container_image(classifier_image)

        filter_task = filter_visible_dogs(
            cropped_images=crop_task.outputs["cropped_images"],
            cropped_labels=crop_task.outputs["cropped_labels"],
        )
        filter_task.set_container_image(classifier_image)
        filter_task.set_env_variable("GOOGLE_CLOUD_PROJECT", config.vertex_ai.project)
        filter_task.set_env_variable("GOOGLE_CLOUD_LOCATION", config.gemini.location)

        split_task = split_dataset(
            cropped_images=crop_task.outputs["cropped_images"],
            cropped_labels=crop_task.outputs["cropped_labels"],
            visible_labels=filter_task.outputs["visible_labels"],
        )
        split_task.set_container_image(classifier_image)

    return data_pipeline
