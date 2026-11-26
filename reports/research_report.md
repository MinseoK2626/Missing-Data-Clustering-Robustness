# Beyond Data Volume

## 1. Abstract

We simulate convenience-store segmentation under three missingness mechanisms,
five masking targets and four imputation methods. Across 480 factorial
runs, iterative imputation minimized masked-cell RMSE in all 15
mechanism–rate groups and maximized mean benchmark ARI in 14. A MAR
scenario yielded higher silhouette than its complete-data benchmark while
changing 13.5% of aligned assignments. Under 30% MNAR masking and zero fill,
increasing training size from 500 to 18,000 improved mean held-out ARI from
0.568 to 0.718 and lowered its replicate SD from 0.152 to 0.010. In a
5,000-store uncertainty analysis, 183 stores had confident mixture
membership despite low assignment stability across scenarios. These results
characterize the specified generator and analysis pipeline.

## 2. Introduction

Retail segmentation often begins by assuming that empty fields can be filled
consistently across stores. In an internship segmentation project, a zero
could plausibly describe a product a store did not offer, but it could also
represent a reporting gap. Because silhouette is computed after preprocessing,
it can reward separation created by preprocessing itself. We use a controlled
synthetic benchmark so that the effect of the assumptions can be measured.

## 3. Related literature

Rubin (1976) formalized conditions under which the missingness process can be
ignored for statistical inference. Here MCAR makes the eligible-cell mask
independent of the features, MAR conditions on always-observed covariates, and
MNAR depends on the value hidden by the mask. Rousseeuw (1987) introduced
silhouette as an internal comparison of within-cluster cohesion and
nearest-cluster separation. It does not compare partitions across
preprocessing choices. Meng (2018) showed how data quality and the dependence
between inclusion and outcomes can shape error even in very large datasets.
Our clustering simulation draws inspiration from that distinction without
replicating Meng's finite-population identity or applying it to ARI.

## 4. Research questions

1. How do the missingness mechanism and imputation strategy affect store
   assignments and centroid locations?
2. When do internal separation and complete-data agreement give different
   assessments?
3. How do mean distortion and replicate variability change with training size?
4. Can scenario stability and conditional mixture probabilities help allocate
   managerial review and improved data collection?

H1 predicts that zero fill can systematically distort clustering when masked
values include positive sales. H2 predicts a divergence between internal
validation and benchmark agreement. H3 predicts that more data can reduce
variability while leaving persistent distortion. H4 predicts that scenario
stability and probabilistic membership can help identify uncertain stores.

## 5. Data-generating process

Each seed creates overlapping urban commuter, residential, university-area,
and suburban family store profiles. Noisy traffic and basket size generate
monthly total sales. Five correlated product-sales features draw from a shared
sales budget, with profile-specific assortment and a structural-zero hurdle.
Weekend and evening customer proportions have separate noisy profile offsets.
See the [generator and exact coefficients](../src/data_generation.py) and the
[methodology](methodology.md).

## 6. Experimental methodology

The 480 factorial runs cross eight seeds, five masking rates, three mechanisms
and four imputation methods. Only the five product-sales columns can be
masked. Standardized four-cluster K-means uses 12 initializations in each run.
We compare against seed-matched complete-data K-means, align assignments
using the Hungarian algorithm, and calculate masked-cell reconstruction
errors in sales units. Silhouette uses the same seeded 1,000-store subset of
each 5,000-store cohort for all preprocessing scenarios within a seed.

The sample-size study uses nested training prefixes and 2,500 independent
evaluation stores held fixed within seed. The benchmark is trained on the
largest clean cohort and predicts on clean features. Zero and median scenarios
use 30% masking in training and evaluation. We compare to clean models
trained at each sample size and report mean and sample standard deviation
over eight seeds.

On the first seed, 48 repeated masking and preprocessing scenarios produce
store-level label frequencies, assignment change rates and sampled
pairwise co-clustering frequencies. A full-covariance Gaussian mixture fit
on the iterative MNAR frame estimates posterior memberships. The MNAR
sensitivity analysis shifts only artificially masked product sales in units
of the observed positive-sales IQR before refitting K-means.

## 7. Results

