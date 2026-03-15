import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from app.models.config import Config


class Envs(BaseSettings):
    """Project configuration settings."""

    PATH_TO_CONFIG: str = "config.toml"
    GOOGLE_CLOUD_PROJECT: str = "pooch-perfect"
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    GOOGLE_CLOUD_BUCKET: str = "pooch-perfect-public"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


env_variables = Envs()


def load_config(path_to_config: str | Path) -> Config:
    """Load configuration from a TOML file.

    Args:
        path_to_config (str | Path): Path to the TOML configuration file.

    Returns:
        Config: The configuration parsed from the TOML file.
    """

    with open(path_to_config, "rb") as file:
        return Config(**tomllib.load(file))


config: Config = load_config(env_variables.PATH_TO_CONFIG)
