from pathlib import Path

import pytest
from kfp import compiler

from pipelines.run import parse_overrides
from pipelines.training import build_training_pipeline


def test_training_pipeline_compiles(tmp_path: Path) -> None:
    """The training pipeline compiles, which catches wiring and type errors early."""
    path = tmp_path / "training.yaml"
    compiler.Compiler().compile(build_training_pipeline("cls:t1"), str(path))
    assert path.exists()


def test_parse_overrides_casts_to_the_default_type() -> None:
    defaults = {"head_epochs": 15, "head_learning_rate": 1e-3}
    overrides = parse_overrides(["head_epochs=2", "head_learning_rate=3e-4"], defaults)
    assert overrides == {"head_epochs": 2, "head_learning_rate": 0.0003}
    assert isinstance(overrides["head_epochs"], int)


def test_parse_overrides_rejects_unknown_parameter() -> None:
    with pytest.raises(ValueError, match="head_lr"):
        parse_overrides(["head_lr=0.1"], {"head_learning_rate": 1e-3})
