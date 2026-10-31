from pydantic import BaseModel
from pydantic import Field


class VertexAIConfig(BaseModel):
    project: str = Field(description="Google Cloud project that runs the pipelines")
    region: str = Field(description="Region for Vertex AI Pipelines and Cloud Build")
    service_account: str = Field(description="Service account the pipeline runs as")
    artifact_registry: str = Field(
        description="Artifact Registry repository path that holds the step images"
    )
    accelerator_type: str = Field(description="GPU type for GPU steps")
    accelerator_count: int = Field(description="Number of GPUs for GPU steps")


class CloudStorageConfig(BaseModel):
    location: str = Field(description="Location of the private bucket")
    private_bucket: str = Field(description="Bucket for pipeline outputs")
    pipeline_root: str = Field(description="gs:// root where KFP stores step artifacts")
    raw_labels_csv: str = Field(description="gs:// path to the raw labels CSV")
    raw_images: str = Field(description="gs:// folder containing the raw JPEG images")


class GeminiConfig(BaseModel):
    model: str = Field(description="Gemini model name for the visibility filter")
    location: str = Field(description="Gemini API location")
    rate_limit: float = Field(description="Max Gemini requests per minute")
    max_retries: int = Field(description="Attempts per Gemini request, including the first")
    passes: int = Field(description="Passes over the crops; later ones retry 429 failures")


class SplitConfig(BaseModel):
    test_size: float = Field(description="Fraction of each breed's crops moved to test/")
    seed: int = Field(description="Seed for choosing which crops move to test/")


class Config(BaseModel):
    vertex_ai: VertexAIConfig
    cloud_storage: CloudStorageConfig
    gemini: GeminiConfig
    split: SplitConfig
