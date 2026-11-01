"""Pydantic models that validate the pipeline `config.toml`."""

from pydantic import BaseModel
from pydantic import Field


class VertexAIConfig(BaseModel):
    """Settings from the `[vertex_ai]` section."""

    project: str = Field(description="Google Cloud project that runs the pipelines")
    region: str = Field(description="Region for Vertex AI Pipelines and Cloud Build")
    service_account: str = Field(description="Service account the pipeline runs as")
    artifact_registry: str = Field(
        description="Artifact Registry repository path that holds the step images"
    )
    accelerator_type: str = Field(description="GPU type for GPU steps")
    accelerator_count: int = Field(description="Number of GPUs for GPU steps")
    experiment: str = Field(description="Vertex AI experiment that records training runs")


class CloudStorageConfig(BaseModel):
    """Settings from the `[cloud_storage]` section."""

    location: str = Field(description="Location of the private bucket")
    private_bucket: str = Field(description="Bucket for pipeline outputs")
    pipeline_root: str = Field(description="gs:// root where KFP stores step artifacts")
    raw_labels_csv: str = Field(description="gs:// path to the raw labels CSV")
    raw_images: str = Field(description="gs:// folder containing the raw JPEG images")


class GeminiConfig(BaseModel):
    """Settings from the `[gemini]` section."""

    model: str = Field(description="Gemini model name for the visibility filter")
    location: str = Field(description="Gemini API location")
    rate_limit: float = Field(description="Max Gemini requests per minute")
    max_retries: int = Field(description="Attempts per Gemini request, including the first")
    passes: int = Field(description="Passes over the crops; later ones retry 429 failures")


class SplitConfig(BaseModel):
    """Settings from the `[split]` section."""

    test_size: float = Field(description="Fraction of each breed's crops moved to test/")
    seed: int = Field(description="Seed for choosing which crops move to test/")


class TrainingParametersConfig(BaseModel):
    """Settings from the `[training_parameters]` section."""

    head_epochs: int = Field(description="Maximum epochs for head training")
    head_batch_size: int = Field(description="Batch size for head training")
    head_learning_rate: float = Field(description="Adam learning rate for head training")
    head_weight_decay: float = Field(description="Adam weight decay for head training")
    head_hidden_units: int = Field(description="Units in the head's hidden layer")
    head_dropout_rate: float = Field(description="Dropout rate after the head's hidden layer")
    head_early_stopping_patience: int = Field(
        description="Epochs without validation improvement before head training stops"
    )


class Config(BaseModel):
    """Root model for the whole `config.toml` file."""

    vertex_ai: VertexAIConfig
    cloud_storage: CloudStorageConfig
    gemini: GeminiConfig
    split: SplitConfig
    training_parameters: TrainingParametersConfig
