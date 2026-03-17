"""Fine-tune EfficientNet-B3 on the dog breed dataset via transfer learning.

Usage (from project root):
    python -m training.scripts.train_classifier
    python -m training.scripts.train_classifier --epochs 1 --batch-size 16
    python -m training.scripts.train_classifier --help
"""

import argparse
import datetime
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import yaml
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader
from torch.utils.data import Subset
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import EfficientNet_B3_Weights
from torchvision.models import efficientnet_b3
from tqdm import tqdm

from app.models.config import TrainClassifierConfig
from app.settings import config
from training.utils import get_device

logger = logging.getLogger(__name__)


def get_dataloaders(
    cfg: TrainClassifierConfig,
) -> tuple[DataLoader, DataLoader, list[str], torch.Tensor]:
    """Build train and validation DataLoaders from a stratified split of the train directory.

    Reserves ``cfg.val_split`` fraction of each breed for validation (stratified).
    Class weights are computed from training indices only to avoid leakage.

    Args:
        cfg: TrainClassifierConfig with directory paths and transform parameters.

    Returns:
        A ``(train_loader, val_loader, classes, class_weights)`` tuple.
    """
    train_transform = transforms.Compose(
        [
            transforms.CenterCrop(cfg.center_crop_size),
            transforms.RandomHorizontalFlip(p=cfg.random_horizontal_flip_prob),
            transforms.RandomRotation(degrees=cfg.random_rotation_degrees),
            transforms.ColorJitter(
                brightness=cfg.color_jitter_brightness,
                contrast=cfg.color_jitter_contrast,
                saturation=cfg.color_jitter_saturation,
                hue=cfg.color_jitter_hue,
            ),
            transforms.ToTensor(),
            transforms.Normalize(mean=cfg.normalize_mean, std=cfg.normalize_std),
        ]
    )
    val_transform = transforms.Compose(
        [
            transforms.CenterCrop(cfg.center_crop_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=cfg.normalize_mean, std=cfg.normalize_std),
        ]
    )

    train_full = ImageFolder(root=cfg.train_directory, transform=train_transform)
    targets = train_full.targets

    train_indices, val_indices = train_test_split(
        list(range(len(targets))),
        test_size=cfg.val_split,
        stratify=targets,
        random_state=42,
    )

    val_full = ImageFolder(root=cfg.train_directory, transform=val_transform)

    train_dataset = Subset(train_full, train_indices)
    val_dataset = Subset(val_full, val_indices)

    train_targets = [targets[i] for i in train_indices]
    weights = compute_class_weight(
        class_weight="balanced",
        classes=np.arange(len(train_full.classes)),
        y=train_targets,
    )
    class_weights = torch.tensor(weights, dtype=torch.float32)

    train_loader = DataLoader(
        train_dataset, batch_size=cfg.batch_size, shuffle=True, num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=cfg.batch_size, shuffle=False, num_workers=4, pin_memory=True
    )

    logger.info(
        f"Split {len(train_full)} images into {len(train_dataset)} train / "
        f"{len(val_dataset)} val across {len(train_full.classes)} classes (stratified)"
    )
    return train_loader, val_loader, train_full.classes, class_weights


def build_model(num_classes: int) -> nn.Module:
    """Load pretrained EfficientNet-B0 and replace the classifier head.

    The convolutional backbone (model.features) is frozen; the classifier head is trained.

    Args:
        num_classes: Number of output classes.

    Returns:
        The modified model.
    """
    model = efficientnet_b3(weights=EfficientNet_B3_Weights.DEFAULT)
    for param in model.features.parameters():
        param.requires_grad = False
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    logger.info(f"Built EfficientNet-B3 head: {in_features} → {num_classes} classes")

    return model


