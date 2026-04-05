from pydantic import BaseModel
from pydantic import Field


class AppConfig(BaseModel):
    model_weights: str = Field(description="Path to the .pth checkpoint used for inference")


class UnpackBoundingBoxesConfig(BaseModel):
    source_labels_csv: str = Field(
        description="CSV mapping image IDs to breeds and bounding boxes"
    )
    bounding_boxes_column: str = Field(
        description="Name of the column containing bounding boxes"
    )


class CropImagesConfig(BaseModel):
    raw_images_directory: str = Field(
        description="Directory containing raw source JPEG images"
    )
    cropped_images_directory: str = Field(
        description="Directory where cropped dog images are saved"
    )
    cropped_image_labels_csv: str = Field(
        description="CSV with unique_id (cropped image filename) and breed for each crop"
    )
    resize: tuple[int, int] | None = Field(
        default=None,
        description="Resize each crop to (width, height) after cropping. None = no resizing.",
    )
    source_id_column: str = Field(
        default="id", description="Column name for the source image ID"
    )
    breed_column: str = Field(default="breed", description="Column name for the breed label")
    bounding_boxes_column: str = Field(
        default="dog_bounding_boxes",
        description="Column name for the bounding boxes list",
    )
    crop_id_column: str = Field(
        default="unique_id",
        description="Column name for the pre-assigned crop UUID from the exploded labels",
    )
    output_id_column: str = Field(
        default="id",
        description="Column name for the crop UUID in the output labels CSV",
    )


class CreateTrainSplitConfig(BaseModel):
    train_directory: str = Field(
        description="Output root; images are written to {train_directory}/{breed}/{id}.jpg"
    )
    visible_labels_csv: str | None = Field(
        default=None,
        description="CSV with a visibility column (stage 4 output). None = copy all images.",
    )
    visible_column: str = Field(
        default="is_visible",
        description="Column name in visible_labels_csv that holds the boolean visibility flag.",  # noqa: E501
    )


class CreateTestSplitConfig(BaseModel):
    test_size: float = Field(
        default=0.25,
        description="Fraction of each breed's images to move into the test split.",
    )


class BaseTrainingConfig(BaseModel):
    batch_size: int = 32
    weight_decay: float = 1e-4
    label_smoothing: float = 0.1
    val_split: float = 0.1
    lr_patience: int = 2
    lr_factor: float = 0.5
    lr_min_lr: float = 1e-7
    normalize_mean: list[float] = [0.485, 0.456, 0.406]
    normalize_std: list[float] = [0.229, 0.224, 0.225]
    random_horizontal_flip_prob: float = 0.5
    random_rotation_degrees: int = 15
    color_jitter_brightness: float = 0.2
    color_jitter_contrast: float = 0.2
    color_jitter_saturation: float = 0.2
    color_jitter_hue: float = 0.1
    center_crop_size: int = Field(
        default=300, description="Center crop size applied before training transforms"
    )


class TrainClassificationHeadConfig(BaseTrainingConfig):
    train_directory: str
    output_directory: str
    epochs: int = 10
    learning_rate: float = 1e-3
    early_stopping_patience: int = 3
    head_hidden_units: int = 512
    head_dropout_rate: float = 0.3


class FinetuneBackboneConfig(BaseTrainingConfig):
    checkpoint_path: str
    train_directory: str
    output_directory: str
    num_unfrozen_blocks: int = Field(
        default=1,
        description="Number of trailing model.features blocks to unfreeze for fine-tuning",
    )
    epochs: int = 20
    learning_rate: float = 1e-3
    momentum: float = 0.9
    lr_min_lr: float = 1e-6
    early_stopping_patience: int = 5


class FilterVisibleDogsConfig(BaseModel):
    cropped_images_directory: str = Field(description="Directory of 380×380 cropped JPEGs")
    cropped_image_labels_csv: str = Field(
        description="CSV with id and breed columns (stage 2 output)"
    )
    output_csv: str = Field(description="Output CSV: id, breed, is_visible")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    rate_limit: float = Field(
        default=10.0, description="Max requests per second (AsyncLimiter)"
    )
    max_retries: int = Field(default=5, description="Retry attempts on transient API errors")


class TrainingConfig(BaseModel):
    exploded_labels_csv: str = Field(
        description="Pipeline handoff CSV: output of unpack_bounding_boxes, input to crop_images"  # noqa: E501
    )
    unpack_bounding_boxes: UnpackBoundingBoxesConfig
    crop_images: CropImagesConfig
    create_train_split: CreateTrainSplitConfig
    create_test_split: CreateTestSplitConfig = CreateTestSplitConfig()
    train_classification_head: TrainClassificationHeadConfig
    filter_visible_dogs: FilterVisibleDogsConfig | None = None
    finetune_backbone: FinetuneBackboneConfig | None = None


class Config(BaseModel):
    app: AppConfig
    training: TrainingConfig
