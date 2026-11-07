"""Step 2, literature: Claude searches the web for prior work on the planned hypothesis."""

import logging
from pathlib import Path

from src.llm import Claude

log = logging.getLogger(__name__)

DRY_RUN = ("Dry run: no literature search.", [], [])


def run(cfg: dict, claude: Claude, plan: dict, it_dir: Path, history: list[dict] = ()) -> dict:
    """With steps.literature == first_only, search once per dataset (a new dataset has its own prior work)."""
    mode = cfg["steps"]["literature"]
    if not mode:
        (it_dir / "literature.md").write_text("Literature step disabled in config.yaml.\n")
        return {"notes": "", "sources": []}
    dataset = cfg["eval"]["dataset"]
    earlier = [h["iteration"] for h in history if h.get("dataset") == dataset]
    if mode == "first_only" and earlier:
        first = f"iter_{min(earlier):03d}"
        path = Path(cfg["paths"]["results"]) / first / "literature.md"
        notes = path.read_text() if path.exists() else ""
        (it_dir / "literature.md").write_text(
            f"Skipped: steps.literature is first_only and {dataset} was searched in {first}. "
            f"The reviewer gets those notes (../{first}/literature.md).\n"
        )
        log.info("literature: skipped (first_only), reusing %s notes for %s", first, dataset)
        return {"notes": notes, "sources": [], "reused_from": min(earlier)}

    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": cfg["limits"]["max_searches"]}]
    prompt = f"""Hypothesis of the next experiment:
{plan['hypothesis']}

Planned method: {plan['method']} with params {plan['params']}, judged by {plan['metric']} {plan['direction']} {plan['threshold']}.
Dataset: {dataset}.

Search the literature for prior work on this hypothesis.
Write short notes: what is already known, which values a result should be compared against,
which methods are standard, and any reason to doubt the planned test.
Cite every claim. Prefer peer-reviewed papers and dataset descriptions."""

    notes, cited, searched = claude.ask_text("librarian", prompt, tools=tools, dry_run_response=DRY_RUN)
    cited_md = "\n".join(f"- {url}" for url in cited) or "- none"
    searched_md = "\n".join(f"- {url}" for url in searched) or "- none"
    (it_dir / "literature.md").write_text(
        f"# Literature\n\n{notes}\n\n## Sources cited in the notes\n\n{cited_md}\n\n"
        f"## Other search results (retrieved, not cited)\n\n{searched_md}\n"
    )
    log.info("literature: %d cited, %d other search results", len(cited), len(searched))
    return {"notes": notes, "sources": cited + searched, "cited": cited}