def save_curves(history: dict[str, list[float]], run_dir: Path) -> None:
    """Save train/val loss and accuracy curves as curves.jpg in run_dir.

    Args:
        history: Dict with keys train_loss, val_loss, train_acc, val_acc.
        run_dir: Directory where curves.jpg is written.
    """
    epochs = range(1, len(history["train_loss"]) + 1)
    fig, (ax_loss, ax_acc) = plt.subplots(1, 2, figsize=(12, 4))

    ax_loss.plot(epochs, history["train_loss"], label="train")
    ax_loss.plot(epochs, history["val_loss"], label="val")
    ax_loss.set_title("Loss")
    ax_loss.set_xlabel("Epoch")
    ax_loss.legend()

    ax_acc.plot(epochs, history["train_acc"], label="train")
    ax_acc.plot(epochs, history["val_acc"], label="val")
    ax_acc.set_title("Accuracy (%)")
    ax_acc.set_xlabel("Epoch")
    ax_acc.legend()

    fig.tight_layout()
    fig.savefig(run_dir / "curves.jpg")
    plt.close(fig)
    logger.info(f"Saved training curves to {run_dir / 'curves.jpg'}")


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    cfg: TrainClassifierConfig,
    device: torch.device,
    run_dir: Path,
    class_weights: torch.Tensor,
    classes: list[str],
) -> None:
    """Train the model, saving checkpoints and curves into run_dir.

    Saves ``best.pth`` whenever validation accuracy improves and ``latest.pth``
    after every epoch. Stops early if validation accuracy has not improved for
    ``cfg.early_stopping_patience`` consecutive epochs.

    Args:
        model: The model to train.
        train_loader: DataLoader for the training split.
        val_loader: DataLoader for the validation split.
        cfg: Config containing training hyperparameters and early_stopping_patience.
        device: Device to run training on.
        run_dir: Directory for this run's artifacts (must already exist).
        class_weights: Per-class loss weights to handle class imbalance.
        classes: Ordered list of class names, used to label checkpoints.
    """
    model.to(device)
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=cfg.learning_rate,
        weight_decay=cfg.weight_decay,
    )
    criterion = nn.CrossEntropyLoss(
        weight=class_weights.to(device), label_smoothing=cfg.label_smoothing
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        patience=cfg.lr_patience,
        factor=cfg.lr_factor,
        min_lr=cfg.lr_min_lr,
    )

    best_val_loss = float("inf")
    patience_counter = 0
    best_path = run_dir / "best.pth"
    latest_path = run_dir / "latest.pth"
    history: dict[str, list[float]] = {
        "train_loss": [],
        "val_loss": [],
        "train_acc": [],
        "val_acc": [],
    }

    for epoch in range(1, cfg.epochs + 1):
        # --- train ---
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        for images, labels in tqdm(
            train_loader, desc=f"Epoch {epoch}/{cfg.epochs} [train]", leave=False
        ):
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * images.size(0)
            train_correct += (outputs.argmax(dim=1) == labels).sum().item()
            train_total += images.size(0)

        # --- eval ---
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in tqdm(
                val_loader, desc=f"Epoch {epoch}/{cfg.epochs} [val]", leave=False
            ):
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                val_correct += (outputs.argmax(dim=1) == labels).sum().item()
                val_total += images.size(0)

        avg_train_loss = train_loss / train_total
        train_acc = 100.0 * train_correct / train_total
        avg_val_loss = val_loss / val_total
        val_acc = 100.0 * val_correct / val_total

        history["train_loss"].append(avg_train_loss)
        history["val_loss"].append(avg_val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        logger.info(
            f"Epoch {epoch}/{cfg.epochs} | "
            f"train_loss={avg_train_loss:.3f} train_acc={train_acc:.1f}% | "
            f"val_loss={avg_val_loss:.3f} val_acc={val_acc:.1f}%"
        )

        checkpoint = {
            "model_state_dict": model.state_dict(),
            "classes": classes,
            "epoch": epoch,
            "val_loss": avg_val_loss,
            "val_acc": val_acc,
        }
        torch.save(checkpoint, latest_path)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            torch.save(checkpoint, best_path)
            logger.info(f"New best val_loss={best_val_loss:.4f} — saved best checkpoint")
        else:
            patience_counter += 1
            logger.info(f"No improvement ({patience_counter}/{cfg.early_stopping_patience})")
            if patience_counter >= cfg.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break

        scheduler.step(avg_val_loss)
        current_lr = optimizer.param_groups[0]["lr"]
        logger.info(f"lr={current_lr:.2e}")

    save_curves(history, run_dir)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments, defaulting to values from config."""
    cfg = config.training.train_classifier
    parser = argparse.ArgumentParser(
        description="Fine-tune EfficientNet-B0 on the dog breed dataset."
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

    cfg = TrainClassifierConfig(
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
    )

    run_dir = Path(cfg.output_directory) / datetime.datetime.now().strftime(
        "run_%Y%m%d_%H%M%S"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Run directory: {run_dir}")

    params = {
        "epochs": cfg.epochs,
        "batch_size": cfg.batch_size,
        "learning_rate": cfg.learning_rate,
        "weight_decay": cfg.weight_decay,
        "val_split": cfg.val_split,
        "early_stopping_patience": cfg.early_stopping_patience,
    }
    with open(run_dir / "params.yaml", "w") as f:
        yaml.safe_dump(params, f, sort_keys=False)

    device = torch.device(args.device) if args.device else get_device()
    logger.info(f"Using device: {device}")

    train_loader, val_loader, classes, class_weights = get_dataloaders(cfg)
    model = build_model(num_classes=len(classes))
    train(model, train_loader, val_loader, cfg, device, run_dir, class_weights, classes)


if __name__ == "__main__":
    main()
