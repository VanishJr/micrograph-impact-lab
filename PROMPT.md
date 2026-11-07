# PROMPT

The standing instruction for every pass of the outer research loop.
Any new Claude Code session can continue the work from this file alone.
Start or resume with:

```
/goal <the goal, stated so it can be checked, e.g. "TASKS.md has no open T-* task and README.md reports the results">
/loop 20m read @PROMPT.md and follow the instructions in it
```

## What this project is

A research loop on optical micrographs, built at the Claude Impact Lab Berlin 2026.
The question is in [README.md](README.md) and in `question` of [config.yaml](config.yaml).
How it is judged, and the rules of this repository, are in [CLAUDE.md](CLAUDE.md).

## One pass

1. **Read** [TASKS.md](TASKS.md), the last entries of [JOURNAL.md](JOURNAL.md) and `results/state.json`.
   Take the highest-priority task that is not blocked.
   Process blockers outrank science tasks, and cheap checks outrank expensive runs.
2. **Formulate.** Write in the task row what would count as done: a metric, a threshold, the data it is measured on.
3. **Build.** If the task needs a new method:
   write a failing test in `tests/` against a known answer first,
   then the method in `src/methods/`, registered with `@register`,
   then make the test pass with `uv run pytest`.
4. **Run** the inner loop: `uv run python run.py -n <k>`.
   Every iteration lands in `results/iter_NNN/`.
5. **Verify.** Open `verify.json` and `summary.json` of the new iterations.
   Does the reviewer accept? Does the result agree with the literature notes in `literature.md`?
   A number that is not in a JSON file is not a result.
6. **Journal.** Append to [JOURNAL.md](JOURNAL.md): what was done, what was found with links to `results/iter_NNN/`,
   what was decided and why, and every exchange with the scientist (question, answer, what changed).
7. **Queue.** Update [TASKS.md](TASKS.md): close what is done, add what the pass revealed, re-prioritise.
   A branch that turned out to be a dead end becomes `KILLED`, with the reason.
8. **Hand over.** If anything in this file has become wrong or incomplete, fix it now.

Run each atomic step (a method, a run, a literature check) in its own subagent,
and keep the main session for planning and review.

## Stop and ask the scientist

- when the question or the success criterion is unclear;
- when a result contradicts the literature or an earlier iteration and the reason is not obvious;
- when the data needed is not in the repository or in the dataset folder;
- when a run would cost far more than the previous ones.
