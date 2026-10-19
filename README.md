[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

# AI/ML Playground

A repository for personal AI and Machine Learning projects. Each project is self-contained and at a different stage of development, covering disciplines like Computer Vision, Natural Language Processing, AI Engineering, etc.

## Projects

| Project | Description | Stack |
|---------|-------------|-------|
| [`dog-detection/`](./dog-detection) | YOLO-based dataset preparation pipeline that filters images to keep only those containing a single dog and no people. Feeds labeled data into the [Pooch Perfect](https://github.com/Gal-Gilor/pooch-perfect) dog breed classifier. | Python, Ultralytics YOLO, Google Cloud Compute |
| [`dog-breed-classifier/`](./dog-breed-classifier) | EfficientNet-B4 training pipeline that classifies images of dogs. Fine-tunes a pretrained backbone in two stages (head training → backbone fine-tuning), achieving ~84.7% accuracy across 120 breeds. Powers the [Pooch Perfect](https://github.com/Gal-Gilor/pooch-perfect) app. | Python, PyTorch, EfficientNet-B4, Pydantic, Gemini |

## Data

The raw dataset used across both projects is publicly available on Google Cloud Storage at [pooch-perfect-public](https://console.cloud.google.com/storage/browser/pooch-perfect-public).

## Portfolio

Other repositories:

- [markdown-chunkify](https://github.com/Gal-Gilor/markdown-chunkify) ([PyPI](https://pypi.org/project/markdown-chunkify/)): Python library that splits Markdown into hierarchical sections, keeping code blocks intact and giving each section an id, a parent link and its position in the source, ready for RAG and graph pipelines. Install with `pip install markdown-chunkify`.

- [markdown-mcp](https://github.com/Gal-Gilor/markdown-mcp): MCP server built with FastMCP and FastAPI that exposes [markdown-chunkify](https://github.com/Gal-Gilor/markdown-chunkify) to AI agents as a tool for splitting Markdown documents into hierarchical sections. Deployed to Cloud Run via GitHub Actions.

- [gemini-scribe](https://github.com/Gal-Gilor/gemini-scribe): FastAPI application that converts PDF documents to Markdown using Gemini. Deployed to Cloud Run with async processing and Google Cloud Storage integration.

## License

Licensed under the [Apache License 2.0](LICENSE).
