"""The evaluator scores predictions against known answers: perfect, 10 % too large, 10 % missing."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from skimage.measure import label

from src import evaluate
from src.methods.common import measure_grains
from tests.voronoi import write_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_316L = ROOT / "data" / "sample" / "316L"
IMAGES = [("voronoi_00", 0.15, 0), ("voronoi_01", 0.55, 1)]


@pytest.fixture
def truth(tmp_path):
    root = write_synthetic_dataset(tmp_path / "dataset", IMAGES)
    cfg = {"paths": {"dataset": root}, "eval": {"synthetic_variant": "corrupted"}}
    return evaluate.truth(cfg, "synthetic", "dev", [name for name, _, _ in IMAGES]), root


def perfect(root, name):
    base = root / "90_SYNTHETIC_exact_ground_truth"
    labels = np.array(Image.open(base / "labels_grain" / f"{name}.png"))
    gray = np.array(Image.open(base / "corrupted" / f"{name}.png"))
    return measure_grains(labels, gray)


def test_truth_follows_the_dataset_conventions(truth):
    t, _ = truth
    assert t["voronoi_00"]["n_all"] == 40  # every seed owns a grain
    assert t["voronoi_00"]["n_interior"] < t["voronoi_00"]["n_all"]  # size is measured on interior grains only


def test_perfect_predictions_score_zero(truth):
    t, root = truth
    result = evaluate.score(t, {n: perfect(root, n) for n in t}, exclude_edge=False)
    assert result["metrics"]["max_rel_error"] == pytest.approx(0, abs=1e-9)
    assert set(result["by_corruption_level"]) == {"0.15", "0.55"}
    assert result["by_family"]["voronoi"]["n_images"] == 2
    assert set(result["by_family"]["voronoi"]["by_level"]) == {"0.15", "0.55"}


def test_ten_percent_larger_grains_give_size_error_010(truth):
    t, root = truth
    preds = {n: [{**g, "eq_diameter_px": g["eq_diameter_px"] * 1.1} for g in perfect(root, n)] for n in t}
    m = evaluate.score(t, preds, exclude_edge=False)["metrics"]
    assert m["median_size_rel_error"] == pytest.approx(0.10)
    assert m["median_count_rel_error"] == 0
    assert m["max_rel_error"] == pytest.approx(0.10)


def test_missing_grains_give_count_error(truth):
    t, root = truth
    preds = {n: perfect(root, n)[4:] for n in t}  # 4 of 40 grains missing
    m = evaluate.score(t, preds, exclude_edge=False)["metrics"]
    assert m["median_count_rel_error"] == pytest.approx(0.10)
    assert m["median_count_bias"] == pytest.approx(-0.10)
    assert m["max_rel_error"] == max(m["median_count_rel_error"], m["median_size_rel_error"])
    assert m["worst_family_rel_error"] == pytest.approx(0.10)  # one family here, so it equals the pooled value


def test_excluding_edge_grains_is_compared_like_for_like(truth):
    t, root = truth
    preds = {n: [g for g in perfect(root, n) if not g["touches_edge"]] for n in t}
    assert evaluate.score(t, preds, exclude_edge=True)["metrics"]["max_rel_error"] == pytest.approx(0, abs=1e-9)
    assert evaluate.score(t, preds, exclude_edge=False)["metrics"]["median_count_rel_error"] > 0.1


def test_316L_truth_from_a_sample_mask():
    mask_path = SAMPLE_316L / "masks" / "A_01_01.png"
    t = evaluate.truth_from_mask(mask_path)
    assert t["n_all"] > 0 and np.isfinite(t["mean_eq_interior"])

    labels = label(np.array(Image.open(mask_path)) == 1, connectivity=1)
    preds = {"A_01_01": measure_grains(labels, labels.astype(float))}
    assert evaluate.score({"A_01_01": t}, preds, exclude_edge=False)["metrics"]["max_rel_error"] == pytest.approx(0, abs=1e-9)
