"""Evaluate a trained model checkpoint on the test split.

Loads a checkpoint, runs inference on the test directory, and outputs a CSV of
per-image predictions alongside an accuracy summary printed to stdout.

Usage (from project root):
    python -m scripts.evaluate_model_performance
    python -m scripts.evaluate_model_performance --checkpoint-path path/to/best.pth
    python -m scripts.evaluate_model_performance --help
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from tqdm import tqdm

from scripts.train_classification_head import build_model
from settings import config
from trainer import get_device

logger = logging.getLogger(__name__)


def load_model(
    checkpoint_path: Path,
    device: torch.device,
) -> tuple[nn.Module, list[str]]:
    """Load a checkpoint and reconstruct the model for inference.

    Reads ``classes``, ``head_hidden_units``, and ``head_dropout_rate`` from the
    checkpoint to reconstruct the exact architecture trained in stage 5 or 6.

    Args:
        checkpoint_path: Path to a ``.pth`` checkpoint from train_classification_head
            or finetune_backbone.
        device: Device to load the model onto.

    Returns:
        A ``(model, classes)`` tuple where ``classes`` is the ordered list of breed names.
    """
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    classes: list[str] = checkpoint["classes"]
    head_cfg = config.training.train_classification_head
    head_hidden_units: int = checkpoint.get("head_hidden_units", head_cfg.head_hidden_units)
    head_dropout_rate: float = checkpoint.get("head_dropout_rate", head_cfg.head_dropout_rate)

    model = build_model(
        num_classes=len(classes),
        head_hidden_units=head_hidden_units,
        head_dropout_rate=head_dropout_rate,
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    epoch = checkpoint.get("epoch", "?")
    val_acc = checkpoint.get("val_acc")
    val_acc_str = f"{val_acc:.1f}%" if isinstance(val_acc, float) else "?"
    logger.info(
        f"Loaded checkpoint: epoch={epoch}, val_acc={val_acc_str}, classes={len(classes)}"
    )
    return model, classes


def get_transforms(
    center_crop_size: int,
    normalize_mean: list[float],
    normalize_std: list[float],
) -> transforms.Compose:
    """Build the validation transform (matches trainer.get_dataloaders val_transform).

    Args:
        center_crop_size: Size to center-crop each image to before normalization.
        normalize_mean: Per-channel normalization mean (ImageNet default).
        normalize_std: Per-channel normalization std (ImageNet default).

    Returns:
        A composed torchvision transform.
    """
    return transforms.Compose(
        [
            transforms.CenterCrop(center_crop_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=normalize_mean, std=normalize_std),
        ]
    )


def run_inference(
    model: nn.Module,
    dataloader: DataLoader,
    classes: list[str],
    device: torch.device,
) -> pd.DataFrame:
    """Run inference on all images in the dataloader and collect per-image results.

    Args:
        model: Model in eval mode.
        dataloader: DataLoader with ``shuffle=False`` so image order is deterministic.
        classes: Ordered list of class names matching the model's output indices.
        device: Device the model is on.

    Returns:
        DataFrame with columns: image_path, true_label, predicted_label, confidence,
        correct, top5_predictions.
    """
    dataset: ImageFolder = dataloader.dataset  # type: ignore[assignment]
    image_paths = [path for path, _ in dataset.imgs]
    top_k = min(5, len(classes))

    rows: list[dict] = []
    path_idx = 0

    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="Evaluating"):
            images = images.to(device)
            outputs = model(images)
            probs = F.softmax(outputs, dim=1)
            top_probs, top_indices = probs.topk(top_k, dim=1)

            for i in range(images.size(0)):
                true_idx = labels[i].item()
                pred_idx = top_indices[i, 0].item()
                top5 = [
                    {
                        "label": classes[top_indices[i, k].item()],
                        "confidence": round(top_probs[i, k].item(), 4),
                    }
                    for k in range(top_k)
                ]
                rows.append(
                    {
                        "image_path": image_paths[path_idx],
                        "true_label": classes[true_idx],
                        "predicted_label": classes[pred_idx],
                        "confidence": round(top_probs[i, 0].item(), 4),
                        "correct": true_idx == pred_idx,
                        "top5_predictions": json.dumps(top5),
                    }
                )
                path_idx += 1

    return pd.DataFrame(rows)


def print_summary(df: pd.DataFrame) -> None:
    """Print overall accuracy and a per-class accuracy table to stdout.

    Args:
        df: Results DataFrame from run_inference.
    """
    overall_acc = df["correct"].mean() * 100
    print(
        f"\nOverall accuracy: {overall_acc:.2f}%  ({df['correct'].sum()}/{len(df)} correct)\n"
    )

    per_class = (
        df.groupby("true_label")["correct"]
        .agg(correct="sum", total="count")
        .assign(accuracy=lambda x: (x["correct"] / x["total"] * 100).round(2))
        .sort_values("accuracy")
    )
    print("Per-class accuracy (sorted, worst first):")
    print(per_class.to_string())
    print()


def parse_args() -> argparse.Namespace:
    head_cfg = config.training.train_classification_head
    default_test_dir = Path(head_cfg.train_directory).parent / "test"

    parser = argparse.ArgumentParser(
        description="Evaluate a trained model checkpoint on the test split."
    )
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=Path(config.app.model_weights),
        help="Path to a .pth checkpoint (default: config.app.model_weights)",
    )
    parser.add_argument(
        "--test-directory",
        type=Path,
        default=default_test_dir,
        help=f"ImageFolder-structured test directory (default: {default_test_dir})",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Path to write results CSV (default: results.csv next to the checkpoint)",
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--center-crop-size",
        type=int,
        default=head_cfg.center_crop_size,
        help=f"Center crop size applied before normalization (default: {head_cfg.center_crop_size})",  # noqa: E501
    )
    parser.add_argument(
        "--normalize-mean",
        type=float,
        nargs=3,
        default=head_cfg.normalize_mean,
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--normalize-std",
        type=float,
        nargs=3,
        default=head_cfg.normalize_std,
        metavar=("R", "G", "B"),
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device override (default: cuda if available, else cpu)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    device = torch.device(args.device) if args.device else get_device()
    logger.info(f"Using device: {device}")

    model, classes = load_model(args.checkpoint_path, device)

    transform = get_transforms(args.center_crop_size, args.normalize_mean, args.normalize_std)
    dataset = ImageFolder(root=str(args.test_directory), transform=transform)

    if sorted(dataset.classes) != sorted(classes):
        raise ValueError(
            f"Test directory classes don't match checkpoint classes.\n"
            f"Checkpoint ({len(classes)}): {sorted(classes)[:5]}...\n"
            f"Test dir   ({len(dataset.classes)}): {sorted(dataset.classes)[:5]}..."
        )

    logger.info(
        f"Test dataset: {len(dataset)} images across {len(dataset.classes)} classes "
        f"in {args.test_directory}"
    )

    dataloader = DataLoader(
        dataset, batch_size=args.batch_size, shuffle=False, num_workers=4, pin_memory=True
    )

    df = run_inference(model, dataloader, classes, device)

    output_csv = args.output_csv or args.checkpoint_path.parent / "results.csv"
    df.to_csv(output_csv, index=False)
    logger.info(f"Results saved to {output_csv}")

    print_summary(df)


if __name__ == "__main__":
    main()
