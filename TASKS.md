# TASKS

The live queue of the outer loop.
Priority rule: process blockers (`P-*`) outrank science tasks (`T-*`), and cheap checks outrank expensive runs.

Status vocabulary: `TODO` · `IN PROGRESS` · `BLOCKED` · `DONE` · `KILLED` (abandoned, with the reason).

| ID | Task | Done when | Status |
|---|---|---|---|
| P-1 | Fix the research question with the scientist | `question` in config.yaml and the Question section of README.md say what is asked, why it is open, and how a result is checked by computation | DONE |
| P-2 | Connect the dataset | `paths.dataset` / `MICROGRAPHS_DIR` points at the dataset outside the repository; `data/splits.json` fixes dev/holdout; licence-checked samples in `data/sample/` | IN PROGRESS: connected and split; the synthetic set's licence is open (Q-1) |
| T-1 | First baseline method | `watershed` in `src/methods/` with tests against known ground truth (Voronoi fixture), run by the inner loop | DONE: iteration 1, `max_rel_error` 0.333, reviewer reject |
| P-3 | First live run | `uv run python run.py -n 1` finishes; the cost of one iteration (`usage.json`) is noted in JOURNAL.md | DONE: about $0.80, 80 % literature |
| T-4 | Tune watershed on synthetic dev | iterations follow the reviewer's grid; if columnar/elongated median count error stays > 0.50, add `markers: hmaxima` (test first) and run 2 more | DONE: best iteration 5, `max_rel_error` 0.066, `worst_family_rel_error` 0.183 (equiaxed); h-maxima fixed columnar |
| T-5 | Scratch and pore detection (scientist: a main goal) | detectors with tests, scored against `artifact_mask` (60, 120); 2 live iterations | DONE: iterations 9–10; scratches ≤ 47 % found (P 0.39) or 9 % (P 0.96); pores 64 % (P 0.17) |
| T-6 | Thin-ridge scratch detector and stricter pores (reviewer, iteration 10) | Frangi-style ridge filter + straightness check; pore darkness test; tests first | TODO, not today |
| T-2 | 316L evaluation | with `eval.dataset: 316L`, the loop tunes on the 40 dev images; README reports `max_rel_error` on dev vs the baseline in `results/baseline/316L/` | DONE for today: iterations 6–8, 11–12; best 0.126 (iteration 11) vs baseline 12.9; target 0.10 not met |
| T-3 | Final holdout run | after tuning, `uv run python run.py --final` once per dataset; `results/final.json` holds dev vs holdout and the gap, reported in README | IN PROGRESS: synthetic → iteration 10, 316L → iteration 11 |
| P-4 | Publish the repository | a public GitHub repository named `micrograph-impact-lab`, with both licence files at the root; no synthetic image in it | TODO |
| P-5 | Write up and submit | README.md reports the results, failures and limits; the submission issue is filed before 17:00 | TODO; switch to 316L (T-2) by 15:30 |

## Open questions for the scientist

| ID | Question | Status |
|---|---|---|
| Q-1 | Source, generator script and licence of the synthetic set `90_SYNTHETIC_exact_ground_truth` | Asked 2026-11-07. Generated with AI prompts and edited by hand; prompts and code not available; licence unknown. Treated as a tuning testbed, not redistributed. |
