"""Fine-tune EfficientNet-B4 backbone on the dog breed dataset.

Loads a checkpoint produced by ``train_classification_head``, unfreezes the last
``num_unfrozen_blocks`` entries of ``model.features``, and trains both the backbone
blocks and the classifier head jointly at a small, uniform learning rate.

BatchNorm layers are kept in eval mode throughout to preserve the ImageNet statistics
captured during the initial pre-training.

Usage (from project root):
    python -m scripts.finetune_backbone
    python -m scripts.finetune_backbone --checkpoint-path path/to/best.pth
    python -m scripts.finetune_backbone --help
"""

import argparse
import datetime
import logging
from pathlib import Path

import torch
import torch.nn as nn
import yaml
from torchvision.models import efficientnet_b4

from config import FinetuneBackboneConfig
from settings import config
from trainer import get_dataloaders
from trainer import get_device
from trainer import train

logger = logging.getLogger(__name__)


def build_model(
    checkpoint_path: str | Path,
    num_unfrozen_blocks: int,
) -> tuple[nn.Module, list[str]]:
    """Load a head-trained checkpoint and prepare the model for backbone fine-tuning.

    All parameters are frozen first, then the classifier head and the last
    ``num_unfrozen_blocks`` entries of ``model.features`` are unfrozen.

    Args:
        checkpoint_path: Path to a ``best.pth`` file from ``train_classification_head``.
        num_unfrozen_blocks: Number of trailing ``model.features`` blocks to unfreeze.

    Returns:
        A ``(model, classes)`` tuple where ``classes`` is the ordered list of breed names
        stored in the checkpoint.
    """
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    classes: list[str] = checkpoint["classes"]
    num_classes = len(classes)
    head_hidden_units: int = checkpoint.get("head_hidden_units", 512)
    head_dropout_rate: float = checkpoint.get("head_dropout_rate", 0.3)

    model = efficientnet_b4(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Sequential(
        nn.Linear(in_features, head_hidden_units),
        nn.ReLU(),
        nn.Dropout(head_dropout_rate),
        nn.Linear(head_hidden_units, num_classes),
    )
    model.load_state_dict(checkpoint["model_state_dict"])

    for param in model.parameters():
        param.requires_grad = False

    for param in model.classifier.parameters():
        param.requires_grad = True

    if num_unfrozen_blocks > 0:
        for param in model.features[-num_unfrozen_blocks:].parameters():
            param.requires_grad = True

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Loaded checkpoint from {checkpoint_path}. "
        f"Unfrozen last {num_unfrozen_blocks} feature block(s). "
        f"Trainable params: {trainable:,} / {total:,}"
    )
    return model, classes


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments, defaulting to values from config."""
    cfg = config.training.finetune_backbone
    parser = argparse.ArgumentParser(
        description="Fine-tune EfficientNet-B4 backbone on the dog breed dataset."
    )
    parser.add_argument(
        "--checkpoint-path",
        type=str,
        default=cfg.checkpoint_path if cfg else "",
        help="Path to best.pth from train_classification_head (required)",
    )
    parser.add_argument(
        "--train-directory",
        type=str,
        default=cfg.train_directory if cfg else "training/data/train",
    )
    parser.add_argument(
        "--output-directory",
        type=str,
        default=cfg.output_directory if cfg else "training/data/models",
    )
    parser.add_argument(
        "--num-unfrozen-blocks",
        type=int,
        default=cfg.num_unfrozen_blocks if cfg else 3,
        help="Number of trailing model.features blocks to unfreeze",
    )
    parser.add_argument("--epochs", type=int, default=cfg.epochs if cfg else 20)
    parser.add_argument("--batch-size", type=int, default=cfg.batch_size if cfg else 32)
    parser.add_argument(
        "--learning-rate", type=float, default=cfg.learning_rate if cfg else 1e-3
    )
    parser.add_argument("--momentum", type=float, default=cfg.momentum if cfg else 0.9)
    parser.add_argument(
        "--weight-decay", type=float, default=cfg.weight_decay if cfg else 1e-4
    )
    parser.add_argument("--val-split", type=float, default=cfg.val_split if cfg else 0.1)
    parser.add_argument(
        "--normalize-mean",
        type=float,
        nargs=3,
        default=cfg.normalize_mean if cfg else [0.485, 0.456, 0.406],
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--normalize-std",
        type=float,
        nargs=3,
        default=cfg.normalize_std if cfg else [0.229, 0.224, 0.225],
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--random-horizontal-flip-prob",
        type=float,
        default=cfg.random_horizontal_flip_prob if cfg else 0.5,
    )
    parser.add_argument(
        "--random-rotation-degrees",
        type=int,
        default=cfg.random_rotation_degrees if cfg else 15,
    )
    parser.add_argument(
        "--color-jitter-brightness",
        type=float,
        default=cfg.color_jitter_brightness if cfg else 0.2,
    )
    parser.add_argument(
        "--color-jitter-contrast",
        type=float,
        default=cfg.color_jitter_contrast if cfg else 0.2,
    )
    parser.add_argument(
        "--color-jitter-saturation",
        type=float,
        default=cfg.color_jitter_saturation if cfg else 0.2,
    )
    parser.add_argument(
        "--color-jitter-hue", type=float, default=cfg.color_jitter_hue if cfg else 0.1
    )
    parser.add_argument(
        "--center-crop-size", type=int, default=cfg.center_crop_size if cfg else 300
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=cfg.early_stopping_patience if cfg else 5,
    )
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
    """Entry point: parse arguments and run backbone fine-tuning."""
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.checkpoint_path:
        raise ValueError(
            "checkpoint_path is required. "
            "Set it in config.toml [training.finetune_backbone] or pass --checkpoint-path."
        )

    cfg = FinetuneBackboneConfig(
        checkpoint_path=args.checkpoint_path,
        train_directory=args.train_directory,
        output_directory=args.output_directory,
        num_unfrozen_blocks=args.num_unfrozen_blocks,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        momentum=args.momentum,
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
    )

    run_dir = Path(cfg.output_directory) / datetime.datetime.now().strftime(
        "run_finetune_%Y%m%d_%H%M%S"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Run directory: {run_dir}")

    device = torch.device(args.device) if args.device else get_device()
    logger.info(f"Using device: {device}")

    train_loader, val_loader, classes, class_weights = get_dataloaders(cfg)
    model, checkpoint_classes = build_model(cfg.checkpoint_path, cfg.num_unfrozen_blocks)

    if classes != list(checkpoint_classes):
        raise ValueError(
            "Class list from train directory does not match checkpoint classes. "
            "Ensure you are using the same dataset that produced the checkpoint."
        )

    optimizer = torch.optim.SGD(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=cfg.learning_rate,
        momentum=cfg.momentum,
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
        freeze_bn=True,
    )

    params = {
        "checkpoint_path": cfg.checkpoint_path,
        "num_unfrozen_blocks": cfg.num_unfrozen_blocks,
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
