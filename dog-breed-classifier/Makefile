.PHONY: unpack crop train-split test-split train pipeline reset

unpack:
	uv run python -m training.scripts.unpack_bounding_boxes

crop:
	uv run python -m training.scripts.crop_images

train-split:
	uv run python -m training.scripts.create_train_split

test-split:
	uv run python -m training.scripts.create_test_split

train:
	uv run python -m training.scripts.train_classifier

pipeline: unpack crop train-split test-split train

reset:
	rm -rf training/data/cropped_images/ training/data/train/ training/data/test/
	rm -f training/data/exploded_labels.csv training/data/cropped_image_labels.csv
