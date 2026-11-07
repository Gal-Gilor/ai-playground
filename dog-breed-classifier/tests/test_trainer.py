"""Tests for the shared training loop."""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.data import TensorDataset

from config import TrainClassificationHeadConfig
from trainer import train


def _make_loader() -> DataLoader:
    generator = torch.Generator().manual_seed(0)
    images = torch.randn(16, 4, generator=generator)
    labels = torch.randint(0, 3, (16,), generator=generator)
    return DataLoader(TensorDataset(images, labels), batch_size=8)


def _make_model() -> nn.Sequential:
    return nn.Sequential(
        nn.Sequential(nn.Linear(4, 8), nn.Dropout(0.5)),
        nn.Dropout(0.5),
        nn.Linear(8, 3),
    )


def _make_config(tmp_path, epochs: int = 1) -> TrainClassificationHeadConfig:
    return TrainClassificationHeadConfig(
        train_directory=str(tmp_path),
        output_directory=str(tmp_path),
        epochs=epochs,
    )


def test_frozen_modules_stay_in_eval_mode(tmp_path):
    model = _make_model()
    frozen_dropout = model[0][1]
    live_dropout = model[1]
    seen: dict[str, list[bool]] = {"frozen": [], "live": []}

    def record(key):
        def hook(module, inputs, output):
            if torch.is_grad_enabled():  # the training pass; validation runs under no_grad
                seen[key].append(module.training)

        return hook

    frozen_dropout.register_forward_hook(record("frozen"))
    live_dropout.register_forward_hook(record("live"))

    train(
        model,
        _make_loader(),
        _make_loader(),
        _make_config(tmp_path),
        torch.device("cpu"),
        tmp_path,
        torch.ones(3),
        ["a", "b", "c"],
        torch.optim.SGD(model.parameters(), lr=0.1),
        frozen_modules=model[0],
    )

    assert seen["frozen"] and not any(seen["frozen"])
    assert seen["live"] and all(seen["live"])


def test_evaluate_first_keeps_the_starting_model_when_training_does_not_improve(tmp_path):
    model = _make_model()

    metrics = train(
        model,
        _make_loader(),
        _make_loader(),
        _make_config(tmp_path),
        torch.device("cpu"),
        tmp_path,
        torch.ones(3),
        ["a", "b", "c"],
        torch.optim.SGD(model.parameters(), lr=0.0),
        evaluate_first=True,
    )

    assert metrics["best_epoch"] == 0
    assert "best_train_loss" not in metrics
    assert "best_train_acc" not in metrics
    assert torch.load(tmp_path / "best.pth")["epoch"] == 0
