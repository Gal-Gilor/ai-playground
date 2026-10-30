# Dog Detection: Dataset Preparation Pipeline for Pooch Perfect

## Overview

[Pooch Perfect](https://github.com/Gal-Gilor/pooch-perfect) is an application that uses multiple models to determine which dog breed a person most resembles. Training the dog breed classifier requires images cropped to a single dog. This repository handles the data preparation workflow: uploading and downloading images to and from GCS, and running YOLO26 inference to detect the dogs in each image and store their bounding box coordinates in `data/labels.csv`, which originally contains only image filenames and breed labels.

## How it works

1. Loads `data/labels.csv` (10,222 rows, one per image — columns: image filename and dog breed)
2. Runs batched YOLO inference using the model named in `config.yaml` (`yolo26l.pt`)
3. Writes each result to a resumable JSONL checkpoint (`data/labels.checkpoint.jsonl`) as it goes
4. Joins detection results back onto the labels DataFrame
5. Writes the updated CSV with boolean flags and bounding box coordinates (`data/labels.csv` by default)
6. Deletes the checkpoint on success

If the pipeline is interrupted, re-running it picks up from the checkpoint automatically.

## Output

Three columns are added to the labels CSV:

- `single_dog`: `True` if exactly one dog was detected
- `multiple_dogs`: `True` if more than one dog was detected
- `dog_bounding_boxes`: JSON array of `[x1, y1, x2, y2]` coordinates for all detected dogs

Only dogs are detected. People in the image are not checked, so the flags do not exclude images that also contain a person.

The dog-breed-classifier does not filter on these flags. It crops every bounding box in `dog_bounding_boxes`, which removes background and other objects that could confuse the breed classification model. To train on single-dog images only, filter to rows where `single_dog == True` first.

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

`config.yaml` controls the runtime paths and detection settings, plus the `upload-*` and `download-*` options used by the GCS scripts. The detection settings:

```yaml
path-to-detection-model: "yolo26l.pt"
path-to-images: "data/images"
path-to-labels: "data/labels.csv"
class-detection-ids:
  - {name: person, id: 0}
  - {name: dog, id: 16}
```

Class IDs are from the COCO dataset (person=0, dog=16). Set the `PATH_TO_CONFIG` environment variable (or add it to a `.env` file) to use a different config path.

`path-to-detection-model` accepts any model name that Ultralytics recognizes (e.g. `yolo11n.pt`, `yolov8s.pt`). If the file does not exist locally, Ultralytics downloads the weights to the working directory (git ignores `/*.pt`). You do not need to download model weights ahead of time.

## Running

| Command | Description |
|---|---|
| `make update-labels` | Run YOLO inference and update `data/labels.csv` |
| `make upload` | Upload `data/images/` to GCS (requires credentials) |
| `make download` | Download images from GCS to `data/images/` (requires credentials) |
| `make clean-cache` | Remove `__pycache__`, `.pyc`, `.pytest_cache`, `.ruff_cache` |

### update_labels.py options

All options are optional. With no flags, the script reads the paths from `config.yaml` and overwrites `data/labels.csv`.

| Flag | Default | Description |
|---|---|---|
| `--images-directory` | `path-to-images` from `config.yaml` (`data/images`) | Directory with the source JPEGs |
| `--labels-csv` | `path-to-labels` from `config.yaml` (`data/labels.csv`) | Labels CSV to read |
| `--output-csv` | `--labels-csv` | Where to write the updated CSV |
| `--checkpoint-path` | `<output stem>.checkpoint.jsonl` next to the output CSV | JSONL checkpoint used to resume |

```bash
uv run python scripts/update_labels.py \
  --images-directory /data/images \
  --labels-csv /data/labels.csv \
  --output-csv /out/labels.csv
```

### Docker image

The `Dockerfile` builds a `python:3.12-slim` image with the locked dependencies installed through `uv` and the YOLO weights from `config.yaml` downloaded at build time. The Vertex AI pipeline runs it as a step. The image sets no entrypoint, so pass the command when you run it, and it needs a GPU.

```bash
docker build -t dog-detection .
docker run --gpus all dog-detection python scripts/update_labels.py --help
```

`.dockerignore` leaves `data/` out of the image, so mount or download the images and labels at run time.

### Downloading from a public bucket

`make download` uses GCP Application Default Credentials. To download from a publicly accessible bucket without credentials, call the script directly with `--public`:

```bash
uv run python scripts/download_folder.py \
  --public \
  --bucket pooch-perfect-public \
  --source-prefix data/raw \
  --file-type-suffix .jpg
```

`--bucket` overrides the `GOOGLE_CLOUD_BUCKET` env var. `--source-prefix` overrides `download-source-prefix` from `config.yaml`.

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
├── Dockerfile             # Image for the Vertex AI pipeline step
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
│   └── yolo26n.pt         # YOLO weights (not used by default; see config.yaml)
├── data/
│   ├── images/            # MD5-named JPGs
│   └── labels.csv         # Ground truth labels (updated in place)
└── tests/
```
