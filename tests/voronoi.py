"""A synthetic micrograph built in code: Voronoi grains with dark boundary lines and exact labels.

Used instead of copying images of unknown licence into the repository.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.spatial import cKDTree
from skimage.measure import regionprops
from skimage.segmentation import find_boundaries

UM_PER_PX = 0.5
SCRATCH, PORE = 60, 120  # codes of the synthetic set's defect masks


def voronoi_micrograph(shape=(240, 320), n_grains=40, seed=0, noise=0.03, stretch=1.0):
    """Return (uint8 image, uint16 labels). Every pixel belongs to a grain, as in the synthetic set.

    stretch > 1 elongates the grains along x by about that factor (columnar / elongated morphologies).
    """
    rng = np.random.default_rng(seed)
    h, w = shape
    seeds = rng.uniform([0, 0], [h, w / stretch], size=(n_grains, 2))
    yy, xx = np.mgrid[:h, :w]
    _, nearest = cKDTree(seeds).query(np.c_[yy.ravel(), xx.ravel() / stretch])
    labels = (nearest.reshape(h, w) + 1).astype(np.uint16)
    image = rng.uniform(0.45, 0.9, n_grains + 1)[labels]
    image[find_boundaries(labels, mode="inner")] = 0.15  # dark lines about 2 px wide
    image += rng.normal(0, noise, image.shape)
    return (np.clip(image, 0, 1) * 255).astype(np.uint8), labels


def add_defects(image: np.ndarray):
    """Plant one dark and one bright straight scratch and three dark round pores.

    Returns (image, defect mask) with the synthetic set's codes: 60 = scratch, 120 = pore.
    Positions are fixed fractions of the image size, so the answer is known.
    """
    from skimage.draw import disk as draw_disk, line
    from skimage.morphology import binary_dilation, disk

    image = image.copy()
    h, w = image.shape
    mask = np.zeros((h, w), np.uint8)
    for (r0, c0, r1, c1), gray in [((0.13, 0.15, 0.67, 0.75), 40), ((0.87, 0.12, 0.40, 0.82), 230)]:
        thin = np.zeros((h, w), bool)
        rr, cc = line(int(r0 * h), int(c0 * w), int(r1 * h), int(c1 * w))
        thin[rr, cc] = True
        thick = binary_dilation(thin, disk(1))
        image[thick] = gray
        mask[thick] = SCRATCH
    for r, c in [(0.25, 0.80), (0.75, 0.30), (0.20, 0.40)]:
        rr, cc = draw_disk((int(r * h), int(c * w)), 5, shape=(h, w))
        image[rr, cc] = 18
        mask[rr, cc] = PORE
    return image, mask


def touches_edge(region, shape) -> bool:
    r0, c0, r1, c1 = region.bbox
    return r0 == 0 or c0 == 0 or r1 == shape[0] or c1 == shape[1]


def write_synthetic_dataset(root: Path, images: list[tuple[str, float, int]], defects: bool = False) -> Path:
    """Write images [(name, corruption_level, seed)] in the layout of 90_SYNTHETIC_exact_ground_truth.

    With defects=True the corrupted images carry planted scratches and pores (see add_defects).
    """
    base = root / "90_SYNTHETIC_exact_ground_truth"
    for sub in ["corrupted", "clean", "labels_grain", "artifact_mask"]:
        (base / sub).mkdir(parents=True, exist_ok=True)
    image_rows, grain_rows = [], []
    for name, level, seed in images:
        image, labels = voronoi_micrograph(seed=seed)
        Image.fromarray(image).save(base / "clean" / f"{name}.png")
        defect_mask = np.zeros(image.shape, np.uint8)
        if defects:
            image, defect_mask = add_defects(image)
        Image.fromarray(image).save(base / "corrupted" / f"{name}.png")
        Image.fromarray(defect_mask).save(base / "artifact_mask" / f"{name}.png")
        Image.fromarray(labels).save(base / "labels_grain" / f"{name}.png")
        regions = regionprops(labels)
        interior = []
        for r in regions:
            edge = touches_edge(r, labels.shape)
            eq_um = r.equivalent_diameter_area * UM_PER_PX
            grain_rows.append(dict(image=name, grain_id=r.label, phase=0, area_um2=r.area * UM_PER_PX**2,
                                   eq_diameter_um=eq_um, aspect_ratio=1.0, orientation_deg=0.0, touches_edge=int(edge)))
            if not edge:
                interior.append(eq_um)
        image_rows.append(dict(image=name, family="voronoi", um_per_px=UM_PER_PX, corruption_level=level,
                               n_grains=len(regions), mean_eq_diameter_um=float(np.mean(interior)),
                               mean_aspect_ratio=1.0, phase1_area_fraction=0.0, artifact_area_fraction=0.0,
                               magnification_set=""))
    pd.DataFrame(image_rows).to_csv(base / "ground_truth_images.csv", index=False)
    pd.DataFrame(grain_rows).to_csv(base / "ground_truth_grains.csv", index=False)
    return root
