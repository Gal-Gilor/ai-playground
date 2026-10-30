FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

# Vertex AI mounts the NVIDIA driver libraries at /usr/local/nvidia/lib64.
# The slim base image does not search there, so torch cannot load libcuda without it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so source changes reuse this layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Download the YOLO weights named in config.yaml at build time.
RUN python -c "from src.settings import model"
