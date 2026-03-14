.PHONY: clean-cache upload download update-labels

clean-cache:
	find . -path ./.venv -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -not -path './.venv/*' -name "*.pyc" -exec rm -f {} +
	rm -rf .pytest_cache .ruff_cache

upload:
	uv run python scripts/upload_folder.py

download:
	uv run python scripts/download_folder.py

update-labels:
	uv run python scripts/update_labels.py
