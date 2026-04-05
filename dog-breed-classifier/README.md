# Dog Breed Classification

Pooch Perfect is an app I'm building that tells you what dog breed you look most like. This repo is a supporting project — the training pipeline for the breed classifier that will power it.

The data comes from the [Kaggle dog-breed-identification competition](https://www.kaggle.com/competitions/dog-breed-identification): 10,222 images across 120 breeds. The raw images needed cleaning before training. Some contained people, some were blurry, some had multiple dogs, and some had both dogs and people. The [dog-detection](https://github.com/Gal-Gilor/ai-playground/tree/main/dog-detection) pipeline handles that first: it filters for images with exactly one dog and no people, then records each dog's bounding box. Stage 1 here unpacks those bounding boxes (one row each), Stage 2 crops to 380×380 and strips the background, yielding 11,077 crops after skipping 465 that detection missed.

Some crops are still unusable due to blur or bounding boxes that didn't capture the full dog. The optional stage 2.5 uses Gemini 2.5 Flash to filter those out.

## Pipeline

| Stage | Script | Input → Output |
|-------|--------|----------------|
| 1 | `unpack_bounding_boxes` | `labels.csv` → `exploded_labels.csv` (one row per bounding box) |
| 2 | `crop_images` | Raw JPEGs → `cropped_images/` (380×380) + `cropped_image_labels.csv` |
| 2.5 (optional) | `filter_visible_dogs` | Cropped images → `cropped_visible_labels.csv` (Gemini 2.5 Flash) |
| 3 | `create_train_split` | Cropped images → `train/<breed>/` |
| 4 | `create_test_split` | `train/` → moves 20% per breed to `test/<breed>/` |
| 5 | `train_classification_head` | `train/` → `models/run_*/best.pth` |
| 6 | `finetune_backbone` | Stage 5 checkpoint → `models/run_finetune_*/best.pth` |
| — | `evaluate_model_performance` | Test directory + checkpoint → predictions CSV + accuracy |

Run the full pipeline (stages 1–5 including filter):

```bash
make pipeline
```

Individual targets: `make unpack`, `make crop`, `make filter`, `make train-split`, `make test-split`, `make train`, `make finetune`. Use `make reset` to delete intermediate data.

Each script also accepts CLI overrides:

```bash
uv run python -m scripts.<script_name> --help
```

## Model

EfficientNet-B4 pretrained on ImageNet, fine-tuned in two stages. The backbone encodes knowledge from 1.2M images; fine-tuning everything at once on 11k images risks overwriting that. Training the head first, then selectively unfreezing the backbone, avoids that.

### Architecture

```
EfficientNet-B4 (1792-dim backbone output)
  → Linear(1792, 512) → ReLU → Dropout(0.3) → Linear(512, 120)
```

The 380×380 input matches EfficientNet-B4's native resolution, derived from its compound scaling formula (224 × 1.15^4 ≈ 380). Using a different size either discards spatial information or forces upsampling the architecture wasn't designed for.

### Stage 1 — train_classification_head

The backbone is frozen. Only the classifier head is trained.

- Adam, lr=1e-3, up to 15 epochs, early stopping (patience 5)
- ReduceLROnPlateau (factor 0.5, patience 2)
- Label smoothing 0.1, class-weighted loss

Adam works well here because the head is randomly initialized and gradients vary significantly across parameters early in training. ReduceLROnPlateau halves the learning rate whenever validation loss stops improving for 2 epochs, which is more reliable than a fixed schedule when you don't know in advance when the model will plateau.

Achieves 82.69% accuracy on the test set (1744/2109 correct).

### Stage 2 — finetune_backbone

Loads the best Stage 1 checkpoint, unfreezes the last 2 EfficientNet-B4 blocks, and trains the unfrozen blocks jointly with the head.

- SGD with momentum (0.9), lr=1e-4
- BatchNorm layers kept in eval mode to preserve ImageNet statistics
- Up to 100 epochs, same early stopping

SGD at lr=1e-4 keeps updates to pre-trained weights small. SGD also generalizes better than Adam on small datasets. Adam's adaptive rates tend to overfit when data is limited. BatchNorm layers stay in eval mode so their running statistics, computed from ImageNet's 1.2M images, don't get replaced by statistics from 11k dog images.

Achieves 84.73% accuracy on the test set (1787/2109 correct).

## Setup

```bash
uv sync
```

For the optional Gemini visibility filter (stage 2.5), create a `.env` file with:

```
GOOGLE_CLOUD_PROJECT=...
GOOGLE_CLOUD_LOCATION=...
GOOGLE_CLOUD_BUCKET=...
```
