from pathlib import Path

from kfp import compiler

from pipelines.components import gcs_to_fuse
from pipelines.data import build_data_pipeline


def test_data_pipeline_compiles(tmp_path: Path) -> None:
    """The data pipeline compiles, which catches wiring and type errors before submitting."""
    path = tmp_path / "data.yaml"
    compiler.Compiler().compile(build_data_pipeline("det:t1"), str(path))
    assert path.exists()


def test_gcs_to_fuse_maps_uri_to_mount_path() -> None:
    """A gs:// URI maps to its path under the Cloud Storage FUSE mount."""
    assert gcs_to_fuse("gs://bucket/data/raw") == "/gcs/bucket/data/raw"
