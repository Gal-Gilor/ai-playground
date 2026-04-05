"""Fine-tune EfficientNet-B4 on the dog breed dataset via transfer learning.

Usage (from project root):
    python -m scripts.train_classification_head
    python -m scripts.train_classification_head --epochs 1 --batch-size 16
    python -m scripts.train_classification_head --help
"""

import argparse
import datetime
import logging
from pathlib import Path

import torch
import torch.nn as nn
import yaml
from torchvision.models import EfficientNet_B4_Weights
from torchvision.models import efficientnet_b4

from config import TrainClassificationHeadConfig
from settings import config
from trainer import get_dataloaders
from trainer import get_device
from trainer import train

logger = logging.getLogger(__name__)


def build_model(
    num_classes: int,
    head_hidden_units: int,
    head_dropout_rate: float,
) -> nn.Module:
    """Load pretrained EfficientNet-B4 and replace the classifier head.

    The convolutional backbone (model.features) is frozen; the classifier head is trained.
    The head is: Dropout(0.3) → Linear(1792, head_hidden_units) → ReLU →
    Dropout(head_dropout_rate) → Linear(head_hidden_units, num_classes).

    Args:
        num_classes: Number of output classes.
        head_hidden_units: Size of the intermediate dense layer.
        head_dropout_rate: Dropout rate applied after the intermediate dense layer.

    Returns:
        The modified model.
    """
    model = efficientnet_b4(weights=EfficientNet_B4_Weights.DEFAULT)
    for param in model.features.parameters():
        param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
        nn.Linear(in_features, head_hidden_units),
        nn.ReLU(),
        nn.Dropout(head_dropout_rate),
        nn.Linear(head_hidden_units, num_classes),
    )
    logger.info(f"EfficientNet-B4 → {in_features} → {head_hidden_units} → {num_classes}.")

    return model


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments, defaulting to values from config."""
    cfg = config.training.train_classification_head
    parser = argparse.ArgumentParser(
        description="Fine-tune EfficientNet-B4 on the dog breed dataset."
    )
    parser.add_argument("--train-directory", type=str, default=cfg.train_directory)
    parser.add_argument("--output-directory", type=str, default=cfg.output_directory)
    parser.add_argument("--epochs", type=int, default=cfg.epochs)
    parser.add_argument("--batch-size", type=int, default=cfg.batch_size)
    parser.add_argument("--learning-rate", type=float, default=cfg.learning_rate)
    parser.add_argument("--weight-decay", type=float, default=cfg.weight_decay)
    parser.add_argument("--val-split", type=float, default=cfg.val_split)
    parser.add_argument(
        "--normalize-mean",
        type=float,
        nargs=3,
        default=cfg.normalize_mean,
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--normalize-std",
        type=float,
        nargs=3,
        default=cfg.normalize_std,
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--random-horizontal-flip-prob", type=float, default=cfg.random_horizontal_flip_prob
    )
    parser.add_argument(
        "--random-rotation-degrees", type=int, default=cfg.random_rotation_degrees
    )
    parser.add_argument(
        "--color-jitter-brightness", type=float, default=cfg.color_jitter_brightness
    )
    parser.add_argument(
        "--color-jitter-contrast", type=float, default=cfg.color_jitter_contrast
    )
    parser.add_argument(
        "--color-jitter-saturation", type=float, default=cfg.color_jitter_saturation
    )
    parser.add_argument("--color-jitter-hue", type=float, default=cfg.color_jitter_hue)
    parser.add_argument("--center-crop-size", type=int, default=cfg.center_crop_size)
    parser.add_argument(
        "--early-stopping-patience", type=int, default=cfg.early_stopping_patience
    )
    parser.add_argument("--head-hidden-units", type=int, default=cfg.head_hidden_units)
    parser.add_argument("--head-dropout-rate", type=float, default=cfg.head_dropout_rate)
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to use for training (default: cuda if available, else cpu)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: parse arguments and run training."""
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = TrainClassificationHeadConfig(
        train_directory=args.train_directory,
        output_directory=args.output_directory,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        val_split=args.val_split,
        normalize_mean=args.normalize_mean,
        normalize_std=args.normalize_std,
        random_horizontal_flip_prob=args.random_horizontal_flip_prob,
        random_rotation_degrees=args.random_rotation_degrees,
        color_jitter_brightness=args.color_jitter_brightness,
        color_jitter_contrast=args.color_jitter_contrast,
        color_jitter_saturation=args.color_jitter_saturation,
        color_jitter_hue=args.color_jitter_hue,
        center_crop_size=args.center_crop_size,
        early_stopping_patience=args.early_stopping_patience,
        head_hidden_units=args.head_hidden_units,
        head_dropout_rate=args.head_dropout_rate,
    )

    run_dir = Path(cfg.output_directory) / datetime.datetime.now().strftime(
        "run_%Y%m%d_%H%M%S"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Run directory: {run_dir}")

    device = torch.device(args.device) if args.device else get_device()
    logger.info(f"Using device: {device}")

    train_loader, val_loader, classes, class_weights = get_dataloaders(cfg)
    model = build_model(
        num_classes=len(classes),
        head_hidden_units=cfg.head_hidden_units,
        head_dropout_rate=cfg.head_dropout_rate,
    )
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
    )
    metrics = train(
        model,
        train_loader,
        val_loader,
        cfg,
        device,
        run_dir,
        class_weights,
        classes,
        optimizer,
        checkpoint_metadata={
            "head_hidden_units": cfg.head_hidden_units,
            "head_dropout_rate": cfg.head_dropout_rate,
        },
    )

    params = {
        "epochs": cfg.epochs,
        "batch_size": cfg.batch_size,
        "learning_rate": cfg.learning_rate,
        "weight_decay": cfg.weight_decay,
        "val_split": cfg.val_split,
        "early_stopping_patience": cfg.early_stopping_patience,
        **metrics,
    }
    with open(run_dir / "params.yaml", "w") as f:
        yaml.safe_dump(params, f, sort_keys=False)


if __name__ == "__main__":
    main()
