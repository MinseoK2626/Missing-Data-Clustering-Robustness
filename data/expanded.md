# Expanded study data dictionary

The primary factorial is in `results/expanded/`. The immutable original
factorial, sample-size and uncertainty outputs remain in `results/tables/`.
All data are synthetic.

| File | Grain and fields |
| --- | --- |
| `manifest.json` | Configuration, seed list, numerical package versions, worker count, elapsed invocation time and worker errors |
| `factorial.csv` | One usable seed × mechanism × target_rate × method row, with benchmark ARI/NMI, latent-profile ARI, aligned change rate, silhouette, Davies–Bouldin, within-cluster squared distance, common-space squared distance per store, displacement and masked-cell MAE/RMSE |
| `benchmarks.csv` | One complete-data reference per attempted seed, with latent-profile ARI, silhouette, Davies–Bouldin and WCSS |
| `diagnostics.csv` | A status and warning/error message for each attempted configuration within a checkpointed seed. A convergence warning yields a usable capped fit. A failed configuration has no performance row |
| `missingness.csv` | Counts, denominators and observed missingness by seed, mechanism, target, feature and profile; `all` features includes all ten columns |
| `imputation_bias.csv` | Signed masked-cell estimate minus truth by seed, mechanism, target, method and product, in sales units |
| `factorial_summary.csv` | Per configuration, successful count, planned count, failures, convergence warnings, and distribution summaries under the `metrics_` prefix |
| `summary.json` | Validated design totals, metric distributions, validation counts, contrasts and rank shares. The website reads the same estimates after building |
| `validation.csv` | Factorial outcomes with seed-matched reference silhouette and change from that value |
| `paired.csv` | Left method minus right method on ARI, calculated on matching seeds |
| `ranking.csv` | Fractional win share among seeds with results for all methods, with equal credit for tied maxima |
| `interactions.csv` | Matched ARI differences-in-differences. Terms are ordered and have coefficients +1, −1, −1, +1 |

Rates use unit fractions. `target_rate` and `realized_product_rate` use the
five eligible sales features. `realized_overall_rate` uses all ten features.
`change_rate` also uses a unit fraction. MAE, RMSE and bias use synthetic currency.
The displacement columns use complete-data standardized units. WCSS depends on
the scaling and rows of each scenario, and comparisons require care.

In estimates, `n` is the usable seed count, `sd` is the sample standard deviation,
`q05` and `q95` are empirical tail percentiles, `iqr = q75 − q25`, and `low` and
`high` are 95% percentile-bootstrap limits for the **mean**. Empty cells represent
undefined estimates. CIs resample matched seed blocks within each contrast.
They quantify simulation-estimate precision under the specified generator.
