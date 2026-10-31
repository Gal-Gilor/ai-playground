FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

# Vertex AI mounts the NVIDIA driver libraries at /usr/local/nvidia/lib64.
# The slim base image does not search there, so torch cannot load libcuda without it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONUNBUFFERED=1 \
    TORCH_HOME=/opt/torch \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install dependencies first so source changes reuse this layer. The project has no build
# backend, so there is nothing to install beyond the dependencies.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Download the EfficientNet-B4 weights at build time.
RUN python -c "from torchvision.models import EfficientNet_B4_Weights, efficientnet_b4; efficientnet_b4(weights=EfficientNet_B4_Weights.DEFAULT)"

COPY . .
