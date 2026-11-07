"""Experiment methods the planner can choose from.

A method is a function registered with @register:

    method(images: list[Path], params: dict, out_dir: Path, overlay: list[str] = ()) -> {
        "predictions": {image stem: [{"area_px", "eq_diameter_px", "aspect_ratio",
                                      "mean_intensity", "touches_edge"}, ...]},
        "exclude_edge": bool,            # whether edge grains were dropped, so they are scored like for like
        "overlays": [path, ...],         # contour overlays for the image stems in `overlay`, shown to the reviewer
        "checks": {name: bool, ...},     # the method's own sanity checks; any False fails the iteration
    }

A method measures; it never scores. The scorer, outside this package, compares its predictions with the truth,
and a test (tests/test_leakage.py) fails if a file here touches the ground truth or the split.
Its docstring is shown to the planner, so say what it measures and which params it takes.
Put each new method in its own module next to this file, with a test in tests/,
and import the module at the bottom of this file.
"""

import inspect
from typing import Callable

METHODS: dict[str, Callable] = {}


def register(fn: Callable) -> Callable:
    METHODS[fn.__name__] = fn
    return fn


def describe() -> str:
    return "\n".join(f"- {name}: {inspect.getdoc(fn) or 'no description'}" for name, fn in sorted(METHODS.items()))


# Import method modules here, after register is defined.
from src.methods import watershed  # noqa: E402,F401
