from pathlib import Path

from scripts.create_test_split import create_test_split


def make_train(root: Path) -> Path:
    """Create a train directory with 10 images for breed_a and 3 for breed_b."""
    train = root / "train"
    for breed, count in {"breed_a": 10, "breed_b": 3}.items():
        (train / breed).mkdir(parents=True)
        for i in range(count):
            (train / breed / f"{i}.jpg").touch()
    return train


def names(directory: Path) -> set[str]:
    """Return the JPEG file names in a directory."""
    return {p.name for p in directory.glob("*.jpg")}


def test_split_is_stratified(tmp_path: Path) -> None:
    """Each breed contributes its own fraction, and too-small breeds are skipped."""
    train = make_train(tmp_path)
    result = create_test_split(train, test_size=0.2)
    assert result == (2, 1)
    assert len(names(tmp_path / "test" / "breed_a")) == 2
    assert not (tmp_path / "test" / "breed_b").exists()


def test_same_seed_gives_same_test_files(tmp_path: Path) -> None:
    """Two fresh copies split with the same seed pick the same test files."""
    first = make_train(tmp_path / "one")
    second = make_train(tmp_path / "two")
    create_test_split(first, test_size=0.2, seed=42)
    create_test_split(second, test_size=0.2, seed=42)
    assert names(tmp_path / "one" / "test" / "breed_a") == names(
        tmp_path / "two" / "test" / "breed_a"
    )


def test_different_seed_changes_test_files(tmp_path: Path) -> None:
    """Different seeds pick different test files."""
    first = make_train(tmp_path / "one")
    second = make_train(tmp_path / "two")
    create_test_split(first, test_size=0.2, seed=42)
    create_test_split(second, test_size=0.2, seed=7)
    assert names(tmp_path / "one" / "test" / "breed_a") != names(
        tmp_path / "two" / "test" / "breed_a"
    )


def test_rerun_moves_nothing(tmp_path: Path) -> None:
    """A second run on the same folder moves no more files."""
    train = make_train(tmp_path)
    create_test_split(train, test_size=0.2)
    before = names(tmp_path / "test" / "breed_a")
    assert create_test_split(train, test_size=0.2) == (0, 1)
    assert names(tmp_path / "test" / "breed_a") == before