### Masking and reconstruction

In the representative cohort, structural zeros ranged from 1.68% for
beverages to 16.90% for household products. At 30% target product masking,
the overall rate across all ten features averaged 14.90% for MCAR, 14.93%
for MAR and 14.97% for MNAR. Under MAR it was 18.79% in residential stores
and 9.32% in urban commuter stores, reflecting their different observed
traffic and evening profiles. [Missingness counts](../results/tables/missingness.csv)

Zero fill produced negative mean reconstruction bias across products and
mechanisms at 30% masking. Iterative imputation had the smallest mean
masked-cell RMSE in all 15 mechanism–rate groups. Its advantage in
reconstruction did not guarantee the strongest partition agreement.

### Partition agreement at 30% target product masking

| Mechanism | Zero ARI | Median ARI | KNN ARI | Iterative ARI |
| --- | ---: | ---: | ---: | ---: |
| MCAR | 0.632 | 0.751 | 0.811 | 0.861 |
| MAR | 0.633 | 0.642 | 0.826 | 0.875 |
| MNAR | 0.730 | 0.761 | 0.782 | 0.853 |

At 30% MCAR, mean centroid displacement was 0.997 complete-standardized
units for zero fill and 0.110 for iterative imputation. Across all masking
targets, zero fill beat median on mean ARI in three of 15 groups and had
the best mean ARI of all methods at 5% MNAR (0.947). The complete-data
partition had mean latent-profile ARI 0.115, consistent with substantial
overlap and the partition also reflecting continuous store volume.
[Factorial summary](../results/tables/factorial_summary.csv) · [Centroid figure](../results/figures/06_centroid_displacement.svg)

### Internal versus external validation

Silhouette met or exceeded its seed-matched complete-data value in 256 of
480 runs. The lowest benchmark ARI among those runs was 0.678. In that case
(MAR, 40%, KNN, seed 23), silhouette rose from 0.160 to 0.167 and 13.48%
of aligned assignments changed. No run paired a silhouette at or above
benchmark with ARI below 0.50. The pooled Spearman correlation between
silhouette and ARI was 0.368. This is descriptive because conditions share
seeds and masking draws. In the separate first-seed cluster-count analysis,
the elbow rule chose four and silhouette chose two on complete, MAR and MNAR
data across every examined preprocessing method. We saw a difference
between selection rules and no change in their selections across those
preprocessing choices.
[Silhouette–ARI figure](../results/figures/05_silhouette_vs_ari.svg) · [Cluster selection](../results/tables/cluster_selection.csv)

### Sample size

| Mechanism | Method | ARI at 500, mean (SD) | ARI at 18,000, mean (SD) |
| --- | --- | ---: | ---: |
| MCAR | Zero | 0.461 (0.125) | 0.615 (0.031) |
| MCAR | Median | 0.493 (0.126) | 0.751 (0.033) |
| MAR | Zero | 0.514 (0.103) | 0.650 (0.021) |
| MAR | Median | 0.487 (0.134) | 0.624 (0.038) |
| MNAR | Zero | 0.568 (0.152) | 0.718 (0.010) |
| MNAR | Median | 0.554 (0.147) | 0.770 (0.024) |

Across the six pipelines, mean held-out ARI improved and seed-to-seed
variability decreased between the smallest and largest training sets.
Several trajectories were nonmonotonic. Under MNAR zero fill, mean ARI was
0.724 at 5,000 and 0.718 at 18,000. Mean silhouette changed from 0.139 at
500 to 0.142 at 18,000 while ARI moved substantially more on its own scale.
The gap at 18,000 includes the consequences of masking the evaluation
data. [Learning curves](../results/figures/07_sample_size.svg) · [Summary](../results/tables/sample_size_summary.csv)

### Store uncertainty and MNAR sensitivity

The benchmark boundary margin correlated positively with scenario stability
(Spearman ρ = 0.754). Mean masked product count had a weak positive
correlation (ρ = 0.116), contrary to the expected negative association.
Among sampled pairs, stores in the same benchmark cluster co-clustered
in 85.4% of scenarios on average, versus 6.8% for different-benchmark pairs.
Maximum GMM posterior correlated weakly with scenario stability
(ρ = 0.125). There were 183 stores with posterior ≥ 0.80 and stability < 0.60.

