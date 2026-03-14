[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

# AI Playground

A personal repository for AI/ML experiments. Projects are self-contained, each with its own dependencies and configuration.

## Projects

| Project | Description | Stack |
|---------|-------------|-------|
| [`dog-detection/`](./dog-detection) | YOLO-based dataset preparation pipeline that filters images to keep only those containing a single dog and no people. Feeds labeled data into the [Pooch Perfect](https://github.com/Gal-Gilor/pooch-perfect) dog breed classifier. | Python, Ultralytics YOLO, Pandas, Google Cloud Storage, uv |

## Portfolio

Other repositories:

- [gemini-scribe](https://github.com/Gal-Gilor/gemini-scribe): FastAPI service that converts PDF documents to Markdown using Google Gemini AI. Deployed to Cloud Run with async processing and Google Cloud Storage integration.

- [markdown-mcp](https://github.com/Gal-Gilor/markdown-mcp): MCP server built with FastMCP and FastAPI that splits Markdown documents into hierarchical sections, preserving parent-child and sibling relationships.

## License

Licensed under the [Apache License 2.0](LICENSE).
