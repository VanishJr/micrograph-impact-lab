"""The evaluator: the only code that reads ground truth (CSV files, label images, masks).

Methods return predictions only; this module scores them.
Conventions, checked against the synthetic set:
- count: predicted grains vs all ground-truth grains, including those touching the image edge
  (as `n_grains` in ground_truth_images.csv); when the method excluded edge grains, vs interior grains only.
- size: mean equivalent diameter of interior grains on both sides
  (as `mean_eq_diameter_um`, which averages grains with touches_edge == 0 only).
"""

import statistics
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from skimage.measure import label, regionprops

from src.splits import STEEL_316L, STEEL_316L_FOLDER, SYNTHETIC, load

METRICS_DOC = """The evaluator reports, over the dev images (errors are relative, 0.10 = 10 %):
- max_rel_error: max(median_count_rel_error, median_size_rel_error); the main metric, target <= 0.10.
- median_count_rel_error: median |predicted grain count - true count| / true count.
- median_size_rel_error: median |predicted - true| / true mean equivalent diameter of interior grains.
- median_count_bias, median_size_bias: the same, signed (> 0: too many grains / too large).
- n_images: images scored.
Per image errors, and (synthetic) medians per corruption_level, are in execute.json."""


def truth(cfg: dict, dataset: str, split: str, names: list[str]) -> dict:
    """Ground truth per image: n_all, n_interior, mean_eq_interior, scale (um per px; 1 for 316L), corruption_level."""
    root = Path(cfg["paths"]["dataset"])
    stems = [Path(n).stem if dataset == "316L" else n for n in names]
    if dataset == "synthetic":
        base = root / SYNTHETIC
        images = pd.read_csv(base / "ground_truth_images.csv").set_index("image")
        grains = pd.read_csv(base / "ground_truth_grains.csv")
        interior = grains[grains.touches_edge == 0].groupby("image").size()
        return {
            n: {
                "n_all": int(images.at[n, "n_grains"]),
                "n_interior": int(interior.get(n, 0)),
                "mean_eq_interior": float(images.at[n, "mean_eq_diameter_um"]),
                "scale": float(images.at[n, "um_per_px"]),
                "unit": "um",
                "corruption_level": float(images.at[n, "corruption_level"]),
            }
            for n in stems
        }
    if dataset == "316L":
        folder = root / STEEL_316L / STEEL_316L_FOLDER[split] / "masks"
        return {n: truth_from_mask(folder / f"{n}.png") for n in stems}
    raise ValueError(f"unknown dataset {dataset!r}")


def truth_from_mask(path: Path) -> dict:
    """316L: grains are the 4-connected components of mask == 1 (0 is boundary). Sizes in pixels."""
    mask = np.array(Image.open(path))
    regions = regionprops(label(mask == 1, connectivity=1))
    h, w = mask.shape
    interior = [r.equivalent_diameter_area for r in regions
                if not (r.bbox[0] == 0 or r.bbox[1] == 0 or r.bbox[2] == h or r.bbox[3] == w)]
    return {
        "n_all": len(regions),
        "n_interior": len(interior),
        "mean_eq_interior": float(np.mean(interior)) if interior else float("nan"),
        "scale": 1.0,
        "unit": "px",
        "corruption_level": None,
    }


def score(truth_by_image: dict, predictions: dict, exclude_edge: bool) -> dict:
    per_image = {}
    for name, t in truth_by_image.items():
        grains = predictions.get(name)
        if grains is None:
            per_image[name] = {"count_rel_error": -1.0, "size_rel_error": 1.0, "missing": True}
            continue
        n_true = t["n_interior"] if exclude_edge else t["n_all"]
        interior = [g["eq_diameter_px"] for g in grains if not g["touches_edge"]]
        row = {
            "n_true": n_true,
            "n_pred": len(grains),
            "count_rel_error": (len(grains) - n_true) / n_true,
            "mean_eq_true": t["mean_eq_interior"],
        }
        if interior:
            mean_pred = float(np.mean(interior)) * t["scale"]
            row["mean_eq_pred"] = mean_pred
            row["size_rel_error"] = (mean_pred - t["mean_eq_interior"]) / t["mean_eq_interior"]
        else:
            row["size_rel_error"] = 1.0  # no interior grain predicted: counted as a 100 % size error
            row["no_interior_grains"] = True
        row["corruption_level"] = t["corruption_level"]
        per_image[name] = row

    def medians(rows):
        count = [r["count_rel_error"] for r in rows]
        size = [r["size_rel_error"] for r in rows]
        return {
            "median_count_rel_error": statistics.median(abs(x) for x in count),
            "median_size_rel_error": statistics.median(abs(x) for x in size),
            "median_count_bias": statistics.median(count),
            "median_size_bias": statistics.median(size),
            "n_images": len(rows),
        }

    metrics = medians(list(per_image.values()))
    metrics["max_rel_error"] = max(metrics["median_count_rel_error"], metrics["median_size_rel_error"])
    levels: dict[str, list] = {}
    for r in per_image.values():
        if r.get("corruption_level") is not None:
            levels.setdefault(f"{r['corruption_level']:g}", []).append(r)
    by_level = {k: medians(v) for k, v in sorted(levels.items(), key=lambda kv: float(kv[0]))}
    return {"metrics": metrics, "by_corruption_level": by_level, "per_image": per_image}


def evaluate(cfg: dict, dataset: str, split: str, predictions: dict, exclude_edge: bool) -> dict:
    """Score predictions {image stem: [grain, ...]} against every image of the split."""
    names = load(cfg)[dataset][split]
    return score(truth(cfg, dataset, split, names), predictions, exclude_edge)


def representative(cfg: dict, dataset: str, split: str, k: int = 3) -> list[str]:
    """Names (stems) of k images to draw overlays for: lowest, middle and highest corruption (316L: by name)."""
    names = [Path(n).stem for n in load(cfg)[dataset][split]]
    if dataset == "synthetic":
        t = truth(cfg, dataset, split, names)
        names = sorted(names, key=lambda n: (t[n]["corruption_level"], n))
    if len(names) <= k:
        return names
    return [names[round(i * (len(names) - 1) / (k - 1))] for i in range(k)]
