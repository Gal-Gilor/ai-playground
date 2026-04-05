"""Shared training utilities used by train_classification_head and finetune_backbone."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader
from torch.utils.data import Subset
from torchvision import transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

from config import BaseTrainingConfig

logger = logging.getLogger(__name__)


def get_device() -> torch.device:
    """Return the best available device, preferring CUDA over CPU.

    Returns:
        torch.device: ``cuda:0`` if a CUDA-capable GPU is available, otherwise ``cpu``.
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA confirmed: {device_name}")
        return torch.device("cuda:0")
    logger.info("No CUDA GPU found — using CPU")
    return torch.device("cpu")


def set_bn_eval(model: nn.Module) -> None:
    """Set all BatchNorm layers to eval mode to preserve ImageNet statistics.

    Call this after ``model.train()`` at the start of every training epoch.

    Args:
        model: The model whose BatchNorm layers should be frozen.
    """
    for module in model.modules():
        if isinstance(module, (nn.BatchNorm2d, nn.BatchNorm1d)):
            module.eval()


def get_dataloaders(
    cfg: BaseTrainingConfig,
) -> tuple[DataLoader, DataLoader, list[str], torch.Tensor]:
    """Build train and validation DataLoaders from a stratified split of the train directory.

    Reserves ``cfg.val_split`` fraction of each breed for validation (stratified).
    Class weights are computed from training indices only to avoid leakage.

    Args:
        cfg: Config with directory paths and transform parameters.

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
    cfg: BaseTrainingConfig,
    device: torch.device,
    run_dir: Path,
    class_weights: torch.Tensor,
    classes: list[str],
    optimizer: torch.optim.Optimizer,
    *,
    freeze_bn: bool = False,
    checkpoint_metadata: dict | None = None,
) -> dict[str, float | int]:
    """Train the model, saving checkpoints and curves into run_dir.

    Saves ``best.pth`` whenever validation loss improves and ``latest.pth``
    after every epoch. Stops early if validation loss has not improved for
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
        optimizer: Optimizer to use for training.
        freeze_bn: If True, keep BatchNorm layers in eval mode during training
            to preserve ImageNet statistics (used during backbone fine-tuning).

    Returns:
        Dict with best-epoch metrics: best_epoch, best_train_loss, best_train_acc,
        best_val_loss, best_val_acc.
    """
    model.to(device)
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
    best_epoch = 0
    best_train_loss = float("inf")
    best_train_acc = 0.0
    best_val_acc = 0.0
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
        if freeze_bn:
            set_bn_eval(model)
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
            **(checkpoint_metadata or {}),
        }
        torch.save(checkpoint, latest_path)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_epoch = epoch
            best_train_loss = avg_train_loss
            best_train_acc = train_acc
            best_val_acc = val_acc
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
    return {
        "best_epoch": best_epoch,
        "best_train_loss": round(best_train_loss, 4),
        "best_train_acc": round(best_train_acc, 2),
        "best_val_loss": round(best_val_loss, 4),
        "best_val_acc": round(best_val_acc, 2),
    }
