"""Step 4, verify: automatic checks against the plan's target, then an optional review by Claude."""

import json
import logging
from pathlib import Path

from src.llm import Claude
from src.state import write_json

log = logging.getLogger(__name__)

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["accept", "reject", "inconclusive"]},
        "reason": {"type": "string"},
        "next_step": {"type": "string"},
    },
    "required": ["verdict", "reason", "next_step"],
    "additionalProperties": False,
}

DRY_RUN_REVIEW = {"verdict": "inconclusive", "reason": "Dry run: no review.", "next_step": "Run without --dry-run."}


def run(cfg: dict, claude: Claude, plan: dict, literature: dict, execution: dict, it_dir: Path) -> dict:
    value = execution["metrics"].get(plan["metric"])
    checks = {
        "executed": execution["ok"],
        "metric_reported": isinstance(value, (int, float)) and not isinstance(value, bool),
        **{f"method:{name}": bool(ok) for name, ok in execution["checks"].items()},
    }
    target_met = checks["metric_reported"] and (
        value >= plan["threshold"] if plan["direction"] == ">=" else value <= plan["threshold"]
    )
    verdict = {
        "metric": plan["metric"],
        "value": value,
        "target": f"{plan['direction']} {plan['threshold']}",
        "target_met": target_met,
        "checks": checks,
        "passed": all(checks.values()) and target_met,
    }

    if cfg["steps"]["llm_review"]:
        overlays = [it_dir / o for o in execution.get("overlays", []) if (it_dir / o).exists()]
        prompt = f"""Review one iteration of the research loop.

Plan:
{json.dumps(plan, indent=2, ensure_ascii=False)}

Literature notes:
{literature.get("notes") or "none"}

Execution result:
{json.dumps(execution, indent=2, ensure_ascii=False, default=str)}

Automatic checks:
{json.dumps(verdict, indent=2, ensure_ascii=False, default=str)}

The attached images ({len(overlays)}) show the segmentation as red grain contours
on dev images at low, middle and high corruption: {", ".join(Path(o).stem for o in overlays) or "none"}.

Does the result support the hypothesis?
Look for what would make it wrong: leakage between inputs and ground truth,
a metric that does not measure what the hypothesis claims, too few samples,
values outside the range the literature reports.
Say where the segmentation fails in the images: grains merged under one contour,
grains over-split into pieces, scratches, pores or artifacts taken as boundaries, boundaries missed.
In next_step, propose concrete parameter changes (param: current value -> new value, and why),
or say plainly that no parameter of the existing methods can fix the failure and which method is needed.
Answer accept only if the evidence holds up."""
        verdict["review"] = claude.ask_json(
            "reviewer", prompt, REVIEW_SCHEMA, images=overlays, dry_run_response=DRY_RUN_REVIEW
        )

    write_json(it_dir / "verify.json", verdict)
    log.info("verify: %s = %s (target %s), passed=%s", plan["metric"], value, verdict["target"], verdict["passed"])
    return verdict
