import json
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import torch

from src.utils import _any_dog_no_person_image
from src.utils import _extract_bounding_box
from src.utils import _extract_class_bounding_boxes
from src.utils import _get_class_mapping
from src.utils import _single_dog_no_person_image
from src.utils import create_batches
from src.utils import get_device_name
from src.utils import get_image_path
from src.utils import read_chunks_in_batches


def test_create_batches_basic():
    """Test basic batching with simple list."""
    # Arrange
    data = [1, 2, 3, 4, 5]
    batch_size = 2

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [(1, 2), (3, 4), (5,)]


def test_create_batches_exact_multiple():
    """Test batching when list length is exact multiple of batch size."""
    # Arrange
    data = [1, 2, 3, 4, 5, 6]
    batch_size = 3

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [(1, 2, 3), (4, 5, 6)]


def test_create_batches_single_batch():
    """Test when all items fit in a single batch."""
    # Arrange
    data = [1, 2, 3]
    batch_size = 5

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [(1, 2, 3)]


def test_create_batches_size_one():
    """Test batching with batch_size of 1."""
    # Arrange
    data = [1, 2, 3]
    batch_size = 1

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [(1,), (2,), (3,)]


def test_create_batches_empty_iterable():
    """Test batching with empty iterable."""
    # Arrange
    data = []
    batch_size = 3

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == []


def test_create_batches_default_size():
    """Test batching with default batch_size (20)."""
    # Arrange
    data = list(range(50))

    # Act
    result = list(create_batches(data))

    # Assert
    assert len(result) == 3
    assert len(result[0]) == 20
    assert len(result[1]) == 20
    assert len(result[2]) == 10


def test_create_batches_generator_input():
    """Test batching with generator as input."""
    # Arrange
    data = (x for x in range(5))
    batch_size = 2

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [(0, 1), (2, 3), (4,)]


def test_create_batches_string_iterable():
    """Test batching with string as iterable."""
    # Arrange
    data = "abcdef"
    batch_size = 2

    # Act
    result = list(create_batches(data, batch_size))

    # Assert
    assert result == [("a", "b"), ("c", "d"), ("e", "f")]


def test_create_batches_invalid_size_zero():
    """Test that batch_size of 0 raises ValueError."""
    # Arrange
    data = [1, 2, 3]
    batch_size = 0

    # Act & Assert
    with pytest.raises(ValueError, match="batch_size must be at least 1"):
        list(create_batches(data, batch_size))


def test_create_batches_invalid_size_negative():
    """Test that negative batch_size raises ValueError."""
    # Arrange
    data = [1, 2, 3]
    batch_size = -1

    # Act & Assert
    with pytest.raises(ValueError, match="batch_size must be at least 1"):
        list(create_batches(data, batch_size))


def test_create_batches_invalid_type():
    """Test that non-integer batch_size raises TypeError."""
    # Arrange
    data = [1, 2, 3]
    batch_size = "5"

    # Act & Assert
    with pytest.raises(TypeError, match="batch_size must be an integer"):
        list(create_batches(data, batch_size))


def test_create_batches_float_type():
    """Test that float batch_size raises TypeError."""
    # Arrange
    data = [1, 2, 3]
    batch_size = 2.5

    # Act & Assert
    with pytest.raises(TypeError, match="batch_size must be an integer"):
        list(create_batches(data, batch_size))


async def test_read_chunks_basic(tmp_path):
    """Test basic reading of JSONL file."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [
        {"section_header": "Header 1", "section_text": "Text 1"},
        {"section_header": "Header 2", "section_text": "Text 2"},
        {"section_header": "Header 3", "section_text": "Text 3"},
    ]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=2):
        batches.append(batch)

    # Assert
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1
    assert batches[0][0]["section_header"] == "Header 1"
    assert batches[0][1]["section_header"] == "Header 2"
    assert batches[1][0]["section_header"] == "Header 3"


async def test_read_chunks_exact_multiple(tmp_path):
    """Test reading when number of chunks is exact multiple of batch_size."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [{"id": i} for i in range(6)]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=3):
        batches.append(batch)

    # Assert
    assert len(batches) == 2
    assert len(batches[0]) == 3
    assert len(batches[1]) == 3


