"""Build step images with Cloud Build and record their tags.

Each image is built from a project folder in the repository and tagged with the short SHA
of the latest commit touching that folder. A folder with uncommitted or untracked changes
gets a `<sha>-dirty-<UTC timestamp>` tag instead, so a run never reuses an image built from
different code.

Usage (from project root):
    python -m pipelines.images dog-detection
    python -m pipelines.images --help
"""

import argparse
import json
import logging
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path

from settings import config

logger = logging.getLogger(__name__)

PIPELINE_DIRECTORY = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIRECTORY.parent
IMAGE_TAGS_PATH = PIPELINE_DIRECTORY / "image_tags.json"
MAKE_TARGETS = {
    "dog-detection": "build-detection",
    "dog-breed-classifier": "build-classifier",
}


def git(*args: str) -> str:
    """Run a git command at the repository root and return its stripped output.

    Args:
        *args (str): Arguments passed to git.

    Returns:
        str: The command's standard output without surrounding whitespace.
    """
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def image_tag(project: str) -> str:
    """Return the image tag for a project folder.

    Args:
        project (str): Folder name under the repository root.

    Returns:
        str: The short SHA of the latest commit touching the folder, with a
            `-dirty-<UTC timestamp>` suffix when the folder has uncommitted or untracked
            changes.
    """
    sha = git("log", "-1", "--format=%h", "--", project)
    if git("status", "--porcelain", "--", project):
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"{sha}-dirty-{timestamp}"
    return sha


def _load_image_tags() -> dict[str, str]:
    """Load the recorded image URIs, keyed by project folder name."""
    if not IMAGE_TAGS_PATH.exists():
        return {}
    return json.loads(IMAGE_TAGS_PATH.read_text())


def build_image(project: str) -> str:
    """Build a project's image with Cloud Build and record its URI.

    Args:
        project (str): Folder name under the repository root. The folder must contain a
            Dockerfile.

    Returns:
        str: The full URI of the pushed image.
    """
    uri = f"{config.vertex_ai.artifact_registry}/{project}:{image_tag(project)}"
    logger.info("Building %s", uri)
    subprocess.run(
        [
            "gcloud",
            "builds",
            "submit",
            str(REPO_ROOT / project),
            "--tag",
            uri,
            "--project",
            config.vertex_ai.project,
            "--region",
            config.vertex_ai.region,
            "--timeout",
            "3600s",
            "--machine-type",
            "e2-highcpu-8",
        ],
        check=True,
    )
    image_tags = _load_image_tags()
    image_tags[project] = uri
    IMAGE_TAGS_PATH.write_text(json.dumps(image_tags, indent=2) + "\n")
    logger.info("Recorded %s in %s", uri, IMAGE_TAGS_PATH)
    return uri


def built_image(project: str) -> str:
    """Return the URI of the last image built for a project.

    Args:
        project (str): Folder name under the repository root.

    Raises:
        RuntimeError: If no image has been built for the project.

    Returns:
        str: The full image URI recorded by `build_image`.
    """
    uri = _load_image_tags().get(project)
    if uri is None:
        raise RuntimeError(
            f"No image recorded for {project}. Run `make {MAKE_TARGETS[project]}` first."
        )
    return uri


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(description="Build a project image with Cloud Build.")
    parser.add_argument(
        "project", choices=sorted(MAKE_TARGETS), help="Project folder to build"
    )
    return parser.parse_args()


def main() -> None:
    """Parse arguments and build the requested image."""
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    build_image(args.project)


if __name__ == "__main__":
    main()
