import pandas as pd

from scripts.unpack_bounding_boxes import unpack_bounding_boxes


def test_crop_ids_combine_source_id_and_box_index() -> None:
    """Each crop ID is the source image ID plus the box index within that image."""
    df = pd.DataFrame({"id": ["a", "b"], "dog_bounding_boxes": [[[1], [2]], [[3]]]})
    assert unpack_bounding_boxes(df)["crop_id"].tolist() == ["a_0", "a_1", "b_0"]


def test_image_without_boxes_gets_one_row() -> None:
    """An image with an empty box list still produces one row."""
    df = pd.DataFrame({"id": ["c"], "dog_bounding_boxes": [[]]})
    assert unpack_bounding_boxes(df)["crop_id"].tolist() == ["c_0"]
