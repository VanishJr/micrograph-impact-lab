"""Scratches and pores: planted in a Voronoi micrograph, found by the method, scored by the evaluator."""

import numpy as np
import pytest
from PIL import Image

from src import evaluate
from src.methods import METHODS
from tests.voronoi import PORE, SCRATCH, add_defects, voronoi_micrograph


@pytest.fixture
def planted(tmp_path):
    image, labels = voronoi_micrograph(shape=(300, 400), n_grains=50, seed=5)
    image, truth = add_defects(image)
    path = tmp_path / "planted.png"
    Image.fromarray(image).save(path)
    return path, labels, truth


def perfect_prediction(truth):
    return np.where(truth == SCRATCH, 1, np.where(truth == PORE, 2, 0)).astype(np.uint8)


def test_perfect_defect_prediction_scores_one(planted):
    _, _, truth = planted
    d = evaluate.score_defects({"planted": truth}, {"planted": perfect_prediction(truth)})
    for kind in ["scratch", "pore"]:
        assert d[kind]["f1"] == pytest.approx(1.0)
        assert d[kind]["detection_rate"] == 1.0
    assert (d["scratch"]["objects_true"], d["pore"]["objects_true"]) == (2, 3)


def test_scratch_pixels_have_a_2px_tolerance(planted):
    _, _, truth = planted
    shifted = np.roll(perfect_prediction(truth) * (truth == SCRATCH), 1, axis=1).astype(np.uint8)
    assert evaluate.score_defects({"planted": truth}, {"planted": shifted})["scratch"]["f1"] == pytest.approx(1.0)


def test_an_empty_prediction_finds_nothing(planted):
    _, _, truth = planted
    d = evaluate.score_defects({"planted": truth}, {"planted": np.zeros_like(truth)})
    assert d["scratch"]["recall"] == 0 and d["pore"]["detection_rate"] == 0


def test_the_method_finds_both_planted_scratches(planted, tmp_path):
    path, _, truth = planted
    result = METHODS["watershed"]([path], {"detect_scratches": True}, tmp_path / "out")

    scratches = [d for d in result["defects"]["planted"] if d["type"] == "scratch"]
    assert scratches and max(d["length_px"] for d in scratches) >= 150
    assert evaluate.score_defects({"planted": truth}, result["defect_maps"])["scratch"]["detection_rate"] == 1.0


def test_the_method_finds_most_planted_pores(planted, tmp_path):
    path, _, truth = planted
    result = METHODS["watershed"]([path], {"detect_pores": True}, tmp_path / "out")

    assert evaluate.score_defects({"planted": truth}, result["defect_maps"])["pore"]["detection_rate"] >= 2 / 3


def test_no_defects_unless_asked(planted, tmp_path):
    path, _, _ = planted
    result = METHODS["watershed"]([path], {}, tmp_path / "out", overlay=["planted"])

    assert result["defects"]["planted"] == []
    assert (tmp_path / "out" / "overlays" / "planted.jpg").exists()
