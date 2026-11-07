"""Methods measure, the evaluator scores: no file in src/methods/ may touch the ground truth or the split."""

from pathlib import Path

import pytest

METHODS_DIR = Path(__file__).resolve().parents[1] / "src" / "methods"
FORBIDDEN = ["ground_truth", "labels_", "masks", "artifact_mask", "holdout", "splits", "evaluate"]


def leaks(text: str) -> list[str]:
    return [token for token in FORBIDDEN if token in text]


def test_the_scanner_flags_a_planted_leak():
    assert leaks("from src.evaluate import truth") == ["evaluate"]
    assert leaks("np.array(Image.open(root / 'labels_grain' / name))") == ["labels_"]


@pytest.mark.parametrize("path", sorted(METHODS_DIR.glob("*.py")), ids=lambda p: p.name)
def test_methods_do_not_touch_ground_truth(path):
    assert leaks(path.read_text()) == [], f"{path.name} mentions ground truth or the split"
