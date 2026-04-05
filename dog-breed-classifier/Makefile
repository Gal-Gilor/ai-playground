.PHONY: unpack crop filter train-split test-split train finetune pipeline reset

unpack:
	uv run python -m scripts.unpack_bounding_boxes

crop:
	uv run python -m scripts.crop_images

filter:
	uv run python -m scripts.filter_visible_dogs

train-split:
	uv run python -m scripts.create_train_split

test-split:
	uv run python -m scripts.create_test_split

train:
	uv run python -m scripts.train_classification_head

finetune:
	uv run python -m scripts.finetune_backbone

pipeline: unpack crop filter train-split test-split train

reset:
	rm -rf data/cropped_images/ data/train/ data/test/
	rm -f data/exploded_labels.csv data/cropped_image_labels.csv data/cropped_visible_labels.csv
