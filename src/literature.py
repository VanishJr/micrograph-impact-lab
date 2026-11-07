"""Step 2, literature: Claude searches the web for prior work on the planned hypothesis."""

import logging
from pathlib import Path

from src.llm import Claude

log = logging.getLogger(__name__)

DRY_RUN = ("Dry run: no literature search.", [])


def run(cfg: dict, claude: Claude, plan: dict, it_dir: Path, iteration: int = 1) -> dict:
    mode = cfg["steps"]["literature"]
    if not mode:
        (it_dir / "literature.md").write_text("Literature step disabled in config.yaml.\n")
        return {"notes": "", "sources": []}
    if mode == "first_only" and iteration > 1:
        first = Path(cfg["paths"]["results"]) / "iter_001" / "literature.md"
        notes = first.read_text() if first.exists() else ""
        (it_dir / "literature.md").write_text(
            "Skipped: steps.literature is first_only. The reviewer gets the notes of iteration 1 (../iter_001/literature.md).\n"
        )
        log.info("literature: skipped (first_only), reusing iteration 1 notes")
        return {"notes": notes, "sources": [], "reused_from": 1}

    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": cfg["limits"]["max_searches"]}]
    prompt = f"""Hypothesis of the next experiment:
{plan['hypothesis']}

Planned method: {plan['method']} with params {plan['params']}, judged by {plan['metric']} {plan['direction']} {plan['threshold']}.

Search the literature for prior work on this hypothesis.
Write short notes: what is already known, which values a result should be compared against,
which methods are standard, and any reason to doubt the planned test.
Cite every claim. Prefer peer-reviewed papers and dataset descriptions."""

    notes, sources = claude.ask_text("librarian", prompt, tools=tools, dry_run_response=DRY_RUN)
    sources_md = "\n".join(f"- {url}" for url in sources) or "- none"
    (it_dir / "literature.md").write_text(f"# Literature\n\n{notes}\n\n## Sources\n\n{sources_md}\n")
    log.info("literature: %d sources", len(sources))
    return {"notes": notes, "sources": sources}
