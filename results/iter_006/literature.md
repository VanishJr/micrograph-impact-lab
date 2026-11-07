# Literature

I couldn't do the literature search for this step. My first query crashed on a parsing bug in my code, and when I retried, the search tool returned "Server tool use limit exceeded". So these notes come from memory, not retrieved sources. I can't cite anything, and author names, years and figures below need checking before anyone relies on them.

## What is probably already known (unverified)

1. **Standard measurement methods.** Grain size is normally measured with the intercept and planimetric methods of ASTM E112, and the automated-image-analysis version is ASTM E1382. Repeat manual intercept measurements are commonly said to vary by about ±0.5 ASTM grain-size number between operators. One ASTM number corresponds to a factor of about 2 in grains per unit area, or about 41% in mean diameter. So a 10% match on mean size is about as tight as the gap between two human annotators. The truth signal (the expert masks) may itself be noisy at roughly that level.
2. **Twins are the known failure mode on austenitic steels.** 316L forms many annealing twins after recrystallisation. ASTM E112 says twin boundaries should be ignored when measuring grain size, and many expert masks follow that rule. Etching often makes twin boundaries look as strong as grain boundaries, so classical boundary detectors (top-hat or ridge filters followed by watershed) tend to split one grain into several. In microstructures with many twins, counts can rise by a factor of about 1.5–2. That supports the secondary prediction that count bias will be positive.
3. **Size bias versus count bias.** If grains are over-split, mean area falls roughly as 1/count. If size is reported as an equivalent diameter, it falls roughly as 1/√count, which is about half the relative error for small biases. So "size bias about −½ × count bias" only holds if the evaluator reports a diameter-like size. If it reports mean area, expect size bias ≈ −count bias. Check this in the evaluator code before testing that prediction.
4. **Transfer from synthetic to real images.** The literature (synthetic Voronoi or Potts-model micrographs, and deep-learning grain-boundary work on steels) generally finds that parameters tuned on synthetic images do not transfer cleanly. Real micrographs have uneven contrast across grain orientations, scratches, etch pits, faint or missing boundaries, and changes in illumination. Missing boundaries cause grains to be merged (under-segmentation). That pushes count bias negative and partly cancels over-splitting from twins. The sign of the net bias is genuinely uncertain.

## Values to compare against
- **Primary threshold:** max_rel_error ≤ 0.10 against the expert masks.
- **Reference points:** the inter-observer variation in item 1 (about 0.5 ASTM number); the synthetic-dev error of this same configuration, to measure how much accuracy is lost in transfer; and a trivial baseline, such as Otsu thresholding plus a plain distance-transform watershed.
- **Breakdowns:** report count bias and size bias separately for each image, not just the median, because twin density varies from image to image.

## Reasons to doubt the planned test
- **Pixel scale.** line_width_px=4, h_px=3 and min_area_px=80 are in pixels and were tuned at the synthetic resolution. If the 316L micrographs have different µm/px or grain sizes in pixels, the parameters don't mean the same thing. Rescale before concluding anything.
- **What the expert masks contain.** Check whether the masks include twin boundaries. If they do, the main mechanism behind the positive-bias prediction disappears.
- **fill_boundaries=true.** This changes grain areas. Check that it matches how the expert masks assign boundary pixels.
- **exclude_edge=false.** Including edge grains inflates count and lowers mean size unless the ground truth is computed the same way.
- **Dev split size.** With a small dev split, a single pass/fail result on max_rel_error is high-variance. Report per-image errors.

## Confidence
- **Strong prior: the configuration fails to transfer** (max_rel_error > 0.10). I'd put about 80% on this, based on general knowledge of synthetic-to-real gaps, not on retrieved evidence.
- **Positive count bias:** about 60%.
- **Size bias close to half the count bias:** this depends on the evaluator's size definition and can't be judged until that is checked.

None of the above is literature-backed in this step. A follow-up search step should verify the ASTM E112/E1382 figures and look for any published 316L grain-boundary segmentation datasets with expert labels.

## Sources cited in the notes

- none

## Other search results (retrieved, not cited)

- https://github.com/AI-HHMI/mia-agentic-search/pull/2234
- https://arxiv.org/pdf/2307.05911
- https://www.nature.com/articles/s41524-025-01801-4
- https://arxiv.org/pdf/2604.18957
- https://arxiv.org/html/2307.05911
- https://impact.ornl.gov/en/publications/grain-and-grain-boundary-segmentation-using-machine-learning-with/
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6357098/
- https://arxiv.org/pdf/2202.04930
- https://arxiv.org/html/2604.18957v1
- https://www.researchgate.net/publication/223533390_The_use_of_watershed_segmentation_and_GIS_software_for_textural_analysis_of_thin_sections
- https://link.springer.com/article/10.1007/s40192-024-00390-2
- https://www.researchgate.net/figure/Optical-micrograph-of-C22-shows-annealing-twins_fig1_275248756
- https://link.springer.com/article/10.1007/s10853-023-08901-w
- https://www.sciencedirect.com/science/article/abs/pii/S1044580325001342
- https://arxiv.org/pdf/2303.16609
- https://www.sciencedirect.com/topics/computer-science/watershed-segmentation
- https://www.sciencedirect.com/science/article/abs/pii/S0263224119302714
- https://arxiv.org/pdf/1912.07959
- https://www.sciencedirect.com/science/article/abs/pii/S0263224112002539
- https://arxiv.org/pdf/2108.08747
- https://www.researchgate.net/publication/286313056_Analysis_of_grain_size_measurement_methods_in_semiautomatic_image_analysis_setup
- https://standards.iteh.ai/catalog/standards/astm/9893e927-aa11-493d-b30c-d4b065d90f1f/astm-e1382-97-2023
- https://infinitalab.com/services/astm-e1382-grain-size-automated-image-analysis-testing/
- https://store.astm.org/e0112-13r21.html
- https://standards.iteh.ai/catalog/standards/astm/291c0f7b-e321-4999-9575-594cbbdb1d80/astm-e1382-97
- https://arxiv.org/pdf/2104.11159
- https://www.mipar.us/how-is-grain-size-measured.html
- https://www.sciencedirect.com/science/article/abs/pii/S2589152923001308
- https://www.researchgate.net/publication/388604760_Improving_microstructures_segmentation_via_pretraining_with_synthetic_data
- https://www.sciencedirect.com/science/article/pii/S0927025625007219
- https://www.researchgate.net/publication/392814963_Synthetic_training_data_for_CT_image_segmentation_of_microstructures
- https://www.nature.com/articles/s41524-020-00392-6
- https://arxiv.org/pdf/2507.00459
- https://arxiv.org/pdf/1905.04711
- https://www.biorxiv.org/content/10.1101/2021.07.21.453284.full.pdf
- https://www.sciencedirect.com/science/article/abs/pii/S0927025623007334
