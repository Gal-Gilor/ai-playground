from pydantic import BaseModel
from pydantic import Field


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


class OrganizeDatasetConfig(BaseModel):
    cropped_image_labels_csv: str = Field(
        description="CSV mapping cropped image IDs to breeds"
    )
    cropped_images_directory: str = Field(
        description="Directory containing flat cropped JPEG images"
    )
    train_directory: str = Field(
        description="Output root; images are written to {train_directory}/{breed}/{id}.jpg"
    )


class TrainingConfig(BaseModel):
    exploded_labels_csv: str = Field(
        description="Pipeline handoff CSV: output of unpack_bounding_boxes, input to crop_images"  # noqa: E501
    )
    unpack_bounding_boxes: UnpackBoundingBoxesConfig
    crop_images: CropImagesConfig
    organize_dataset: OrganizeDatasetConfig


class Config(BaseModel):
    training: TrainingConfig
