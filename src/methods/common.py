"""Helpers shared by methods: measure grains, save label images and overlays."""

from pathlib import Path

import numpy as np
from PIL import Image
from skimage.measure import regionprops
from skimage.segmentation import find_boundaries

OVERLAY_MAX_WIDTH = 1024
OVERLAY_QUALITY = 85


def measure_grains(labels: np.ndarray, gray: np.ndarray) -> list[dict]:
    """One dict per labelled region, in pixels. Label 0 is background."""
    h, w = labels.shape
    grains = []
    for r in regionprops(labels, intensity_image=gray):
        r0, c0, r1, c1 = r.bbox
        minor = r.axis_minor_length
        grains.append(
            {
                "area_px": int(r.area),
                "eq_diameter_px": float(r.equivalent_diameter_area),
                "aspect_ratio": float(r.axis_major_length / minor) if minor > 0 else None,
                "mean_intensity": float(r.intensity_mean),
                "touches_edge": bool(r0 == 0 or c0 == 0 or r1 == h or c1 == w),
            }
        )
    return grains


def save_labels(labels: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(labels.astype(np.uint16)).save(path)


def save_overlay(image: np.ndarray, labels: np.ndarray, path: Path, defects: np.ndarray | None = None) -> Path:
    """Red grain contours over the image, as JPEG (quality 85, at most 1024 px wide).

    With a defect map: value 1 (scratch) drawn blue, value 2 (pore) yellow.
    """
    if image.ndim == 2:
        rgb = np.stack([image] * 3, axis=-1)
    else:
        rgb = image[..., :3].copy()
    rgb = rgb.astype(np.uint8)
    rgb[find_boundaries(labels, mode="inner")] = (255, 0, 0)
    if defects is not None:
        rgb[defects == 1] = (0, 90, 255)
        rgb[defects == 2] = (255, 220, 0)
    out = Image.fromarray(rgb)
    if out.width > OVERLAY_MAX_WIDTH:
        out = out.resize((OVERLAY_MAX_WIDTH, round(out.height * OVERLAY_MAX_WIDTH / out.width)))
    path = path.with_suffix(".jpg")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, quality=OVERLAY_QUALITY)
    return path
