from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from ultralytics import YOLO


class Envs(BaseSettings):
    """Project configuration settings."""

    PATH_TO_CONFIG: str = "config.yaml"
    GOOGLE_CLOUD_PROJECT: str = "pooch-perfect"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_CLOUD_BUCKET: str = "pooch-perfect-public"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


env_variables = Envs()


def load_config(path_to_config: str | Path) -> dict:
    """Load configuration from a YAML file.

    Args:
        path_to_config (str | Path): Path to the YAML configuration file.

    Returns:
        dict: The configuration parsed from the YAML file.
    """

    with open(path_to_config, "r") as file:
        return yaml.safe_load(file)


config = load_config(env_variables.PATH_TO_CONFIG)


@lru_cache(maxsize=1)
def load_yolo_model(path_to_model: str | Path) -> YOLO:
    """Load a YOLO model from the specified path.

    Args:
        path_to_model (str | Path): Path to the YOLO model file.

    Returns:
        YOLO: The loaded YOLO model.
    """
    return YOLO(path_to_model)


model = load_yolo_model(config["path-to-detection-model"])