The illustrative policy assigned 3,550 stores to cluster strategy, 1,061
to review and 389 to additional data collection. A +0.50 IQR shift
lowered benchmark ARI from 0.854 to 0.776 and increased mean centroid
displacement from 0.191 to 0.519 standardized units. It changed the aligned
assignment of 5.42% of stores relative to the unshifted model and escalated
1.40% of all stores to managerial review. At −0.50 IQR, the assignment
and decision change rates were 5.60% and 1.82%. Neither direction
improved benchmark ARI in this cohort.
[Store-level results](../results/tables/store_stability.csv) · [Sensitivity](../results/tables/sensitivity.csv)

## 8. Discussion

**H1 was supported within the simulated design.** Zero fill consistently
underestimated masked sales on average and usually produced weaker
partitions. The 5% MNAR exception is compatible with a low-value masking
mechanism and shows that the ARI ranking depends on the scenario.

**H2 was supported in a qualified sense.** Improved internal separation
coexisted with meaningful assignment changes. An extreme example of
improved silhouette with ARI below 0.50 was absent. The tested partitions
had modest silhouette scores in absolute terms.

**H3 was supported over the tested sample-size range.** More training
stores reduced across-seed variability at the endpoints in each pipeline,
while benchmark disagreement persisted. The results do not establish an
asymptotic limit.

**H4 was supported as a diagnostic, with operational value unresolved.**
Cross-scenario stability recognized boundary-sensitive stores and
provided information beyond the fitted mixture's posterior. A count of
missing products alone did not identify lower stability in this cohort.
Business rules would require independent validation.

## 9. Business implications

Segmentation can inform product assortment, inventory allocation and
promotions. Under the illustrative policy, stores with both stable K-means
assignment and high maximum mixture posterior can be considered for a
cluster-level strategy. Stores in the middle qualify for targeted review,
and stores with weak signals qualify for additional data collection or
individual assessment. Teams could first reconcile a missing sales feed
against merchandise records before changing an assortment. The study
measures decision changes under alternate assumptions. It provides no
experimental estimate of forecast, sales or inventory improvement.

## 10. Limitations

- The distributions, features, product hurdle and missingness equations
  represent a single synthetic environment. Covariates are fully observed
  by design. Missingness probabilities are known to the simulator.
- Complete-data K-means inherits the geometry and choices of the algorithm.
  It estimates a partition of the features and is evaluated separately from
  the overlapping latent profiles.
- The sample-size comparison combines missingness during training and
  evaluation. It cannot isolate the effect of collecting more complete
  deployment features. Each seed has a different holdout population.
- Silhouette and WCSS use imputation-specific scaled feature spaces.
  Across-seed SD is descriptive and paired scenarios share draws.
- Iterative imputation reached the 15-iteration cap before its early-stopping
  condition in 14 fits during the full run. The reported results use those capped estimates.
- The uncertainty analysis uses one cohort and a selected scenario grid.
  GMM posteriors are model-conditional and may be concentrated even when
  the K-means assignment varies. Scenario frequencies and sensitivity
  shifts do not identify an MNAR mechanism.

## 11. Future research

Separating missingness at training and evaluation would clarify the value of
collecting better deployment data. Alternative generators could vary profile
overlap, tail behavior and category absence. Stochastic multiple imputation
could distinguish imputation uncertainty from variation across model
choices. Evaluating the decision framework would require independently
verified business outcomes and sensitivity to the cost of review.

## 12. References

- Meng, X.-L. (2018). Statistical paradises and paradoxes in big data (I). Law of large populations, big data paradox, and the 2016 US presidential election. *Annals of Applied Statistics*, 12(2), 685–726. [DOI](https://doi.org/10.1214/18-AOAS1161SF)
- Rubin, D. B. (1976). Inference and missing data. *Biometrika*, 63(3), 581–592. [DOI](https://doi.org/10.1093/biomet/63.3.581)
- Rousseeuw, P. J. (1987). Silhouettes. A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, 53–65. [DOI](https://doi.org/10.1016/0377-0427(87)90125-7)
