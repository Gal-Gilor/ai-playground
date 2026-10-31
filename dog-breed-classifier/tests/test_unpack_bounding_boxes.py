import pandas as pd

from scripts.unpack_bounding_boxes import unpack_bounding_boxes
from settings import config


def labels(rows: dict[str, list]) -> pd.DataFrame:
    column = config.training.unpack_bounding_boxes.bounding_boxes_column
    return pd.DataFrame({"id": list(rows), column: list(rows.values())})


def test_crop_ids_combine_source_id_and_box_index() -> None:
    """Each crop ID is the source image ID plus the box index within that image."""
    df = unpack_bounding_boxes(labels({"a": [[1], [2]], "b": [[3]]}))
    assert df[config.training.crop_images.crop_id_column].tolist() == ["a_0", "a_1", "b_0"]


def test_image_without_boxes_gets_one_row() -> None:
    """An image with an empty box list still produces one row."""
    df = unpack_bounding_boxes(labels({"c": []}))
    assert df[config.training.crop_images.crop_id_column].tolist() == ["c_0"]
