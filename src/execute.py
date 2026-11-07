"""Step 3, execute: run the planned method on the dev images, then score it with the evaluator.

A failing method is recorded, not raised.
The method sees image paths only; src/evaluate.py alone reads the ground truth.

    uv run python -m src.execute --dataset synthetic --out results/baseline/synthetic   # no API calls
"""

import argparse
import json
import logging
import time
from pathlib import Path

import pandas as pd

from src import evaluate, splits
from src.methods import METHODS
from src.state import write_json

log = logging.getLogger(__name__)


def run(cfg: dict, plan: dict, it_dir: Path, split: str = "dev") -> dict:
    dataset = cfg["eval"]["dataset"]
    out_dir = it_dir / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    execution = {"ok": False, "dataset": dataset, "split": split, "method": plan["method"], "params": plan["params"]}
    try:
        images = splits.image_paths(cfg, dataset, split)
        overlay = evaluate.representative(cfg, dataset, split)
        result = METHODS[plan["method"]](images, plan["params"], out_dir, overlay=overlay)
        _write_predictions(result["predictions"], out_dir / "predictions.csv")
        scored = evaluate.evaluate(cfg, dataset, split, result["predictions"], result["exclude_edge"])
        execution.update(
            ok=True,
            n_images=len(images),
            metrics=scored["metrics"],
            by_corruption_level=scored["by_corruption_level"],
            by_family=scored["by_family"],
            per_image=scored["per_image"],
            checks=result.get("checks", {}),
            overlays=[str(Path(p).relative_to(it_dir)) for p in result.get("overlays", [])],
        )
    except Exception as e:  # the loop must survive a broken experiment and record why it broke
        log.exception("execute: %s failed", plan["method"])
        execution["error"] = f"{type(e).__name__}: {e}"
    execution.setdefault("metrics", {})
    execution.setdefault("checks", {})
    execution.setdefault("overlays", [])
    execution["seconds"] = round(time.monotonic() - started, 2)
    write_json(it_dir / "execute.json", execution)
    log.info("execute: ok=%s metrics=%s", execution["ok"], execution["metrics"])
    return execution


def _write_predictions(predictions: dict, path: Path) -> None:
    rows = [{"image": name, "grain": i + 1, **g} for name, grains in predictions.items() for i, g in enumerate(grains)]
    pd.DataFrame(rows).to_csv(path, index=False, float_format="%.4g")


def main(argv=None) -> None:
    from src.config import load_config

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dataset", choices=splits.DATASETS)
    parser.add_argument("--method", default="watershed", choices=sorted(METHODS))
    parser.add_argument("--params", default="{}", help="JSON object of method params")
    parser.add_argument("--out", required=True, help="directory for execute.json and outputs/")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config)
    if args.dataset:
        cfg["eval"]["dataset"] = args.dataset
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    execution = run(cfg, {"method": args.method, "params": json.loads(args.params)}, out, split="dev")
    print(json.dumps({k: execution.get(k) for k in ["ok", "dataset", "split", "metrics", "by_corruption_level", "error"]}, indent=2))


if __name__ == "__main__":
    main()
