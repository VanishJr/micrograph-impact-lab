"""Smoke test of the watershed method on a Voronoi micrograph with known grains, and on one real 316L image."""

from pathlib import Path

import numpy as np
import pytest

from src import evaluate
from src.methods import METHODS
from tests.voronoi import write_synthetic_dataset

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