async def test_read_chunks_single_batch(tmp_path):
    """Test reading when all chunks fit in a single batch."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [{"id": i} for i in range(3)]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=10):
        batches.append(batch)

    # Assert
    assert len(batches) == 1
    assert len(batches[0]) == 3


async def test_read_chunks_empty_file(tmp_path):
    """Test reading from empty file."""
    # Arrange
    file_path = tmp_path / "empty.jsonl"
    file_path.write_text("")

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=2):
        batches.append(batch)

    # Assert
    assert batches == []


async def test_read_chunks_empty_lines(tmp_path):
    """Test reading file with empty lines (should skip them)."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    content = '\n{"id": 1}\n\n{"id": 2}\n\n\n{"id": 3}\n'
    file_path.write_text(content)

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=2):
        batches.append(batch)

    # Assert
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


async def test_read_chunks_file_not_found(tmp_path):
    """Test that FileNotFoundError is raised for non-existent file."""
    # Arrange
    file_path = tmp_path / "nonexistent.jsonl"

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="File not found"):
        async for _ in read_chunks_in_batches(file_path):
            pass


async def test_read_chunks_invalid_batch_size(tmp_path):
    """Test that ValueError is raised for invalid batch_size."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    file_path.write_text('{"id": 1}')

    # Act & Assert
    with pytest.raises(ValueError, match="batch_size must be at least 1"):
        async for _ in read_chunks_in_batches(file_path, batch_size=0):
            pass


async def test_read_chunks_invalid_json_non_strict(tmp_path, caplog):
    """Test handling of invalid JSON in non-strict mode (should skip and log)."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    content = '{"id": 1}\n{invalid json}\n{"id": 2}\n'
    file_path.write_text(content)

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=2, strict=False):
        batches.append(batch)

    # Assert
    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert batches[0][0]["id"] == 1
    assert batches[0][1]["id"] == 2
    # Check that error was logged
    assert any("Failed to parse JSON at line 2" in record.message for record in caplog.records)


async def test_read_chunks_invalid_json_strict(tmp_path):
    """Test that invalid JSON raises exception in strict mode."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    content = '{"id": 1}\n{invalid json}\n{"id": 2}\n'
    file_path.write_text(content)

    # Act & Assert
    with pytest.raises(json.JSONDecodeError):
        async for _ in read_chunks_in_batches(file_path, batch_size=2, strict=True):
            pass


async def test_read_chunks_streaming_behavior(tmp_path):
    """Test that function yields batches incrementally (streaming)."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [{"id": i} for i in range(25)]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act - verify we can start processing before reading entire file
    batch_count = 0
    first_batch = None
    async for batch in read_chunks_in_batches(file_path, batch_size=5):
        if first_batch is None:
            first_batch = batch
        batch_count += 1
        # Verify we get batches incrementally
        assert len(batch) <= 5

    # Assert
    assert batch_count == 5
    assert first_batch is not None
    assert len(first_batch) == 5


async def test_read_chunks_default_batch_size(tmp_path):
    """Test reading with default batch_size (10)."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [{"id": i} for i in range(25)]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path):
        batches.append(batch)

    # Assert
    assert len(batches) == 3
    assert len(batches[0]) == 10
    assert len(batches[1]) == 10
    assert len(batches[2]) == 5


async def test_read_chunks_path_as_string(tmp_path):
    """Test that function accepts file path as string."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [{"id": 1}, {"id": 2}]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(str(file_path), batch_size=2):
        batches.append(batch)

    # Assert
    assert len(batches) == 1
    assert len(batches[0]) == 2


