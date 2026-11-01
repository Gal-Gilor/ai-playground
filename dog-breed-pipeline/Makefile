.PHONY: build-detection build-classifier run-data run-training test lint

RUN_FLAGS = $(if $(WAIT),--wait)

build-detection:
	uv run python -m pipelines.images dog-detection

build-classifier:
	uv run python -m pipelines.images dog-breed-classifier

run-data:
	uv run python -m pipelines.run data $(RUN_FLAGS)

run-training:
	uv run python -m pipelines.run training --dataset-uri $(DATASET_URI) $(foreach p,$(PARAMS),--param $(p)) $(RUN_FLAGS)

test:
	uv run pytest -v

lint:
	uv run ruff check . && uv run ruff format --check .
