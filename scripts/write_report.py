"""Regenerate the expanded research report from validated tables."""
import json
from pathlib import Path

import pandas as pd

from src.statistics import distribution


def main():
    root = Path("results")
    expanded = root / "expanded"
    analysis = json.loads((expanded / "summary.json").read_text())
    manifest = json.loads((expanded / "manifest.json").read_text())
    design, validation = analysis["design"], analysis["validation"]
    config = manifest["config"]
    rows = analysis["summary"]
    mcar = [row for row in rows if row["mechanism"] == "MCAR" and row["target_rate"] == .30]
    paired = next(row for row in analysis["paired"] if row["mechanism"] == "MCAR"
                  and row["target_rate"] == .30 and (row["left"], row["right"]) == ("zero", "iterative"))
    ranks = [row for row in analysis["ranking"] if row["mechanism"] == "MCAR" and row["target_rate"] == .30]
    rank = next(row for row in ranks if row["method"] == "iterative")
    example = validation["example"]
    sample = pd.read_csv(root / "tables/sample_size.csv")
    small = distribution(sample.query("mechanism == 'MNAR' and method == 'zero' and stores == 500").ari)
    large = distribution(sample.query("mechanism == 'MNAR' and method == 'zero' and stores == 18000").ari)
    stores = pd.read_csv(root / "tables/store_stability.csv")
    discordant = sum((stores.gmm_max_posterior >= .80) & (stores.stability < .60))
    association = stores[["stability", "gmm_max_posterior"]].corr(method="spearman").iloc[0, 1]
    warnings_rate = design["warnings"] / design["completed"]
    mcar_table = "\n".join(
        f"| {row['method']} | {a['mean']:.3f} | {a['median']:.3f} | {a['sd']:.3f} | "
        f"{a['q05']:.3f}–{a['q95']:.3f} | {a['low']:.3f}–{a['high']:.3f} | {a['n']} |"
        for row in mcar for a in [row["metrics"]["ari"]])
    interaction_rows = []
    for family in ("mechanism × method", "severity × method", "mechanism × severity"):
        row = max((row for row in analysis["interactions"] if row["interaction"] == family
                   and row["mean"] is not None), key=lambda item: abs(item["mean"]))
        interaction_rows.append(f"- **{family}**. The largest observed absolute mean among the prespecified contrasts was "
                                f"{row['mean']:+.3f} ARI (95% interval {row['low']:+.3f} to {row['high']:+.3f}; "
                                f"n = {row['n']}). The ordered terms are `{row['contrast']}`; coefficients are +1, −1, −1, +1.")
    interaction_text = "\n".join(interaction_rows)
    report = f"""---
title: "Beyond Data Volume"
subtitle: "Clustering robustness under systematic missingness"
author: "Minseo Kim · Independent computational research"
date: "2026"
geometry: margin=1in
---

# 1. Abstract

Missing sales records and genuine zeros carry different information. We simulated
overlapping retail profiles to study how this distinction affects unsupervised
segmentation. The expanded factorial produced {design['completed']:,} usable runs
out of {design['planned']:,} planned runs over {design['seeds']} completed seeds.
At 30% MCAR, iterative imputation improved mean benchmark ARI over zero fill by
{-paired['mean']:.3f} (95% seed-bootstrap interval {-paired['high']:.3f} to
{-paired['low']:.3f}). In {validation['changed_ten_percent']:,} runs, silhouette
improved while at least 10% of aligned assignments changed. A separate original
sample-size experiment and store cohort illustrate residual finite-sample
distortion and the gap between model confidence and assignment stability.
Inference concerns this synthetic generator and the tested pipelines.

# 2. Introduction

Retail data can record zero sales because a product is absent, while missing data
can reflect an incomplete feed. Our controlled simulation preserves both kinds
of information before masking. This allows comparison between a partition fit
after preprocessing and a complete-data reference on the same cohort. The
analysis uses synthetic data throughout.

# 3. Related literature

Rubin formalized mechanisms for missingness, and Little and Rubin connect those
mechanisms to assumptions behind incomplete-data procedures. Rousseeuw defined
the silhouette as an internal geometric measure. Von Luxburg discusses the scope
and limitations of clustering stability. Meng motivates our emphasis on data
quality alongside quantity. Our finite sample-size experiment is not a replication
of the data-defect correlation identity.

# 4. Research questions

1. How do mechanism, severity and imputation jointly affect benchmark agreement?
2. Can internal separation improve when individual assignments change?
3. How does sample size affect agreement when masking persists?
4. How consistent are imputation rankings across independent simulated cohorts?
5. Does confidence under a fitted mixture identify stable K-means assignments?

# 5. Mathematical framework

Given a feature vector $x_i$, the K-means fit minimizes $\\sum_i \\|z_i - \\mu_{{c_i}}\\|_2^2$
over cluster centers $\\mu$ and assignments $c$, with feature-wise standardized inputs
$z_i$. ARI compares co-membership pairs with chance correction. Silhouette for
store $i$ is $(b_i-a_i)/\\max(a_i,b_i)$, where $a_i$ is average within-cluster
distance and $b_i$ is the smallest average distance to another cluster. Hungarian
matching maximizes label overlap, after which assignment change is the fraction
of unmatched stores. Complete-data K-means is a reference partition. The
generator's latent profiles remain separate from clustering and imputation.

MCAR uses Bernoulli probability $r$ in every eligible product cell. MAR uses
fully observed log traffic, evening share and category offsets in a logistic
model. MNAR uses its own underlying log product sale in a logistic model. The
latter also depends on genuine zero sales. For MAR and MNAR, the intercept is
chosen so average product-cell propensity equals the target.

Zero fill encodes absence, median fill uses an observed marginal statistic,
five-neighbor KNN borrows values from similar observed standardized features,
and iterative imputation uses chained Bayesian ridge. Observed values are kept;
multivariate estimates are clipped to nonnegative sales. See
[methodology](methodology.md) for coefficients, feature construction and metrics.

# 6. Experimental design

Within each seed, a 5,000-store cohort and one complete-data fit serve every
condition. A seed and mechanism–rate combination define a common mask shared
by all imputation methods. Product-cell masking targets range from 5% to 40%.
We retain product-only and dataset-wide realized rates. K-means uses four
clusters, 12 initializations, and scaling fitted separately to each frame.
Silhouette uses a seeded subset of 1,000 stores. The original study tested elbow
and silhouette choices separately and found different cluster counts for the
two selection rules on its first seed.

Seed is the unit for uncertainty. For each configuration we estimate means,
medians, sample SDs, the interquartile range, and 5th and 95th percentiles.
Percentile 95% mean intervals use 4,000 bootstrap resamples of seed-level
outcomes. Paired effects subtract within seed before resampling. Interactions
use within-seed differences-in-differences. Ranking uses only complete
four-method seed blocks and splits credit for ties. Intervals quantify
Monte Carlo precision under this generator. They do not give uncertainty
for real-world retailers and are not simultaneous intervals.

The sample-size and uncertainty experiments below use preserved original
outputs. Held-out imputation and scaling use training data only.

# 7. Results

## RQ1. Missingness and preprocessing

At 30% MCAR, the strategies produced the following seed-level summaries.

| Method | Mean ARI | Median | SD | P05–P95 | 95% mean interval | Runs |
|---|---:|---:|---:|---:|---:|---:|
{mcar_table}

ARI and reconstruction error answer different questions. Business use would
require auditing membership alongside reconstruction quality. Results depend on
the simulated missingness propensities and input features.

## RQ2. Validation metric reliability

Silhouette improved in {validation['improved']:,}/{design['completed']:,}
({validation['improved']/design['completed']:.1%}) usable runs. Among those,
{validation['changed_ten_percent']:,} changed at least 10% of assignments and
{validation['ari_below_half']:,} had ARI below 0.50. Among the improved cases,
the lowest ARI was {example['ari']:.3f} at seed {example['seed']}, under
{example['mechanism']} with {example['target_rate']:.0%} masking and {example['method']}
imputation. That run changed {example['change_rate']:.1%} of aligned assignments.
The pooled Spearman association between silhouette and ARI was {validation['spearman']:.3f}.
These thresholds are descriptive and the pooled numbers do not make runs within
a seed independent.

## RQ3. Data volume and distortion

The original {len(sample)} held-out runs vary training size from 500 to 18,000.
Under 30% MNAR with zero fill, the mean was {small['mean']:.3f} at 500
(95% interval {small['low']:.3f} to {small['high']:.3f}) and {large['mean']:.3f}
at 18,000 ({large['low']:.3f} to {large['high']:.3f}). Seed SD fell from
{small['sd']:.3f} to {large['sd']:.3f}. The evaluation population stayed
fixed within each seed. This contrast includes the cost of missing deployment
features and makes no claim about an asymptotic limit.

## RQ4. Variation and matched interactions

At 30% MCAR, iterative imputation exceeded zero fill by {-paired['mean']:.3f}
ARI (95% interval {-paired['high']:.3f} to {-paired['low']:.3f}; {paired['n']}
pairs). Iterative imputation had a fractional best-ARI share of
{rank['win_share']:.1%} across {rank['n']} complete groups. The summary
reports lower-tail behavior alongside mean performance. Below, the largest
observed contrast in each family is shown descriptively because selecting an
extreme can exaggerate its magnitude.

{interaction_text}

The full matched contrasts and ranks are in the machine-readable results.
A pipeline with good mean results but weak lower-tail agreement may warrant
additional checks on cohort composition and mask assumptions.

## RQ5. Confidence versus stability

The original seed-11 diagnostic used {len(stores):,} stores, a four-component
GMM on one iteratively imputed 30% MNAR frame, and the modal aligned K-means
assignment frequency across 48 preprocessing scenarios. Maximum posterior and
scenario stability had Spearman correlation {association:.3f}. For {discordant}
stores the highest posterior was at least 0.80 while stability was below 0.60.
The combination suggests cases to review but is not a calibrated accuracy
score. A separate IQR shift experiment tests sensitivity to systematically
lower or higher unobserved sales within this cohort.

# 8. Discussion

A larger sample stabilizes some estimated partitions without removing systematic
measurement distortion. Likewise, stronger internal geometric separation can
appear after a preprocessing transformation that changes business-facing store
assignments. In an illustrative workflow, review the provenance of masked sales
and assess alternative imputations before applying a single assortment rule.
No revenue, profitability or business decision quality was measured.

# 9. Limitations

The results depend on one generator, selective availability mechanisms, a
single scaling recipe and K-means geometry. A reference partition has its own
model error. MNAR mechanisms cannot generally be identified from observed
records alone. Seed variation, systematic distortion, conditional posterior
confidence, assignment stability under alternatives, and uncertainty about
the whole data-generating process describe different phenomena.

The ledger records {design['failures']} failures and {design['unattempted']}
unattempted configurations. {design['warnings']} usable runs ({warnings_rate:.1%})
raised convergence warnings. Capped fits are included and flagged. The
pairing and ranking analyses use only the observed matching seeds for each
comparison. The GMM analysis is restricted to a single original cohort.

# 10. Future research

Vary profile overlap, dependence and assortment propensity; compare
alternative clustering geometry; propagate missingness uncertainty with
stochastic multiple imputation and Bayesian mixture models; and use suitable
public data or evaluate review decisions against measured outcomes.

# 11. References

- Rubin, D. B. (1976). Inference and missing data. *Biometrika* 63(3), 581–592. <https://doi.org/10.1093/biomet/63.3.581>
- Little, R. J. A., & Rubin, D. B. (2019). *Statistical Analysis with Missing Data*, 3rd ed. Wiley. <https://doi.org/10.1002/9781119482260>
- Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics* 20, 53–65. <https://doi.org/10.1016/0377-0427(87)90125-7>
- von Luxburg, U. (2010). Clustering stability: An overview. *Foundations and Trends in Machine Learning* 2(3), 235–274. <https://doi.org/10.1561/2200000008>
- Meng, X.-L. (2018). Statistical paradises and paradoxes in big data (I): Law of large populations, big data paradox, and the 2016 US presidential election. *Annals of Applied Statistics* 12(2), 685–726. <https://doi.org/10.1214/18-AOAS1161SF>

# 12. Reproducibility appendix

The deterministic seed list is in `configs/expanded.yaml`. The design reuses
the first eight original seeds and adds consecutive seeds 1001–1072.
The recorded run used Python {manifest['python']}, {manifest['workers']} processes
and {manifest['invocation_seconds']:.1f} seconds for the recorded invocation.
The manifest records the numerical-library versions and worker errors.

```sh
python -m pip install -r requirements.txt
python -m pytest -q
python run_expanded.py --jobs 4
python -m scripts.analyze_expanded
python -m scripts.write_report
pandoc reports/expanded_report.md --pdf-engine=xelatex -o reports/expanded_report.pdf
python -m scripts.build_site
```

Outputs and their columns are described in [data dictionary](../data/expanded.md).
The original study remains in [the archived report](research_report.md).
"""
    assert len(config["rates"]) == 5
    Path("reports/expanded_report.md").write_text(report)


if __name__ == "__main__":
    main()
