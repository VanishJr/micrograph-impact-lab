"""Fixed dev/holdout split of the images, saved to data/splits.json.

Reads file names only, never ground truth.
The inner loop evaluates on `dev`; `holdout` is used once, by `run.py --final`.

    uv run python -m src.splits   # writes data/splits.json from the dataset in config.yaml
"""

import argparse
import json
import random
import re
from pathlib import Path

SYNTHETIC = "90_SYNTHETIC_exact_ground_truth"
STEEL_316L = "02_316L_stainless_with_grain_masks/Grain"
STEEL_316L_FOLDER = {"dev": "val", "holdout": "test"}
DATASETS = ("synthetic", "316L")
SEED = 0
HOLDOUT_FRACTION = 1 / 3
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def family(name: str) -> str:
    return re.sub(r"_\d+$", "", name)


def make_synthetic_split(names: list[str], seed: int = SEED) -> dict:
    """Per family, about 2/3 of the images go to dev and 1/3 to holdout.

    The magset* images are excluded: they come at 1.0 and 2.0 um/px,
    and their rows in the dataset have no mean grain size and no per-grain rows.
    """
    rng = random.Random(seed)
    excluded = sorted(n for n in names if n.startswith("magset"))
    by_family: dict[str, list[str]] = {}
    for n in sorted(set(names) - set(excluded)):
        by_family.setdefault(family(n), []).append(n)
    dev, holdout = [], []
    for fam in sorted(by_family):
        members = by_family[fam][:]
        rng.shuffle(members)
        k = round(len(members) * HOLDOUT_FRACTION)
        holdout += members[:k]
        dev += members[k:]
    return {"dev": sorted(dev), "holdout": sorted(holdout), "excluded": excluded}


def make_splits(dataset_root: Path, seed: int = SEED) -> dict:
    synthetic = [p.stem for p in (dataset_root / SYNTHETIC / "corrupted").glob("*.png")]
    steel = {  # file names with extension: the 316L images are a mix of .png and .jpg
        split: sorted(p.name for p in (dataset_root / STEEL_316L / folder / "images").iterdir() if p.suffix in IMAGE_SUFFIXES)
        for split, folder in STEEL_316L_FOLDER.items()
    }
    return {
        "seed": seed,
        "synthetic": make_synthetic_split(synthetic, seed),
        "316L": {**steel, "note": "dev = the dataset's val folder, holdout = its test folder; train is unused"},
    }


def load(cfg: dict) -> dict:
    return json.loads(Path(cfg["paths"]["splits"]).read_text())


def image_paths(cfg: dict, dataset: str, split: str) -> list[Path]:
    """Paths of the input images of one split. Only images, never ground truth."""
    names = load(cfg)[dataset][split]
    root = Path(cfg["paths"]["dataset"])
    if dataset == "synthetic":
        folder = root / SYNTHETIC / cfg["eval"]["synthetic_variant"]
        return [folder / f"{n}.png" for n in names]
    if dataset == "316L":
        folder = root / STEEL_316L / STEEL_316L_FOLDER[split] / "images"
        return [folder / n for n in names]
    raise ValueError(f"unknown dataset {dataset!r}, expected one of {DATASETS}")


def main(argv=None) -> None:
    from src.config import load_config

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    splits = make_splits(Path(cfg["paths"]["dataset"]))
    out = Path(cfg["paths"]["splits"])
    out.write_text(json.dumps(splits, indent=2) + "\n")
    for d in DATASETS:
        print(f"{d}: dev {len(splits[d]['dev'])}, holdout {len(splits[d]['holdout'])} -> {out}")


if __name__ == "__main__":
    main()
