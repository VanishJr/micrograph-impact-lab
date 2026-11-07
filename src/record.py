"""Step 5, record: summarise the iteration, save the loop state and append to the journal."""

import logging
import os
from datetime import datetime
from pathlib import Path

from src.state import State, write_json

log = logging.getLogger(__name__)


def run(cfg, state: State, it_dir: Path, plan, literature, execution, verdict, usage: list[dict]) -> dict:
    review = verdict.get("review", {})
    summary = {
        "iteration": state.iteration,
        "time": datetime.now().isoformat(timespec="seconds"),
        "hypothesis": plan["hypothesis"],
        "dataset": execution.get("dataset"),
        "method": plan["method"],
        "params": plan["params"],
        "metric": plan["metric"],
        "value": verdict["value"],
        "target": verdict["target"],
        "passed": verdict["passed"],
        "error": execution.get("error"),
        "review": review.get("verdict"),
        "review_reason": review.get("reason"),
        "next_step": review.get("next_step"),
        "rationale": plan["rationale"],
        "sources": len(literature["sources"]),
        "tokens": {
            "input": sum(u["input_tokens"] for u in usage),
            "output": sum(u["output_tokens"] for u in usage),
        },
    }
    write_json(it_dir / "summary.json", summary)
    write_json(it_dir / "usage.json", usage)

    state.history.append(summary)
    state.save()
    _append_journal(cfg["paths"]["journal"], it_dir, summary)
    log.info("record: iteration %d saved", state.iteration)
    return summary


def _append_journal(journal: Path, it_dir: Path, s: dict) -> None:
    link = os.path.relpath(it_dir, journal.parent)
    outcome = "**pass**" if s["passed"] else "**fail**"
    lines = [
        f"\n## {s['time'][:16].replace('T', ' ')} · iteration {s['iteration']} (run.py)\n",
        f"- Hypothesis: {s['hypothesis']}",
        f"- Method: `{s['method']}` with {s['params']}",
        f"- Result: {s['metric']} = {s['value']}, target {s['target']}: {outcome}"
        + (f" ({s['error']})" if s["error"] else ""),
    ]
    if s["review"]:
        lines.append(f"- Review: {s['review']}. {s['review_reason']}")
        lines.append(f"- Next: {s['next_step']}")
    lines.append(f"- Outputs: [{link}/]({link}/)\n")
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a") as f:
        f.write("\n".join(lines))
