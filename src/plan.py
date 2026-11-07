"""Step 1, plan: Claude picks the next experiment from the methods that exist."""

import json
import logging
from pathlib import Path

from src import evaluate, methods
from src.llm import Claude
from src.state import State, write_json

log = logging.getLogger(__name__)

DRY_RUN = {
    "hypothesis": "Dry run: the default watershed parameters reach max_rel_error <= 0.10 on dev.",
    "rationale": "No API call in dry-run mode; runs the method with its defaults.",
    "method": "watershed",
    "params_json": "{}",
    "metric": "max_rel_error",
    "threshold": 0.10,
    "direction": "<=",
}


def schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "hypothesis": {"type": "string"},
            "rationale": {"type": "string"},
            "method": {"type": "string", "enum": sorted(methods.METHODS)},
            "params_json": {"type": "string"},
            "metric": {"type": "string"},
            "threshold": {"type": "number"},
            "direction": {"type": "string", "enum": [">=", "<="]},
        },
        "required": ["hypothesis", "rationale", "method", "params_json", "metric", "threshold", "direction"],
        "additionalProperties": False,
    }


def run(cfg: dict, claude: Claude, state: State, it_dir: Path) -> dict:
    history = state.history[-cfg["limits"]["history_in_prompt"] :]
    prompt = f"""Past iterations, oldest first:
{json.dumps(history, indent=2, ensure_ascii=False) if history else "none yet"}

Methods you can run:
{methods.describe()}

Data: every experiment runs on the dev split of the "{cfg['eval']['dataset']}" dataset; the holdout split is never shown to you.
The method only segments and measures; a separate evaluator compares its grains with the ground truth.
{evaluate.METRICS_DOC}

Propose the single next experiment that most reduces uncertainty about the research question.
- hypothesis: one falsifiable sentence.
- rationale: why this experiment now, given the past iterations.
- method and params_json: one of the methods above, and its parameters as a JSON object string.
- metric, threshold, direction: the metric the method reports that decides the outcome,
  and the value that counts as success (metric >= threshold or metric <= threshold).
If none of the methods can test what is needed next, choose the closest one,
and say in the rationale which new method should be written."""

    plan = claude.ask_json("planner", prompt, schema(), dry_run_response=DRY_RUN)
    try:
        plan["params"] = json.loads(plan["params_json"] or "{}")
    except json.JSONDecodeError:
        log.warning("plan: params_json is not valid JSON, running with no params: %r", plan["params_json"])
        plan["params"] = {}
    write_json(it_dir / "plan.json", plan)
    log.info("plan: %s -> %s(%s)", plan["hypothesis"], plan["method"], plan["params"])
    return plan
