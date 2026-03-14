# Dog Detection: Dataset Preparation Pipeline for Pooch Perfect

## Overview

[Pooch Perfect](https://github.com/Gal-Gilor/pooch-perfect) is an application that uses multiple models to determine which dog breed a person most resembles. Training the dog breed classifier requires images with exactly one dog and no people. This repository handles the full data preparation workflow: uploading and downloading images to and from GCS, and running YOLOv26 inference to identify whether each image contains a single dog or multiple dogs and store bounding box coordinates back to `data/labels.csv`, which originally contains only image filenames and breed labels.

## How it works

1. Loads `data/labels.csv` (10,222 rows, one per image — columns: image filename and dog breed)
2. Runs batched YOLO inference using `models/yolo26n.pt`
3. Writes each result to a resumable JSONL checkpoint (`.labels.csv.checkpoint.jsonl`) as it goes
4. Joins detection results back onto the labels DataFrame
5. Outputs the updated `data/labels.csv` with boolean flags and bounding box coordinates
6. Deletes the checkpoint on success

If the pipeline is interrupted, re-running it picks up from the checkpoint automatically.

## Output

Three columns are added to `labels.csv`:

- `single_dog`: `True` if exactly one dog was detected and no person; suitable for training
- `multiple_dogs`: `True` if more than one dog was detected and no person; excluded from training
- `dog_bounding_boxes`: JSON array of `[x1, y1, x2, y2]` coordinates for all detected dogs

To get a usable training set, filter to rows where `single_dog == True`, then use `dog_bounding_boxes` to crop each image to just the dog. Cropping removes background and other objects that could confuse the breed classification model.

## Setup

Prerequisites:

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) for package management
- A CUDA-capable GPU (the pipeline raises `RuntimeError` if CUDA is unavailable)

Install dependencies and the project package:

```bash
uv sync
```

`uv sync` installs the project in editable mode so `src` resolves correctly when running scripts directly.

## Configuration

`config.yaml` controls all runtime paths and detection settings:

```yaml
path-to-detection-model: "models/yolo26n.pt"
path-to-images: "data/images"
path-to-labels: "data/labels.csv"
class-detection-ids:
  - {name: person, id: 0}
  - {name: dog, id: 16}
```

Class IDs are from the COCO dataset (person=0, dog=16). Set the `PATH_TO_CONFIG` environment variable (or add it to a `.env` file) to use a different config path.

`path-to-detection-model` accepts any model name that Ultralytics recognizes (e.g. `yolo11n.pt`, `yolov8s.pt`). If the file does not exist locally, Ultralytics downloads the weights automatically. You do not need to download model weights ahead of time.

## Running

| Command | Description |
|---|---|
| `make update-labels` | Run YOLO inference and update `data/labels.csv` |
| `make upload` | Upload `data/images/` to GCS |
| `make download` | Download images from GCS to `data/images/` |
| `make clean-cache` | Remove `__pycache__`, `.pyc`, `.pytest_cache`, `.ruff_cache` |

## Development

```bash
# Lint
uv run ruff check src/ scripts/

# Format
uv run ruff format src/ scripts/

# Test
uv run pytest
```

## Project structure

```
dog-detection/
├── config.yaml            # Runtime configuration
├── Makefile               # Common task runner
├── scripts/
│   ├── update_labels.py   # Pipeline entrypoint
│   ├── upload_folder.py   # Upload images to GCS
│   └── download_folder.py # Download images from GCS
├── src/
│   ├── settings.py        # Config loading and cached YOLO model
│   ├── storage.py         # Google Cloud Storage utilities
│   └── utils.py           # Detection helpers and batching utilities
├── models/
│   └── yolo26n.pt         # YOLO model weights
├── data/
│   ├── images/            # MD5-named JPGs
│   └── labels.csv         # Ground truth labels (updated in place)
└── tests/
```
