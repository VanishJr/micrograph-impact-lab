# CLAUDE.md

Context for Claude Code sessions in this repository.
It holds what cannot be read from the code; [PROMPT.md](PROMPT.md) holds the loop itself.

## The task

This is a team entry for the [Claude Impact Lab Berlin 2026](https://github.com/xemantic/claude-impact-lab-2026)
(Claude Community × Foresight Institute, CIC Berlin, 7 November 2026).
A scientist brings an open problem from their own research,
and the team builds a research loop on it:
an agent that reads the literature, writes and runs code, and checks its own results.
The loop stays on GitHub as open source that anyone can keep using.

Submission is one GitHub issue per team in the lab repository, **by 17:00 on 7 November 2026**,
using its [submission template](https://github.com/xemantic/claude-impact-lab-2026/blob/main/.github/ISSUE_TEMPLATE/project-submission.yml).
Claude scores every repository from 1 to 5, and the jury decides with those reviews in hand:

- **Problem**: open, significant, and checkable by computation.
- **Loop**: reads literature, writes and runs code, checks its own results, keeps its state in files.
- **Evidence**: the findings are backed by artifacts in this repository.
- **Honesty**: failures, limits and confidence are stated.
- **Reproducibility**: someone else could run it from the README.

Length and polish are not rewarded.
An honest, well-verified negative result beats an impressive claim the repository does not support.

Team: Ivan Logutov (engineer) and Cesare Garberino (scientist), who brought the problem:
measuring grains in optical micrographs of metals. **Submission deadline: 17:00 on 7 November 2026.**

The research question (also `question` in [config.yaml](config.yaml) and the Question section of [README.md](README.md)):

> Can an agent loop tune a classical grain segmentation pipeline so that grain count and mean grain size on optical micrographs match ground truth within 10%,
> and how does accuracy degrade with image noise,
> and can scratches and pores be detected and kept from corrupting the grain measurements?

Code measures, Claude tunes: a scikit-image pipeline segments and measures,
the planner chooses parameters, the reviewer reads metrics and contour overlays.
Claude never estimates sizes from pixels.

Data, outside the repository (`paths.dataset`, or `MICROGRAPHS_DIR`):
real 316L stainless steel with expert masks (CC BY 4.0), where the main claim is measured;
and a synthetic set with exact labels, which is a **tuning testbed, not evidence**
(AI-generated, no generator code, licence unknown: never copy its files into the repository).

## Two loops

- The **inner loop** is `run.py`: plan → literature → execute → verify → record, through the Claude API.
  The planner can only choose methods that exist in `src.methods.METHODS` (they are the enum of its output schema).
  When it needs a method that does not exist, it says so in `rationale`.
- The **outer loop** is a Claude Code session following [PROMPT.md](PROMPT.md).
  It reads those rationales and the reviews, writes the missing methods with their tests, and runs the inner loop again.

## Rules

- The state lives in files: `results/`, [TASKS.md](TASKS.md), [JOURNAL.md](JOURNAL.md), [PROMPT.md](PROMPT.md). Nothing important lives only in a chat.
- Quote a number only after opening the `results/iter_*/*.json` file that holds it. A subagent's report is a summary, not evidence.
- Test first: a new method gets a failing test against a known answer (synthetic ground truth, a published value, an analytic case) before its code.
- A result that contradicts an earlier one is recorded next to it in JOURNAL.md, with the reason. It does not silently replace it.
- When the available methods cannot answer a question, say so plainly instead of answering anyway.
- **No leakage.** Only `src/evaluate.py` reads ground truth (CSV files, `labels_*`, masks).
  Files in `src/methods/` get image paths only: they never mention ground truth, the split or the holdout, and never import `src.evaluate`.
  `tests/test_leakage.py` enforces it.
- The inner loop evaluates on the dev split only. The holdout is used once per dataset, by `run.py --final`, after tuning.
  Do not look at holdout numbers before that, not even with `--dry-run --final`.
- Live runs (without `--dry-run`) bill the Anthropic API. Tests and development use `--dry-run`.
- The dataset stays outside the repository. Only a small sample goes to `data/sample/`, with the source and licence of every file.
- Commit only when the developer asks. In auto mode, leave changes in the working tree for review.
- Markdown uses [semantic line breaks](https://sembr.org/): a line break after each sentence, never hard-wrapped to a width.
- Licences: Apache 2.0 for code ([LICENSE](LICENSE)), CC BY 4.0 for text ([LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0)).

## Lessons

Add an entry when something surprises you: a quirk, a non-obvious constraint, an anti-pattern a developer flagged.
One line per lesson, with its non-obvious *why*.

- The Python environment is managed by `uv`; run everything through `uv run` so the locked dependencies are used.
- In the synthetic CSV, `n_grains` counts all grains but `mean_eq_diameter_um` averages interior grains only: compare count and size each like with like, or the size error is biased.
- `.gitignore` has `data/*`, so `data/splits.json` needs its own `!data/splits.json` line, or the split is silently not committed.
- `execute.json` is pasted verbatim into the reviewer prompt: keep per-grain data in `outputs/predictions.csv`, not in it.
- The 316L images are a mix of `.png` and `.jpg` (the masks are all `.png`), so the split stores file names with extensions.
- The leakage test matches substrings: words like "over-splits" trip it; reword rather than weaken the test.
- With `web_search_20260209` the librarian's text may carry no citations; URLs are in `web_search_tool_result` blocks, so read both or literature.md shows "0 sources".
- The planner treats every name in a method docstring as a param: mentioning the `overlay` argument there put `overlay` into params and failed iteration 3.
- The planner sets its own threshold per hypothesis, so "pass" in a summary is relative to that threshold, not to the project's 10 %; read `by_family` too.
