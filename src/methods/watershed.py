"""Classical grain segmentation: denoise, boundary map, distance-transform watershed."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2gray
from skimage.feature import peak_local_max
from skimage.filters import gaussian, median, sobel, threshold_otsu
from skimage.measure import label
from skimage.draw import line as draw_line
from skimage.measure import regionprops
from skimage.morphology import (
    binary_dilation, binary_opening, black_tophat, disk, h_maxima, remove_small_objects, white_tophat,
)
from skimage.transform import probabilistic_hough_line
from skimage.segmentation import clear_border, relabel_sequential
from skimage.segmentation import watershed as skwatershed

from src.methods import register
from src.methods.common import measure_grains, save_labels, save_overlay

DEFAULTS = {
    "denoise": "gaussian",
    "sigma": 1.0,
    "boundary": "tophat",
    "line_width_px": 4,
    "markers": "peaks",
    "h_px": 2.0,
    "min_distance": 8,
    "footprint": 15,
    "min_area_px": 40,
    "exclude_edge": False,
    "fill_boundaries": True,
    "detect_scratches": False,
    "scratch_min_length_px": 200,
    "detect_pores": False,
    "pore_max_area_px": 200,
}
SCRATCH, PORE = 1, 2  # values in the returned defect maps
# 0.25 degree steps: with the default 1 degree, a 300 px line drifts 5 px off a 3 px scratch and breaks up
HOUGH_THETA = np.linspace(-np.pi / 2, np.pi / 2, 720, endpoint=False)
CHOICES = {
    "denoise": ("none", "gaussian", "median"),
    "boundary": ("threshold", "sobel", "tophat"),
    "markers": ("peaks", "hmaxima"),
}


@register
def watershed(images, params, out_dir, overlay=()):
    """Segment grains with a classical pipeline and measure each one, in pixels.

    Pipeline: grayscale -> denoise -> boundary map -> distance transform of the non-boundary pixels
    -> markers on the distance transform -> watershed -> drop small regions -> (optional) drop edge grains.
    Params (all optional, defaults in brackets):
    - denoise: "none" | "gaussian" | "median" ["gaussian"]
    - sigma: 0.5-5, gaussian sigma or median disk radius in px [1.0]
    - boundary: how boundary pixels are found ["tophat"]
        "threshold": darker than the Otsu threshold of the whole image (dark grains become boundary too);
        "sobel": gradient magnitude above its Otsu threshold (responds to every edge, incl. scratches);
        "tophat": black top-hat, i.e. dark lines thinner than line_width_px, whatever the grain's gray level.
    - line_width_px: 1-15, disk radius of the top-hat; boundaries wider than this are missed [4]
    - markers: how grains are seeded on the distance transform ["peaks"]
        "peaks": one marker per local maximum, at least min_distance apart (elongated grains get several);
        "hmaxima": one marker per maximum that rises at least h_px above its surroundings, whatever the spacing,
        so a long grain whose ridge is nearly flat gets one marker. min_distance and footprint are ignored.
    - h_px: 1-5 px, height for "hmaxima"; larger merges more [2.0]
    - min_distance: 2-60 px, "peaks" only: minimum distance between two markers; larger merges grains, smaller over-segments them [8]
    - footprint: 3-61 px, odd, "peaks" only: window in which a marker must be the maximum [15]
    - min_area_px: 0-5000, regions smaller than this are dropped [40]
    - exclude_edge: drop grains touching the image edge [false]
    - fill_boundaries: true assigns boundary pixels to the nearest grain, tiling the image;
        false leaves boundary pixels unassigned [true]
    Defects, found before the watershed; their pixels are taken out of the boundary map,
    so a scratch no longer cuts grains and a pore is no longer outlined as a grain:
    - detect_scratches: find straight dark or bright lines (Hough on top-hat line maps) [false]
    - scratch_min_length_px: 50-500, shorter straight lines are kept as boundaries [200];
        long straight grain boundaries (columnar grains) can be taken for scratches if this is too low
    - detect_pores: find small, round, very dark spots (darker than half the Otsu level) [false]
    - pore_max_area_px: 20-500, larger dark blobs are not pores [200]
    Found defects are listed per image (type, area_px, length_px, centroid) and drawn on the contour
    drawings: scratches blue, pores yellow.
    Only the params above are accepted; any other key fails the run.
    Writes a label image per input to out_dir/labels/; the loop itself picks the few images that get contour drawings.
    """
    unknown = set(params) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown params {sorted(unknown)}; allowed: {sorted(DEFAULTS)}")
    p = {**DEFAULTS, **params}
    for key, allowed in CHOICES.items():
        if p[key] not in allowed:
            raise ValueError(f"{key}={p[key]!r}, expected one of {allowed}")

    out_dir = Path(out_dir)
    predictions, overlays, defects, defect_maps = {}, [], {}, {}
    detecting = p["detect_scratches"] or p["detect_pores"]
    for path in map(Path, images):
        raw = np.array(Image.open(path))
        labels, gray, found = segment(raw, p)
        name = path.stem
        predictions[name] = measure_grains(labels, gray)
        defects[name] = describe_defects(found)
        if detecting:
            defect_maps[name] = found
        save_labels(labels, out_dir / "labels" / f"{name}.png")
        if name in overlay:
            overlays.append(str(save_overlay(raw, labels, out_dir / "overlays" / name, defects=found)))
    return {
        "predictions": predictions,
        "defects": defects,
        "defect_maps": defect_maps,
        "exclude_edge": bool(p["exclude_edge"]),
        "params_used": p,
        "overlays": overlays,
        "checks": {"every_image_has_grains": all(len(g) > 0 for g in predictions.values())},
    }


def find_defects(smooth: np.ndarray, p: dict) -> np.ndarray:
    """uint8 map: SCRATCH for straight lines, PORE for small round very dark spots, 0 elsewhere."""
    found = np.zeros(smooth.shape, np.uint8)
    if p["detect_scratches"]:
        w = int(p["line_width_px"])
        dark, bright = black_tophat(smooth, disk(w)), white_tophat(smooth, disk(w))
        lines = (dark > threshold_otsu(dark)) | (bright > threshold_otsu(bright))
        segments = probabilistic_hough_line(
            lines, threshold=50, line_length=int(p["scratch_min_length_px"]), line_gap=10,
            theta=HOUGH_THETA, rng=0,
        )
        drawn = np.zeros(smooth.shape, bool)
        for (x0, y0), (x1, y1) in segments:
            rr, cc = draw_line(y0, x0, y1, x1)
            drawn[rr, cc] = True
        found[binary_dilation(drawn, disk(1)) & binary_dilation(lines, disk(1))] = SCRATCH
    if p["detect_pores"]:
        blobs = binary_opening(smooth < 0.5 * threshold_otsu(smooth), disk(2))  # the opening drops thin lines
        for r in regionprops(label(blobs)):
            circularity = 4 * np.pi * r.area / max(r.perimeter, 1) ** 2
            if 12 <= r.area <= p["pore_max_area_px"] and circularity >= 0.6:
                found[tuple(r.coords.T)] = PORE
    return found


def describe_defects(found: np.ndarray) -> list[dict]:
    items = []
    for kind, value in [("scratch", SCRATCH), ("pore", PORE)]:
        for r in regionprops(label(found == value)):
            items.append({
                "type": kind,
                "area_px": int(r.area),
                "length_px": round(float(r.axis_major_length), 1),
                "centroid": [round(float(r.centroid[0]), 1), round(float(r.centroid[1]), 1)],
            })
    return items


def segment(raw: np.ndarray, p: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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

    found = find_defects(smooth, p)
    if found.any():
        boundary = boundary & ~binary_dilation(found > 0, disk(2))

    interior = ~boundary
    distance = ndi.distance_transform_edt(interior)
    if p["markers"] == "hmaxima":
        markers = label(h_maxima(distance, float(p["h_px"])).astype(bool) & interior)
    else:
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
    return labels, gray, found
