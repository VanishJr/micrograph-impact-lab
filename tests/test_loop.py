"""The loop runs end to end without the API (dry run), and keeps its state in files."""

import json
from pathlib import Path

import pytest

import run
from src import literature, plan, verify
from src.config import load_config
from src.llm import Claude
from src.methods import METHODS
from src.state import State
from tests.voronoi import write_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def cfg(tmp_path):
    """The real config, pointed at a tiny Voronoi dataset with one dev and one holdout image."""
    cfg = load_config(ROOT / "config.yaml")
    cfg["paths"]["results"] = tmp_path / "results"
    cfg["paths"]["journal"] = tmp_path / "JOURNAL.md"
    cfg["paths"]["dataset"] = write_synthetic_dataset(tmp_path / "dataset", [("voronoi_00", 0.15, 0), ("voronoi_01", 0.55, 1)])
    cfg["paths"]["splits"] = tmp_path / "splits.json"
    cfg["paths"]["splits"].write_text(json.dumps({"synthetic": {"dev": ["voronoi_00"], "holdout": ["voronoi_01"]}}))
    cfg["eval"]["dataset"] = "synthetic"
    return cfg


def iterate_once(cfg):
    state = State.load(cfg["paths"]["results"])
    return run.iterate(cfg, Claude(cfg, dry_run=True), state)


def test_one_iteration_writes_every_step(cfg):
    summary = iterate_once(cfg)

    it_dir = cfg["paths"]["results"] / "iter_001"
    for name in ["plan.json", "literature.md", "execute.json", "verify.json", "summary.json", "run.log"]:
        assert (it_dir / name).exists(), name
    assert summary["iteration"] == 1
    assert summary["metric"] == "max_rel_error" and 0 <= summary["value"] < 1
    assert (it_dir / "outputs" / "predictions.csv").exists()
    assert "iteration 1" in cfg["paths"]["journal"].read_text()


def test_state_survives_a_restart(cfg):
    iterate_once(cfg)
    iterate_once(cfg)  # a fresh State.load, as after a new session

    state = State.load(cfg["paths"]["results"])
    assert state.iteration == 2
    assert [h["iteration"] for h in state.history] == [1, 2]
    assert (cfg["paths"]["results"] / "iter_002").is_dir()


def test_a_failing_method_is_recorded_not_raised(cfg, monkeypatch):
    def broken(images, params, out_dir, overlay=()):
        raise ValueError("bad input")

    monkeypatch.setitem(METHODS, "watershed", broken)
    summary = iterate_once(cfg)

    execution = json.loads((cfg["paths"]["results"] / "iter_001" / "execute.json").read_text())
    assert execution["ok"] is False
    assert "bad input" in execution["error"]
    assert summary["passed"] is False


@pytest.mark.parametrize(
    ("direction", "value", "passed"),
    [("<=", 0.05, True), ("<=", 0.2, False), (">=", 0.2, True), (">=", 0.05, False)],
)
def test_verify_checks_the_target(cfg, tmp_path, direction, value, passed):
    cfg["steps"]["llm_review"] = False
    plan = {"metric": "error", "threshold": 0.1, "direction": direction}
    execution = {"ok": True, "metrics": {"error": value}, "checks": {}}

    verdict = verify.run(cfg, Claude(cfg, dry_run=True), plan, {}, execution, tmp_path)

    assert verdict["passed"] is passed


def test_verify_fails_when_the_metric_is_missing(cfg, tmp_path):
    cfg["steps"]["llm_review"] = False
    plan = {"metric": "error", "threshold": 0.1, "direction": "<="}
    execution = {"ok": True, "metrics": {}, "checks": {}}

    verdict = verify.run(cfg, Claude(cfg, dry_run=True), plan, {}, execution, tmp_path)

    assert verdict["checks"]["metric_reported"] is False
    assert verdict["passed"] is False


def test_the_loop_stops_at_max_iterations(cfg):
    cfg["limits"]["max_iterations"] = 1

    run.run_loop(cfg, n=3, dry_run=True)

    assert State.load(cfg["paths"]["results"]).iteration == 1


def test_literature_runs_only_on_the_first_iteration(cfg):
    iterate_once(cfg)
    iterate_once(cfg)

    assert "Skipped" in (cfg["paths"]["results"] / "iter_002" / "literature.md").read_text()


def test_literature_runs_again_for_a_new_dataset(cfg, tmp_path):
    claude = Claude(cfg, dry_run=True)
    history = [{"iteration": 1, "dataset": "synthetic"}]

    cfg["eval"]["dataset"] = "316L"
    literature.run(cfg, claude, {"hypothesis": "h", "method": "m", "params": {}, "metric": "x",
                                 "direction": "<=", "threshold": 0.1}, tmp_path, history)

    assert "Skipped" not in (tmp_path / "literature.md").read_text()


def test_the_reviewer_sees_the_overlays(cfg, monkeypatch):
    seen = {}

    def ask_json(self, role, prompt, schema, *, images=(), dry_run_response):
        if role == "reviewer":
            seen["images"] = list(images)
        return dry_run_response

    monkeypatch.setattr(Claude, "ask_json", ask_json)
    iterate_once(cfg)

    assert [p.name for p in seen["images"]] == ["voronoi_00.jpg"]
    assert all(p.exists() for p in seen["images"])


def test_final_runs_the_best_dev_iteration_once_on_holdout(cfg):
    iterate_once(cfg)

    out = run.final(cfg)

    assert out["best_iteration"] == 1
    assert set(out) >= {"dev", "holdout", "gap"}
    holdout_run = json.loads((cfg["paths"]["results"] / "final_synthetic" / "execute.json").read_text())
    assert holdout_run["split"] == "holdout"
    with pytest.raises(SystemExit, match="used once"):
        run.final(cfg)


def test_the_planner_is_held_to_the_project_target(cfg):
    iterate_once(cfg)

    plan_json = json.loads((cfg["paths"]["results"] / "iter_001" / "plan.json").read_text())
    assert (plan_json["metric"], plan_json["direction"], plan_json["threshold"]) == ("max_rel_error", "<=", 0.10)
    assert "threshold" not in plan.schema()["properties"]


def test_best_dev_iteration_reads_max_rel_error_from_execute_json(tmp_path):
    for i, value in [(1, 0.30), (2, 0.07)]:
        (tmp_path / f"iter_{i:03d}").mkdir()
        (tmp_path / f"iter_{i:03d}" / "execute.json").write_text(json.dumps({"metrics": {"max_rel_error": value}}))
    history = [
        {"iteration": 1, "dataset": "synthetic", "metric": "max_rel_error", "value": 0.30},
        {"iteration": 2, "dataset": "synthetic", "metric": "worst_family_rel_error", "value": 0.18},
    ]
    assert run.best_dev_iteration(tmp_path, history, "synthetic")["iteration"] == 2


def test_the_outer_loop_can_fix_the_params_of_one_iteration(cfg):
    state = State.load(cfg["paths"]["results"])
    fixed = {"method": "watershed", "params": {"fill_boundaries": False}, "hypothesis": "h"}
    summary = run.iterate(cfg, Claude(cfg, dry_run=True), state, fixed)

    plan_json = json.loads((cfg["paths"]["results"] / "iter_001" / "plan.json").read_text())
    assert plan_json["params"] == {"fill_boundaries": False} and plan_json["fixed_by_outer_loop"] is True
    assert summary["metric"] == "max_rel_error" and summary["params"] == {"fill_boundaries": False}
