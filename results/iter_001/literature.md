# Literature

I hit the search tool's usage limit after five queries, so this review is thin. I found nothing published that tests this exact pipeline (Gaussian blur, top-hat boundary filter, distance-transform watershed, area filter) against per-grain ground truth. What follows is what I could anchor in sources, plus my own reasoning, which I label as such.

## What is already known

- **Classical pipelines are standard, and their reported accuracy is mixed.** Earlier work on optical micrographs used an advanced thresholding technique to discern grains and a planimetric grain count to determine the ASTM grain size, G. Past research has also employed Canny edge detection to create closed contours and similarly determine planimetric grain size, with small improvements in accuracy. In one comparison, a learned edge detector achieves much higher accuracy than the Canny edge detection method while reducing the image processing time by one to two orders of magnitude.
- **Watershed is the usual classical method, and over-segmentation is its known weakness.** Metallographic image segmentation tasks widely employ Otsu's thresholding and watershed algorithms. In marker-based watershed, the h-maxima transform is used to suppress noise and reduce over-segmentation problems. So min_distance and footprint are the parameters most likely to decide whether the grain count is right.
- **The real 316L data has a published baseline, and it is unflattering to classical methods.** The images are 316L stainless steel printed on an EXone printer from an optical microscope at 500X, published as Warren's "ExONE Stainless Steel 316L Grains 500X" on Kaggle. That paper states that manual segmentation is accurate but time-consuming, and existing computational methods are faster but often inaccurate. It reports improved accuracy from Convolutional Neural Networks (CNN) trained on a combination of real and generated data. Its synthetic data is a Voronoi tessellation pattern combined with random synthetic noise, and I expect our synthetic split resembles it.
- **Prior work on synthetic data mostly measures boundary pixels, not grain statistics.** In a Voronoi transfer-learning study, model performance was assessed based on the accuracy of grain boundary segmentation. The authors also note that the size distribution of Voronoi cells differed from the grain size distribution observed in SEM images. That is a warning that success on synthetic images may not carry over to the real images.

## Values to compare against

- **What ASTM E112 implies for the 10% target.** The G number is logarithmic: each one-unit increase doubles grain count. My own calculation from that: a 10% error in grain count or mean area is about 0.14 G units. A 10% error in mean diameter is about 21% in area, or roughly 0.27 G units. The E112-13 interlaboratory summary (from a fragmentary text extract) says chart ratings were 0.5 to 1 G unit coarser than the measured ones, and it mentions planimetric or intercept measurements agreeing within about ±0.1 G. So a 10% count target is roughly at the level of careful manual planimetric precision. That is strict, not lenient.
- **One published grain-size error figure, source method unclear.** The deep-learning grain-size paper reports a mean error of 11.9% in the optical microscope images tested with a standard deviation of 7.6%. The extract is too fragmented for me to tell which method this number belongs to, so treat it only as a rough sense of scale.

## Reasons to doubt the planned test (my reasoning, not from sources)

1. **"Mean grain size" must be defined before the run.** Area versus equivalent diameter roughly doubles or halves how hard the 10% threshold is. The evaluator's definition should be fixed and recorded first.
2. **exclude_edge=False biases the count.** It counts truncated edge grains as whole grains. ASTM's planimetric method counts them as half. This error grows when grains are large relative to the image.
3. **min_area_px=40 and min_distance=8 have to match the grain scale in pixels.** If ground-truth grains are smaller than about 16 px across, the watershed will merge them and undercount. Dropping small regions also pushes the mean size up.
4. **The top-hat line width has to match the boundary width.** A 4 px line width assumes boundaries about that thick. Thin or broken boundaries on the real 316L images (and in noisy synthetic images) will make neighbouring grains leak together. That causes undercounting, which is the opposite of over-segmentation.
5. **fill_boundaries changes measured areas.** Whether boundary pixels are added to grains changes area by roughly the boundary width times the perimeter. That alone could be several percent for small grains.
6. **The pass test is a maximum over metrics, possibly over images.** max_rel_error ≤ 0.10 fails if either metric fails. With a small dev split, the outcome may depend on one or two images, so per-image errors should be reported, not just the summary.
7. **Synthetic noise level matters.** If the synthetic dev split is low-noise, passing says little about robustness. Noise robustness has to be tested by explicitly sweeping noise levels.

## Bottom line

I have low confidence that this has been shown before; I found no direct precedent. Before the run, I'd guess the untuned defaults will **not** reach ≤10% on both metrics, with perhaps a 30–40% chance of passing. Over- or under-segmentation from min_distance and the edge-grain bias are the likeliest causes. This guess is my judgement, not something the literature supports. Either way, the result works as a baseline for the tuning loop.

## Sources

- none
