"""The dev/holdout split is fixed, stratified by family, and never mixes the two."""

import json
from pathlib import Path

from src.splits import make_synthetic_split

ROOT = Path(__file__).resolve().parents[1]

FAMILIES = ["equiaxed_single", "duplex_50", "columnar_duplex"]
NAMES = [f"{f}_{i:02d}" for f in FAMILIES for i in range(6)] + ["magset0_equiaxed_single_x1", "magset1_duplex_50_x2"]


def test_synthetic_split_is_stratified_disjoint_and_deterministic():
    split = make_synthetic_split(NAMES, seed=0)

    assert split == make_synthetic_split(list(reversed(NAMES)), seed=0)
    assert not set(split["dev"]) & set(split["holdout"])
    assert sorted(split["excluded"]) == ["magset0_equiaxed_single_x1", "magset1_duplex_50_x2"]
    for family in FAMILIES:
        assert sum(n.startswith(family + "_") for n in split["dev"]) == 4
        assert sum(n.startswith(family + "_") for n in split["holdout"]) == 2


def test_committed_splits_file():
    splits = json.loads((ROOT / "data" / "splits.json").read_text())

    assert (len(splits["synthetic"]["dev"]), len(splits["synthetic"]["holdout"])) == (24, 12)
    assert (len(splits["316L"]["dev"]), len(splits["316L"]["holdout"])) == (40, 165)
    for dataset in ["synthetic", "316L"]:
        assert not set(splits[dataset]["dev"]) & set(splits[dataset]["holdout"])
