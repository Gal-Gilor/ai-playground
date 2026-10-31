"""Compile a pipeline and submit it to Vertex AI Pipelines.

The compiled spec is written to `build/<name>.yaml`. Each run is labeled with the repository
commit it was submitted from and whether tracked files had uncommitted changes.

Usage (from project root):
    python -m pipelines.run data
    python -m pipelines.run data --wait
    python -m pipelines.run --help
"""

import argparse
import logging

from google.cloud import aiplatform
from kfp import compiler
from kfp.dsl.graph_component import GraphComponent

from pipelines.data import build_data_pipeline
from pipelines.images import PIPELINE_DIRECTORY
from pipelines.images import built_image
from pipelines.images import git
from settings import config

logger = logging.getLogger(__name__)

BUILD_DIRECTORY = PIPELINE_DIRECTORY / "build"


def git_labels() -> dict[str, str]:
    """Return the run labels that identify the submitted code.

    Returns:
        dict[str, str]: `git_commit` (short HEAD SHA) and `git_dirty` (`true` when tracked
            files have uncommitted changes).
    """
    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    return {
        "git_commit": git("rev-parse", "--short", "HEAD"),
        "git_dirty": str(dirty).lower(),
    }


def compile_pipeline(name: str, pipeline: GraphComponent) -> str:
    """Compile a pipeline to `build/<name>.yaml`.

    Args:
        name (str): File name for the compiled spec, without extension.
        pipeline (GraphComponent): The pipeline to compile.

    Returns:
        str: Path to the compiled spec.
    """
    BUILD_DIRECTORY.mkdir(exist_ok=True)
    path = str(BUILD_DIRECTORY / f"{name}.yaml")
    compiler.Compiler().compile(pipeline, path)
    logger.info("Compiled %s", path)
    return path


def log_task_outputs(job: aiplatform.PipelineJob) -> None:
    """Log the output artifact URIs of every task in a pipeline run.

    Args:
        job (aiplatform.PipelineJob): The submitted pipeline run.
    """
    for task in job.task_details:
        for output_name, artifact_list in task.outputs.items():
            for artifact in artifact_list.artifacts:
                logger.info("%s.%s: %s", task.task_name, output_name, artifact.uri)


def submit(name: str, template_path: str, wait: bool) -> None:
    """Submit a compiled pipeline to Vertex AI Pipelines.

    Args:
        name (str): Pipeline name, used in the run's display name.
        template_path (str): Path to the compiled pipeline spec.
        wait (bool): Block until the run finishes and log its task outputs.

    Raises:
        RuntimeError: If `wait` is set and the run fails.
    """
    aiplatform.init(project=config.vertex_ai.project, location=config.vertex_ai.region)
    job = aiplatform.PipelineJob(
        display_name=f"dog-breed-{name}",
        template_path=template_path,
        pipeline_root=config.cloud_storage.pipeline_root,
        enable_caching=True,
        labels=git_labels(),
    )
    # The SDK logs the run's console link on submit.
    job.submit(service_account=config.vertex_ai.service_account)
    if not wait:
        return
    try:
        job.wait()
    finally:
        log_task_outputs(job)


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compile a pipeline and submit it to Vertex AI Pipelines."
    )
    subparsers = parser.add_subparsers(dest="pipeline", required=True)
    data_parser = subparsers.add_parser("data", help="Run the data pipeline")
    data_parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the run finishes and log each task's output artifacts",
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments, then compile and submit the requested pipeline."""
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    pipeline = build_data_pipeline(detection_image=built_image("dog-detection"))
    submit(args.pipeline, compile_pipeline(args.pipeline, pipeline), args.wait)


if __name__ == "__main__":
    main()
