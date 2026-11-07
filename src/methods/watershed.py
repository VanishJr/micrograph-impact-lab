"""Classical grain segmentation: denoise, boundary map, distance-transform watershed."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2gray
from skimage.feature import peak_local_max
from skimage.filters import gaussian, median, sobel, threshold_otsu
from skimage.measure import label
from skimage.morphology import black_tophat, disk, remove_small_objects
from skimage.segmentation import clear_border, relabel_sequential
from skimage.segmentation import watershed as skwatershed

from src.methods import register
from src.methods.common import measure_grains, save_labels, save_overlay

DEFAULTS = {
    "denoise": "gaussian",
    "sigma": 1.0,
    "boundary": "tophat",
    "line_width_px": 4,
    "min_distance": 8,
    "footprint": 15,
    "min_area_px": 40,
    "exclude_edge": False,
    "fill_boundaries": True,
}
CHOICES = {"denoise": ("none", "gaussian", "median"), "boundary": ("threshold", "sobel", "tophat")}


@register
def watershed(images, params, out_dir, overlay=()):
    """Segment grains with a classical pipeline and measure each one, in pixels.

    Pipeline: grayscale -> denoise -> boundary map -> distance transform of the non-boundary pixels
    -> one marker per local maximum -> watershed -> drop small regions -> (optional) drop edge grains.
    Params (all optional, defaults in brackets):
    - denoise: "none" | "gaussian" | "median" ["gaussian"]
    - sigma: 0.5-5, gaussian sigma or median disk radius in px [1.0]
    - boundary: how boundary pixels are found ["tophat"]
        "threshold": darker than the Otsu threshold of the whole image (dark grains become boundary too);
        "sobel": gradient magnitude above its Otsu threshold (responds to every edge, incl. scratches);
        "tophat": black top-hat, i.e. dark lines thinner than line_width_px, whatever the grain's gray level.
    - line_width_px: 1-15, disk radius of the top-hat; boundaries wider than this are missed [4]
    - min_distance: 2-60 px, minimum distance between two markers; larger merges grains, smaller over-segments them [8]
    - footprint: 3-61 px, odd, window in which a marker must be the maximum [15]
    - min_area_px: 0-5000, regions smaller than this are dropped [40]
    - exclude_edge: drop grains touching the image edge [false]
    - fill_boundaries: true assigns boundary pixels to the nearest grain, tiling the image;
        false leaves boundary pixels unassigned [true]
    Writes a label image per input to out_dir/labels/ and a contour overlay JPEG for each name in `overlay`.
    """
    unknown = set(params) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown params {sorted(unknown)}; allowed: {sorted(DEFAULTS)}")
    p = {**DEFAULTS, **params}
    for key, allowed in CHOICES.items():
        if p[key] not in allowed:
            raise ValueError(f"{key}={p[key]!r}, expected one of {allowed}")

    out_dir = Path(out_dir)
    predictions, overlays = {}, []
    for path in map(Path, images):
        raw = np.array(Image.open(path))
        labels, gray = segment(raw, p)
        name = path.stem
        predictions[name] = measure_grains(labels, gray)
        save_labels(labels, out_dir / "labels" / f"{name}.png")
        if name in overlay:
            overlays.append(str(save_overlay(raw, labels, out_dir / "overlays" / name)))
    return {
        "predictions": predictions,
        "exclude_edge": bool(p["exclude_edge"]),
        "params_used": p,
        "overlays": overlays,
        "checks": {"every_image_has_grains": all(len(g) > 0 for g in predictions.values())},
    }


def segment(raw: np.ndarray, p: dict) -> tuple[np.ndarray, np.ndarray]:
    gray = rgb2gray(raw[..., :3]) if raw.ndim == 3 else raw.astype(float) / 255.0
    if p["denoise"] == "gaussian":
        smooth = gaussian(gray, sigma=p["sigma"])
    elif p["denoise"] == "median":
        smooth = median(gray, disk(max(1, round(p["sigma"]))))
    else:
        smooth = gray

    if p["boundary"] == "threshold":
        boundary = smooth < threshold_otsu(smooth)
    elif p["boundary"] == "sobel":
        edges = sobel(smooth)
        boundary = edges > threshold_otsu(edges)
    else:
        response = black_tophat(smooth, disk(int(p["line_width_px"])))
        boundary = response > threshold_otsu(response)

    interior = ~boundary
    distance = ndi.distance_transform_edt(interior)
    size = int(p["footprint"]) | 1
    peaks = peak_local_max(distance, min_distance=int(p["min_distance"]),
                           footprint=np.ones((size, size)), labels=label(interior), exclude_border=False)
    markers = np.zeros(distance.shape, dtype=np.int32)
    markers[tuple(peaks.T)] = np.arange(1, len(peaks) + 1)
    labels = skwatershed(-distance, markers, mask=None if p["fill_boundaries"] else interior)

    if p["min_area_px"] > 0:
        labels = remove_small_objects(labels, min_size=int(p["min_area_px"]))
    if p["exclude_edge"]:
        labels = clear_border(labels)
    labels, _, _ = relabel_sequential(labels)
    return labels, gray