async def test_read_chunks_complex_json_objects(tmp_path):
    """Test reading complex nested JSON objects."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    data = [
        {
            "section_header": "Header 1",
            "section_text": "Text 1",
            "header_level": 1,
            "metadata": {"author": "John", "tags": ["tag1", "tag2"]},
        },
        {
            "section_header": "Header 2",
            "section_text": "Text 2",
            "header_level": 2,
            "metadata": {"author": "Jane", "tags": ["tag3"]},
        },
    ]
    file_path.write_text("\n".join(json.dumps(item) for item in data))

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=1):
        batches.append(batch)

    # Assert
    assert len(batches) == 2
    assert batches[0][0]["metadata"]["author"] == "John"
    assert batches[0][0]["metadata"]["tags"] == ["tag1", "tag2"]
    assert batches[1][0]["metadata"]["author"] == "Jane"


async def test_read_chunks_whitespace_handling(tmp_path):
    """Test that leading/trailing whitespace in lines is handled correctly."""
    # Arrange
    file_path = tmp_path / "test.jsonl"
    content = '  {"id": 1}  \n\t{"id": 2}\t\n   {"id": 3}   \n'
    file_path.write_text(content)

    # Act
    batches = []
    async for batch in read_chunks_in_batches(file_path, batch_size=2):
        batches.append(batch)

    # Assert
    assert len(batches) == 2
    assert len(batches[0]) == 2
    assert len(batches[1]) == 1


def _make_yolo_result(class_ids: list[int], boxes: list[list[float]]):
    result = MagicMock()
    result.boxes.cls = torch.tensor(class_ids, dtype=torch.float32)
    result.boxes.xyxy = torch.tensor(boxes, dtype=torch.float32)
    return result


CLASS_MAPPING = {0: "person", 16: "dog"}


def test_get_image_path_returns_correct_path(tmp_path):
    path = get_image_path(tmp_path, "abc123")
    assert path == tmp_path / "abc123.jpg"


# --- _get_class_mapping ---


def test_get_class_mapping_standard():
    config = {"class-detection-ids": [{"id": 0, "name": "person"}, {"id": 16, "name": "dog"}]}
    assert _get_class_mapping(config) == {0: "person", 16: "dog"}


def test_get_class_mapping_empty():
    assert _get_class_mapping({}) == {}


def test_get_class_mapping_custom_keys():
    config = {
        "detections": [
            {"class_id": 1, "class_name": "cat"},
            {"class_id": 2, "class_name": "bird"},
        ]
    }
    result = _get_class_mapping(
        config,
        class_name_key="class_name",
        class_id_key="class_id",
        class_mapping_key="detections",
    )
    assert result == {1: "cat", 2: "bird"}


# --- _extract_bounding_box ---


def test_extract_bounding_box_first():
    result = _make_yolo_result([16], [[10.0, 20.0, 30.0, 40.0]])
    assert _extract_bounding_box(result, 0) == [10.0, 20.0, 30.0, 40.0]


def test_extract_bounding_box_second():
    result = _make_yolo_result([0, 16], [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]])
    assert _extract_bounding_box(result, 1) == [5.0, 6.0, 7.0, 8.0]


# --- _extract_class_bounding_boxes ---


def test_extract_class_bounding_boxes_matching():
    result = _make_yolo_result([16], [[10.0, 20.0, 30.0, 40.0]])
    assert _extract_class_bounding_boxes(result, 16) == [[10.0, 20.0, 30.0, 40.0]]


def test_extract_class_bounding_boxes_no_match():
    result = _make_yolo_result([0], [[10.0, 20.0, 30.0, 40.0]])
    assert _extract_class_bounding_boxes(result, 16) == []


def test_extract_class_bounding_boxes_multiple_matches():
    result = _make_yolo_result(
        [16, 0, 16],
        [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0], [9.0, 10.0, 11.0, 12.0]],
    )
    boxes = _extract_class_bounding_boxes(result, 16)
    assert boxes == [[1.0, 2.0, 3.0, 4.0], [9.0, 10.0, 11.0, 12.0]]


# --- _single_dog_no_person_image ---


@pytest.mark.parametrize(
    "class_ids,expected",
    [
        ([16], True),
        ([], True),
        ([16, 16], False),
        ([16, 0], False),
        ([0], False),
    ],
)
def test_single_dog_no_person_image(class_ids, expected):
    result = _make_yolo_result(class_ids, [[0.0, 0.0, 1.0, 1.0]] * len(class_ids))
    assert _single_dog_no_person_image(result, CLASS_MAPPING) is expected


# --- _any_dog_no_person_image ---


@pytest.mark.parametrize(
    "class_ids,expected",
    [
        ([16], True),
        ([16, 16], True),
        ([], False),
        ([16, 0], False),
    ],
)
def test_any_dog_no_person_image(class_ids, expected):
    result = _make_yolo_result(class_ids, [[0.0, 0.0, 1.0, 1.0]] * len(class_ids))
    assert _any_dog_no_person_image(result, CLASS_MAPPING) is expected


# --- get_device_name ---


def test_get_device_name_cuda_available():
    with patch("torch.cuda.is_available", return_value=True):
        assert get_device_name() == "cuda:0"


def test_get_device_name_cuda_unavailable():
    with patch("torch.cuda.is_available", return_value=False):
        with pytest.raises(RuntimeError, match="CUDA not available"):
            get_device_name()
