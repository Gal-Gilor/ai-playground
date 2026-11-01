"""The training pipeline: a dataset in, a trained model and logged metrics out."""

from kfp import dsl
from kfp.dsl.graph_component import GraphComponent

from pipelines.components import log_metrics
from pipelines.components import train_head
from pipelines.components import use_gpu
from settings import config

DEFAULTS = config.training_parameters


def build_training_pipeline(classifier_image: str) -> GraphComponent:
    """Build the training pipeline for the given classifier image.

    Args:
        classifier_image (str): Full URI of the dog-breed-classifier image.

    Returns:
        GraphComponent: The pipeline, ready to compile.
    """

    @dsl.pipeline(name="dog-breed-training")
    def training_pipeline(
        dataset_uri: str,
        head_epochs: int = DEFAULTS.head_epochs,
        head_batch_size: int = DEFAULTS.head_batch_size,
        head_learning_rate: float = DEFAULTS.head_learning_rate,
        head_weight_decay: float = DEFAULTS.head_weight_decay,
        head_hidden_units: int = DEFAULTS.head_hidden_units,
        head_dropout_rate: float = DEFAULTS.head_dropout_rate,
        head_early_stopping_patience: int = DEFAULTS.head_early_stopping_patience,
    ) -> None:
        """Train the classification head on a dataset and log its metrics.

        Args:
            dataset_uri (str): gs:// URI of the dataset folder with train/<breed>/ images.
            head_epochs (int): Maximum epochs for head training.
            head_batch_size (int): Batch size for head training.
            head_learning_rate (float): Adam learning rate for head training.
            head_weight_decay (float): Adam weight decay for head training.
            head_hidden_units (int): Units in the head's hidden layer.
            head_dropout_rate (float): Dropout rate after the head's hidden layer.
            head_early_stopping_patience (int): Epochs without validation improvement before
                head training stops.
        """
        dataset = dsl.importer(
            artifact_uri=dataset_uri, artifact_class=dsl.Dataset, reimport=False
        )

        head_task = train_head(
            dataset=dataset.output,
            epochs=head_epochs,
            batch_size=head_batch_size,
            learning_rate=head_learning_rate,
            weight_decay=head_weight_decay,
            hidden_units=head_hidden_units,
            dropout_rate=head_dropout_rate,
            early_stopping_patience=head_early_stopping_patience,
        )
        use_gpu(head_task).set_container_image(classifier_image)

        log_metrics(run=head_task.outputs["model"], prefix="head")

    return training_pipeline
