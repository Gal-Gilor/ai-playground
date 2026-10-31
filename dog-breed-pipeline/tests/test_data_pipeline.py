from pathlib import Path

import pytest
import yaml
from kfp import compiler

from pipelines.data import build_data_pipeline
from settings import config


@pytest.fixture
def compiled_path(tmp_path: Path) -> Path:
    """Compile the data pipeline with a placeholder image URI."""
    path = tmp_path / "data.yaml"
    compiler.Compiler().compile(build_data_pipeline("det:t1"), str(path))
    return path


@pytest.fixture
def pipeline_spec(compiled_path: Path) -> dict:
    """Load the compiled pipeline spec."""
    with compiled_path.open() as file:
        return yaml.safe_load(file)


def _container(pipeline_spec: dict, executor: str) -> dict:
    return pipeline_spec["deploymentSpec"]["executors"][executor]["container"]


def _resolved_args(pipeline_spec: dict, task_name: str) -> list[str]:
    """Return a task's container args with constant input parameters filled in."""
    task = pipeline_spec["root"]["dag"]["tasks"][task_name]
    constants = {
        name: value["runtimeValue"]["constant"]
        for name, value in task["inputs"]["parameters"].items()
    }
    executor = pipeline_spec["components"][task["componentRef"]["name"]]["executorLabel"]
    resolved = []
    for arg in _container(pipeline_spec, executor)["args"]:
        for name, value in constants.items():
            arg = arg.replace(f"{{{{$.inputs.parameters['{name}']}}}}", value)
        resolved.append(arg)
    return resolved


def test_data_pipeline_compiles(compiled_path: Path, pipeline_spec: dict) -> None:
    """The data pipeline compiles to a spec named dog-breed-data."""
    assert compiled_path.exists()
    assert pipeline_spec["pipelineInfo"]["name"] == "dog-breed-data"


def test_detect_dogs_uses_detection_image_and_gpu(pipeline_spec: dict) -> None:
    """The detect step runs the detection image on the configured GPU type."""
    container = _container(pipeline_spec, "exec-detect-dogs")
    assert container["image"] == "det:t1"
    assert container["resources"]["accelerator"]["type"] == config.vertex_ai.accelerator_type


def test_detect_dogs_reads_raw_data_through_gcs_mount(pipeline_spec: dict) -> None:
    """Detection reads the public raw data through the /gcs mount, not over gs:// URLs."""
    args = _resolved_args(pipeline_spec, "detect-dogs")
    assert "/gcs/pooch-perfect-public/data/labels.csv" in args
    assert "/gcs/pooch-perfect-public/data/raw" in args
    assert "/tmp/detections.checkpoint.jsonl" in args


def test_detect_dogs_uses_a_small_machine(pipeline_spec: dict) -> None:
    """Detection is I/O bound, so it requests a smaller machine than training."""
    resources = _container(pipeline_spec, "exec-detect-dogs")["resources"]
    assert resources["cpuLimit"] == 4.0
    assert resources["memoryLimit"] == 15.0
