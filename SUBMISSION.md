# Submission

Text for the lab's [project submission issue](https://github.com/xemantic/claude-impact-lab-2026/blob/main/.github/ISSUE_TEMPLATE/project-submission.yml), one section per field.
Before filing, check the repository URL and fill in the GitHub handles.

**Title:** [Submission] micrograph-impact-lab: an agent loop that tunes classical grain segmentation on optical micrographs of metals

## Team name

micrograph-impact-lab

## Team members

```
Ivan Logutov (@VanishJr), engineer
Cesare Garberino (@<handle>), scientist, problem owner
```

## Field

Chemistry / materials

## Repository

https://github.com/VanishJr/micrograph-impact-lab

## License

Apache 2.0 for code, CC BY 4.0 for text

## Open problem

Grain size strongly affects the strength of metals.
The smaller the grains, the higher the yield strength (the Hall–Petch relation),
and it is still often measured by hand on optical micrographs.
Classical segmentation (threshold + watershed) can do it, but needs hand-tuned parameters for each material and image quality.
That tuning is manual and rarely reported with errors against ground truth.

We ask:

> Can an agent loop tune a classical grain segmentation pipeline so that grain count and mean grain size match ground truth within 10%,
> how does accuracy degrade with image noise,
> and can scratches and pores be detected and kept from corrupting the grain measurements?

It is checked by computation.
An evaluator compares the pipeline's grains with expert grain-boundary masks of real 316L stainless steel (Warren et al. 2024, CC BY 4.0),
and with exact labels and defect masks of a synthetic testbed.
The loop tunes on a dev split; a holdout split is used once at the end.

## The research loop

**Code measures, Claude tunes:** a scikit-image pipeline segments and measures; Claude never estimates sizes from pixels.

- **Inner loop** ([run.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/run.py)), one iteration:
  1. **plan** ([src/plan.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/plan.py)):
     Claude proposes a falsifiable hypothesis and a method plus parameters, chosen from the methods that exist.
     The pass threshold is fixed by the project, not by the planner.
  2. **literature** ([src/literature.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/literature.py)):
     Claude with web search, once per dataset; notes and retrieved URLs go to `literature.md`.
  3. **execute** ([src/execute.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/execute.py)):
     runs the method on the dev images.
     [src/evaluate.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/evaluate.py), the only code that reads ground truth, then scores grain count and size (per image, per morphology, per noise level) and defects.
  4. **verify** ([src/verify.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/verify.py)):
     automatic checks against the target, then a Claude reviewer with contour drawings of three dev images.
     It names failure modes and proposes concrete parameter changes.
  5. **record** ([src/record.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/src/record.py)):
     state in `results/state.json`, one directory per iteration, an entry in `JOURNAL.md`.
