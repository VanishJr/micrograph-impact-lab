"""Smoke test of the watershed method on a Voronoi micrograph with known grains, and on one real 316L image."""

from pathlib import Path

import numpy as np
import pytest

from PIL import Image

from src import evaluate
from src.methods import METHODS
from tests.voronoi import voronoi_micrograph, write_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


def test_watershed_finds_a_plausible_number_of_grains(tmp_path):
    root = write_synthetic_dataset(tmp_path / "dataset", [("voronoi_00", 0.15, 0)])
    image = root / "90_SYNTHETIC_exact_ground_truth" / "corrupted" / "voronoi_00.png"

    result = METHODS["watershed"]([image], {}, tmp_path / "out", overlay=["voronoi_00"])

    n = len(result["predictions"]["voronoi_00"])
    assert 20 <= n <= 60, n  # 40 true grains; a wide bound, this is a smoke test
    assert (tmp_path / "out" / "labels" / "voronoi_00.png").exists()
    assert [Path(p).name for p in result["overlays"]] == ["voronoi_00.jpg"]
    cfg = {"paths": {"dataset": root}, "eval": {"synthetic_variant": "corrupted"}}
    t = evaluate.truth(cfg, "synthetic", "dev", ["voronoi_00"])
    m = evaluate.score(t, result["predictions"], result["exclude_edge"])["metrics"]
    assert np.isfinite(m["max_rel_error"])


def test_watershed_runs_on_a_real_316L_image(tmp_path):
    image = ROOT / "data" / "sample" / "316L" / "images" / "RG10_1_1.jpg"
    result = METHODS["watershed"]([image], {"fill_boundaries": False}, tmp_path)
    assert len(result["predictions"]["RG10_1_1"]) >= 1


def test_unknown_params_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="sigmaa"):
        METHODS["watershed"]([], {"sigmaa": 1}, tmp_path)


def test_hmaxima_markers_over_split_elongated_grains_less_than_peaks(tmp_path):
    image, labels = voronoi_micrograph(shape=(240, 480), n_grains=40, seed=3, stretch=4.0)
    path = tmp_path / "elongated.png"
    Image.fromarray(image).save(path)
    n_true = len(np.unique(labels))
    common = {"min_distance": 8, "footprint": 15}

    def count(params, out):
        return len(METHODS["watershed"]([path], {**common, **params}, tmp_path / out)["predictions"]["elongated"])

    n_peaks = count({"markers": "peaks"}, "peaks")
    n_hmaxima = count({"markers": "hmaxima", "h_px": 2}, "hmaxima")
    assert n_peaks > 1.3 * n_true  # the failure the reviewer saw: ladders of markers along each grain
    assert abs(n_hmaxima - n_true) < abs(n_peaks - n_true), (n_true, n_peaks, n_hmaxima)


def test_unknown_marker_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="markers"):
        METHODS["watershed"]([], {"markers": "random"}, tmp_path)
