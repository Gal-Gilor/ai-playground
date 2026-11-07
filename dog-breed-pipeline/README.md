# Dog Breed Pipeline

This project runs [dog-detection](../dog-detection) and [dog-breed-classifier](../dog-breed-classifier) as two Kubeflow Pipelines (KFP 2.18) on Vertex AI. This folder holds only the orchestration. Each step runs one of the existing scripts through its CLI, inside a container image built from that project's folder.

The data pipeline turns the 10,222 raw images from the [Kaggle dog-breed-identification competition](https://www.kaggle.com/competitions/dog-breed-identification) into a dataset of cropped dogs, split into `train/` and `test/`. The training pipeline takes the location of that dataset, then trains, fine-tunes and evaluates the classifier. The two are separate so that training changes never invalidate the cached data steps. The Gemini filter is slow, and its answers can change between runs, so a saved dataset is what keeps the training input identical across runs.

## Data pipeline

| # | Step | Image | Machine | Script | Output |
|---|------|-------|---------|--------|--------|
| 1 | detect dogs | dog-detection | GPU | `scripts/update_labels.py` | labels CSV with bounding boxes |
| 2 | unpack bounding boxes | dog-breed-classifier | CPU | `scripts.unpack_bounding_boxes` | labels CSV with one row per bounding box |
| 3 | crop images | dog-breed-classifier | CPU | `scripts.crop_images` | cropped images and their labels CSV |
| 4 | filter visible dogs (optional) | dog-breed-classifier | CPU | `scripts.filter_visible_dogs` | visibility labels CSV |
| 5 | split | dog-breed-classifier | CPU | `scripts.create_train_split`, then `scripts.create_test_split` | dataset folder with `train/<breed>/` and `test/<breed>/` |

Step 1 reads the raw labels and images from the public bucket set in the `[cloud_storage]` section of `config.toml`. Steps read and write Cloud Storage through the `/gcs/` mount that Vertex AI provides.

Step 4 asks `gemini-3.5-flash` whether each crop shows a clearly visible dog. It is off by default. When it is off, the pipeline imports the visibility labels at `visible_labels_uri` instead, which defaults to the labels from the earlier run `dog-breed-data-20261031145230`. The two branches show in the Vertex AI console as `run-gemini-filter` and `reuse-visible-labels`, and the split step takes the labels from whichever one ran.

Step 5 runs both split scripts in one step because the test split moves files out of `train/`. As two steps, the second would change the first step's cached output. The split moves 20% of each breed to `test/`, chosen with seed 42 (the `[split]` section). With the reused labels, the split kept 10,782 of the 11,073 crops: 8,681 in `train/` and 2,101 in `test/`, across 120 breeds.

## Training pipeline

| # | Step | Image | Machine | Script | Inputs | Output |
|---|------|-------|---------|--------|--------|--------|
| 6 | train head | dog-breed-classifier | GPU | `scripts.train_classification_head` | dataset `train/` | run folder with `best.pth` and `metrics.json` |
| 7 | fine-tune backbone | dog-breed-classifier | GPU | `scripts.finetune_backbone` | dataset `train/`, step 6 `best.pth` | run folder with `best.pth` and `metrics.json` |
| 8 | evaluate | dog-breed-classifier | GPU | `scripts.evaluate_model_performance` | dataset `test/`, step 7 `best.pth` | `predictions.csv` and `metrics.json` |

After each of these steps, a small `log_metrics` step reads its `metrics.json` and logs the values as KFP metrics. Steps 6 to 8 run on an n1-standard-8 machine with one NVIDIA T4. The GPU type comes from `accelerator_type` in `config.toml`. The model and the reasons for the two training stages are described in the [dog-breed-classifier README](../dog-breed-classifier/README.md).

## Prerequisites

- The one-time cloud setup in [SETUP.md](SETUP.md): a gcloud configuration, the APIs, the Artifact Registry repository and the pipeline service account.
- Values in `config.toml` that match your project, bucket and service account.
- [`uv`](https://github.com/astral-sh/uv). Install the dependencies with `uv sync`.

Docker is not needed locally. Cloud Build builds the images.

## Build the images

```bash
make build-detection
make build-classifier
```

Each target builds one project's image with Cloud Build, pushes it to Artifact Registry and records its URI in `image_tags.json`. The run targets use the recorded images and stop with an error if one has not been built.

## Run the pipelines

Run the data pipeline with the reused visibility labels, or with the Gemini filter:

```bash
make run-data
make run-data PARAMS="filter_visible=true"
```

The dataset URI is the `dataset` output of the split step, shown in the Vertex AI console. Pass it to the training pipeline:

```bash
make run-training DATASET_URI=gs://...
```

Add `WAIT=1` to any run target to wait until the run finishes and log the output URIs of every step, including the dataset. Each target compiles the pipeline to `build/<name>.yaml` before submitting it. Every run is labeled `git_commit` (the short SHA of `HEAD`) and `git_dirty` (`true` when tracked files have uncommitted changes).

## Parameters

The pipeline parameters and their defaults are the `[data_parameters]` and `[training_parameters]` sections of `config.toml`. `PARAMS` overrides any of them with space-separated `NAME=VALUE` pairs:

```bash
make run-training DATASET_URI=gs://... PARAMS="head_epochs=2 finetune_epochs=2"
```

Overrides are checked before anything is compiled or submitted. An unknown name or a value of the wrong type fails, and booleans take only `true` or `false`, in any case. The merged values must also pass the limits in `config.py`:

- `finetune_learning_rate` is at most 1e-4.
- `head_lr_factor` and `finetune_lr_factor` are between 0 and 1.
- `head_lr_min_lr` and `finetune_lr_min_lr` are not negative.
- Each step's `lr_patience` is below its `early_stopping_patience`, so the learning rate is cut before early stopping ends training.

## Experiment tracking

Training runs are recorded in the Vertex AI experiment `dog-breed-tuning`. Data runs are not. Each training run records every pipeline parameter, including `dataset_uri`, and these metrics:

- `head_*` and `finetune_*`: `best_epoch`, `best_train_loss`, `best_train_acc`, `best_val_loss` and `best_val_acc` from each step's best epoch. Fine-tuning leaves out the two train values when no epoch beats its starting checkpoint.
- `test_accuracy`: the share of test images the fine-tuned model classifies correctly, in percent.

The pipeline run itself carries the `git_commit` and `git_dirty` labels.

The experiment name must differ from the pipeline names, `dog-breed-data` and `dog-breed-training`, because Vertex AI Experiments and Vertex AI Pipelines share one Vertex ML Metadata ID space. An experiment that reused a pipeline name made the submit fail with "Context to be updated has a different schema title".

## Results

The training run `dog-breed-training-20261106221723`, on commit `7fff4e9` with the default parameters, reached 91.53% test accuracy (1923 of 2101 images). The head's validation accuracy peaked at 91.48% in its last epoch, 25. Fine-tuning stopped early after 5 epochs without beating its starting checkpoint, so the evaluated model is the head.

## Image tags and caching

An image is tagged with the short SHA of the latest commit that touched its project folder. If the folder has uncommitted or untracked changes, the tag is `<sha>-dirty-<UTC timestamp>` instead, so every build of in-progress code gets a new tag. Caching is on for every run, and KFP reuses a step only when its image and inputs are unchanged. A rebuilt image with a new tag therefore reruns every step that uses it, which for the classifier image means steps 2 to 8.

## Tests

```bash
make test
```

The tests compile both pipelines and check how overrides are parsed and validated. They need no cloud access. `make lint` runs ruff.
