from pathlib import Path

import pytest
from kfp import compiler
from pydantic import ValidationError

from pipelines.run import parse_overrides
from pipelines.run import validated_overrides
from pipelines.training import build_training_pipeline
from settings import config


def test_training_pipeline_compiles(tmp_path: Path) -> None:
    """The training pipeline compiles, which catches wiring and type errors early."""
    path = tmp_path / "training.yaml"
    compiler.Compiler().compile(build_training_pipeline("cls:t1"), str(path))
    assert path.exists()


def test_parse_overrides_casts_to_the_default_type() -> None:
    """Override values are cast to the type of the matching default."""
    defaults = {"head_epochs": 15, "head_learning_rate": 1e-3}
    overrides = parse_overrides(["head_epochs=2", "head_learning_rate=3e-4"], defaults)
    assert overrides == {"head_epochs": 2, "head_learning_rate": 0.0003}
    assert isinstance(overrides["head_epochs"], int)


def test_parse_overrides_rejects_unknown_parameter() -> None:
    """An override that names no known parameter raises an error."""
    with pytest.raises(ValueError, match="head_lr"):
        parse_overrides(["head_lr=0.1"], {"head_learning_rate": 1e-3})


def test_parse_overrides_parses_booleans() -> None:
    """A bool default takes `true` or `false` in any case; `bool("false")` would be True."""
    defaults = {"filter_visible": True}
    assert parse_overrides(["filter_visible=False"], defaults) == {"filter_visible": False}
    assert parse_overrides(["filter_visible=TRUE"], defaults) == {"filter_visible": True}
    with pytest.raises(ValueError, match="filter_visible"):
        parse_overrides(["filter_visible=yes"], defaults)


def test_finetune_learning_rate_above_maximum_is_rejected() -> None:
    """A fine-tune learning rate above 1e-4 fails before any job is submitted."""
    with pytest.raises(ValidationError, match="finetune_learning_rate"):
        validated_overrides(["finetune_learning_rate=1e-3"], config.training_parameters)


def test_lr_patience_must_be_below_early_stopping_patience() -> None:
    """A learning-rate patience at or above the early-stopping patience is rejected."""
    with pytest.raises(ValidationError, match="finetune"):
        validated_overrides(["finetune_lr_patience=5"], config.training_parameters)
