# results

The state of the inner loop, written by `run.py`.

- `state.json`: the iteration counter and a summary of every iteration; the planner reads it.
- `iter_NNN/`: one directory per iteration, always on the **dev** split.
  - `plan.json`: the hypothesis, method, parameters and target.
  - `literature.md`: notes from the literature search, with sources (iteration 1 only with `steps.literature: first_only`).
  - `execute.json`: the evaluator's metrics, per-image errors, errors per corruption level, or the error the method raised.
  - `outputs/predictions.csv`: every grain the method found (pixels), one row per grain.
  - `outputs/overlays/*.jpg`: red grain contours on three dev images (low, middle, high corruption); the reviewer sees them.
  - `outputs/labels/`: label images, not committed (regenerate them by rerunning the method with the same params).
  - `verify.json`: the automatic checks and the reviewer's verdict.
  - `summary.json`: one line of the history, as the planner sees it.
  - `usage.json`: tokens used by each Claude call.
  - `run.log`: the log of the iteration.
- `baseline/<dataset>/`: the watershed method with default params on dev, run without the API
  (`uv run python -m src.execute --dataset <dataset> --out results/baseline/<dataset>`).
- `final.json`, `final_<dataset>/`: the one-time holdout exam, `run.py --final`, per dataset.
- `_dry_run/`: output of `run.py --dry-run`, not committed.
