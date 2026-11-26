# Methodology

## Synthetic stores

The generator draws urban commuter, residential, university-area and suburban
family profiles with probabilities 26%, 29%, 20% and 25%. Log traffic and log
basket value receive profile offsets and independent Gaussian noise with standard
deviations 0.40 and 0.24. Traffic is rounded from 4,300 times exponentiated log
volume. Average transaction value starts from 12 currency units on the same
multiplicative scale. Total monthly sales equal traffic times average transaction
value. Weekend and evening shares use logistic transforms of noisy,
profile-specific log odds. Noise and shared feature distributions produce overlap.

Five categories have log-normal assortment weights with profile-specific offsets
and log-scale standard deviation 0.45. A Bernoulli hurdle makes a category
structurally zero with probability depending on the category, profile and log
traffic. Category sales divide the remaining weights by their sum plus a fixed
weight of 0.40 for unmodeled categories and multiply by total sales. This
introduces positive volume dependence, competition for the sales share and
structural zeros. Exact coefficients are in [the generator](../src/data_generation.py).
Latent profiles enter only descriptive tabulation and external evaluation.

## Missingness and imputation

- MCAR uses a constant Bernoulli probability for each eligible cell.
- MAR uses the logistic function of standardized negative log traffic, 0.55 times
  standardized evening share, a product-specific offset and a calibrated intercept.
  Traffic and evening share are always observed.
- MNAR uses a logistic score of −1.25 times standardized log(1 + product sales)
  within each product. Low and zero sales have higher masking probabilities.
  Observed data alone generally cannot distinguish this mechanism from
  alternatives with different distributions of missing values.

The intercept targets the mean probability within the eligible matrix. Realized
rates fluctuate around targets. Common random numbers across rates and mechanisms
pair comparisons within seeds. Both positive sales and genuine zeros are
eligible. All-feature masking rates use all ten columns as the denominator,
yielding about half the product-cell rate. The missingness table also reports
counts and denominators by feature and latent profile.

Zero fill assumes that missing implies no sales. Median fill preserves a
univariate center and ignores conditional structure. Five-neighbor, distance-
weighted KNN uses Euclidean distances on shared observed standardized features.
Iterative imputation uses deterministic chained Bayesian ridge regressions for
up to 15 iterations. The two multivariate methods fit observed-data scaling on
training rows, return estimates to currency units and clip negative product
estimates to zero. Observed values are preserved. Distances, regression form,
and the selective availability of training cases can all matter under MNAR.
This implementation uses single imputations.

## Clustering and metrics

Each completed frame gets a separately fitted standard scaler and a four-cluster
K-means model with 12 initializations. Complete-data K-means uses the same recipe
and is the paired reference. ARI and NMI compare partitions. Latent-profile ARI
checks overlap with the generator's profile labels. For individual changes and
centroids, Hungarian matching maximizes agreement with the reference. Centroid
distances are averaged over equally weighted matched clusters in the
complete-data standardized coordinate system.

Silhouette is computed on a shared seeded uniform subset within each replicate
(up to 1,000 stores in full mode). Davies–Bouldin and WCSS use all evaluated
rows. Scenario-native WCSS depends on preprocessing and row count. The common
space WCSS per store holds units fixed, although the underlying feature values
still vary by imputation. Reconstruction MAE, RMSE and signed feature bias
(imputed minus truth) use only masked cells in original units.

The first seed's cluster-count check evaluates 2–8 clusters on complete data
and under MAR and MNAR at 30% target masking. The silhouette rule selects its
maximum. The elbow heuristic takes the largest vertical gap between normalized
inertia and the straight line joining the endpoints. Both depend on the search
range and chosen scaling.

## Sample-size design

Within each seed, sample sizes use nested prefixes of an independent training
cohort. A separate fixed 2,500-store evaluation cohort is shared by all
training sizes. Both training and evaluation are masked at 30% product-cell
target, once per mechanism for each seed. Benchmark labels come from predicting
on clean evaluation features with K-means trained on the largest complete
training cohort. Imputation and model fitting use the training prefix only.
A clean model trained on the same prefix supplies a clean learning-curve
comparison and a same-size reference ARI. The largest clean model's ARI of one
is by construction. The largest corrupted model still assigns from corrupted
evaluation features, so this experiment measures total segmentation distortion
when missingness persists in both training and deployment.

Tables report paired seed-level observations plus means and sample SDs. The SDs
describe simulation variability across seeds. Observations within a seed are
dependent, and the project makes no significance claims.

## Uncertainty, sensitivity and decisions

On the first complete cohort, we repeat masking across all mechanisms at
30% target and refit all four methods (48 paired scenarios in full mode).
Report the frequency of the modal aligned assignment, frequency of departure
from the benchmark, normalized entropy of scenario frequencies and
co-clustering frequency for a seeded sample of unordered store pairs (all
pairs in quick mode). Spearman correlations relate stability to mean masked
product count and the complete-data relative gap between the two nearest
K-means centroids. The boundary margin is available in this simulation and
would require a proxy in deployment.

A full-covariance four-component Gaussian mixture with five initializations
and diagonal regularization of 0.00001 is fitted on the iterative-MNAR
completed frame. Output includes maximum posterior, entropy divided by log(4)
and the gap between the two largest posteriors. Posterior concentration
describes uncertainty within the estimated mixture. Scenario stability
describes sensitivity of K-means to the selected analysis choices. The signals
measure different quantities and can disagree.

For MNAR sensitivity, shift missing iterative estimates by −0.50, −0.25, 0,
+0.25 and +0.50 times each product's observed positive-sales IQR and clip to zero.
Refit scaling and clustering at each shift and compare aligned labels and
centroids. The range illustrates assumptions about unobserved sales.

Cluster strategy is considered when stability and maximum posterior are both
at least 0.80. Collect more data when stability is below 0.60 or maximum
posterior is below 0.55. Other stores receive managerial review. These
thresholds are illustrative. In sensitivity scenarios, a cluster-strategy
store whose aligned cluster changes is sent to managerial review. This
evaluates recommendation sensitivity without asserting a measured effect on
inventory, promotions, or sales.