- **Outer loop:** a Claude Code session following [PROMPT.md](https://github.com/VanishJr/micrograph-impact-lab/blob/main/PROMPT.md).
  It reads the reviews, writes missing methods test-first, and reruns the inner loop.
  Example: the reviewer saw elongated grains cut into "ladders", and the session added h-maxima markers with a test.
- **Guards:**
  - a test that fails if a method touches ground truth or the split ([tests/test_leakage.py](https://github.com/VanishJr/micrograph-impact-lab/blob/main/tests/test_leakage.py));
  - a fixed split ([data/splits.json](https://github.com/VanishJr/micrograph-impact-lab/blob/main/data/splits.json));
  - a one-time holdout exam (`run.py --final`);
  - 42 tests on a Voronoi micrograph with known answers.

## What the loop found

Error = the larger of the median count error and the median size error.
Numbers from `results/*/execute.json` and [results/final.json](https://github.com/VanishJr/micrograph-impact-lab/blob/main/results/final.json).

**Real 316L stainless steel**:

| Run | Error |
|---|---|
| Untuned baseline (dev) | 1290 % |
| Scaled to the real grain size (iteration 7, dev) | 23.5 % |
| `fill_boundaries=false` (iteration 11, dev) | **12.6 %** |
| Holdout, 165 unseen images | **17.4 %** |

- The 10 % target is **not met**.
- Iteration 11, the final config, was set by the outer loop on the reviewer's suggestion, not chosen by the planner.
- The 4.8-point dev–holdout gap suggests part of the gain is fit to the 40 dev images.

**Synthetic testbed** (AI-generated, not evidence about real metals):
- Pooled error: 33.3 % → 6.1 % on dev, 4.6 % on holdout.
- Two of six grain morphologies stay above 10 % (worst: 15.0 % dev, 12.8 % holdout).
- Scratches and pores were found in part: at best 47 % of scratches (precision 39 %) and 64 % of pores (precision 17 %).

**Noise:** no controlled sweep was done.
The within-morphology pattern is an observation on one image per cell, not a measurement.

**Verification:**
- Every number is read from the iteration's JSON.
- Each iteration has a Claude review in `verify.json`.
- The holdout was touched once.

**Confidence:**
- High that the 316L result misses 10 %.
- Moderate in the exact holdout value: 165 images, with the median as the metric.

See [README.md](https://github.com/VanishJr/micrograph-impact-lab/blob/main/README.md#results) and the figure [docs/before_after_316L.png](https://github.com/VanishJr/micrograph-impact-lab/blob/main/docs/before_after_316L.png).

## Where it got stuck

- **316L:**
  - One global scale cannot fit both fine-grained and coarse-grained images; predicted sizes sit in a narrow band.
  - The scratch detector does not transfer to real images: on 316L it marked 1,233 false "scratches" in the wide boundary bands, and the error rose to 16.7 %.
- **Synthetic:**
  - Equiaxed and elongated grains over-count by 13–15 %.
  - The scratch detector either takes straight columnar boundaries for scratches or finds few.
  - Pore detection mistakes triple junctions for pores.
- **Bugs the loop and the reviews exposed,** each recorded next to its result in JOURNAL.md:
  - a NaN in a size median;
  - an iteration lost to a parameter the planner copied from a docstring;
  - a planner that set its own looser pass threshold;
  - literature URLs that were not captured.
- **The tuned parameters are tied to grain scale.** On a new SEM image (not in the repository), the 316L config merged neighbouring grains.

## What it would need next

- **Labelled images per new image type** (SEM, other alloys), so the loop can tune for them.
- **Size-adaptive methods:**
  - per-image scale estimation;
  - learned segmentation as a comparison.
- **New defect methods,** test first: a thin-ridge (Hessian) scratch detector and a stricter pore test.
- **Defect ground truth on real images.**
- **A controlled noise sweep** (the same images at increasing noise) to answer the second part of the question.
- **More dev images,** to narrow the dev–holdout gap.

## How to run it

```shell
git clone https://github.com/VanishJr/micrograph-impact-lab && cd micrograph-impact-lab
uv sync
uv run pytest                                   # 42 tests, no API key, no dataset
export MICROGRAPHS_DIR=/path/to/data            # 316L: download from Zenodo 10.5281/zenodo.22039777 (layout in README)
uv run python run.py --dry-run                  # one iteration without API calls
export ANTHROPIC_API_KEY=...                    # live runs are billed, about $0.25 per iteration
uv run python run.py -n 3 --dataset 316L
uv run python run.py --final --dataset 316L     # once, at the end
```

## Data and sources

- **316L stainless steel** optical micrographs with expert grain masks: Warren et al. 2024, [Zenodo 10.5281/zenodo.22039777](https://doi.org/10.5281/zenodo.22039777), CC BY 4.0, public.
  Two images are in `data/sample/`.
- **Synthetic micrographs:** generated by the scientist with AI prompts and edited by hand.
  No generator code exists and the licence is unknown, so they are not redistributed. They serve as a tuning testbed only.
- **Literature:** the URLs the librarian retrieved are listed in each `literature.md`.

No private or personal data.

## How Claude was used

- **Inner loop: Claude Opus 5.5 (`claude-opus-5-5`)** through the Anthropic API, in three roles:
  - planner (structured output);
  - librarian (web search);
  - reviewer (structured output, with contour drawings as images).
- **Outer loop: Claude Code**, following PROMPT.md and working with the developer. It wrote and tested:
  - the evaluator, the methods and the defect detectors;
  - the fixes;
  - the journal and this text.
- **Cost:** API spend for iterations 1–12 was about $3.10.

## Demo materials

[docs/before_after_316L.png](https://github.com/VanishJr/micrograph-impact-lab/blob/main/docs/before_after_316L.png)
