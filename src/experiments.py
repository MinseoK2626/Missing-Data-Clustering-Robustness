"""Run paired simulations and collect tidy, machine-readable outputs."""
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score

from .clustering import fit_kmeans
from .data_generation import PRODUCTS, generate
from .evaluation import agreement, centroid_displacement, internal, reconstruction
from .imputation import impute
from .missingness import apply_missingness
from .sensitivity import uncertainty_analysis


def evaluate(frame, scaler, model, reference, profiles, common_scaler,
             reference_centers, limit, seed):
    values = scaler.transform(frame)
    labels = model.predict(values)
    metrics, aligned, mapping = agreement(reference, labels, profiles)
    centers = common_scaler.transform(pd.DataFrame(
        scaler.inverse_transform(model.cluster_centers_), columns=frame.columns))
    metrics.update(internal(values, labels, limit, seed))
    metrics["wcss"] = np.square(values - model.cluster_centers_[labels]).sum()
    metrics["common_wcss_per_store"] = np.square(common_scaler.transform(frame)
                                               - centers[labels]).sum(axis=1).mean()
    metrics["centroid_displacement"] = centroid_displacement(reference_centers, centers, mapping)
    return metrics, aligned


def cluster_selection(frame, keys, limit, seed):
    rows = []
    for k in range(2, 9):
        scaler, model = fit_kmeans(frame, seed, k)
        scores = internal(scaler.transform(frame), model.labels_, limit, seed)
        rows.append(dict(keys, k=k, wcss=model.inertia_, silhouette=scores["silhouette"]))
    inertia = np.array([row["wcss"] for row in rows])
    normalized = (inertia - inertia[-1]) / (inertia[0] - inertia[-1])
    elbow = np.argmax(1 - np.linspace(0, 1, len(rows)) - normalized)
    best = np.argmax([row["silhouette"] for row in rows])
    for index, row in enumerate(rows):
        row.update(elbow_selected=index == elbow, silhouette_selected=index == best)
    return rows


def run_factorial(config):
    rows, missingness, bias, selection, benchmarks = [], [], [], [], []
    representative = {}
    for seed in config["seeds"]:
        complete, profiles = generate(config["stores"], seed)
        common, benchmark = fit_kmeans(complete, seed)
        reference = benchmark.labels_
        full_scores = internal(common.transform(complete), reference, config["silhouette_limit"], seed)
        benchmarks.append(dict(seed=seed, latent_ari=adjusted_rand_score(profiles, reference),
                               wcss=benchmark.inertia_, **full_scores))
        first = seed == config["seeds"][0]
        if first:
            selection.extend(cluster_selection(complete, {"mechanism": "complete", "method": "none",
                                                          "target_rate": 0},
                                               config["silhouette_limit"], seed))
        for mechanism in config["mechanisms"]:
            for rate in config["rates"]:
                observed, mask = apply_missingness(complete, mechanism, rate, seed + 1000)
                keys = dict(seed=seed, mechanism=mechanism, target_rate=rate)
                for profile, group in [("all", mask), *mask.groupby(profiles)]:
                    for feature in ["all", *complete.columns]:
                        cells = group.to_numpy() if feature == "all" else group[feature]
                        missingness.append(dict(keys, profile=profile, feature=feature,
                                                masked=int(np.sum(cells)), eligible_or_all_cells=np.size(cells),
                                                rate=np.mean(cells)))
                for method in config["methods"]:
                    imputed, _ = impute(observed, method, seed)
                    scaler, model = fit_kmeans(imputed, seed)
                    metrics, aligned = evaluate(imputed, scaler, model, reference, profiles, common,
                                                benchmark.cluster_centers_, config["silhouette_limit"], seed)
                    errors, feature_bias = reconstruction(complete, imputed, mask)
                    rows.append(dict(keys, method=method,
                                     realized_product_rate=mask[PRODUCTS].to_numpy().mean(),
                                     realized_overall_rate=mask.to_numpy().mean(), **metrics, **errors))
                    bias.extend(dict(keys, method=method, feature=feature, bias=feature_bias[feature])
                                for feature in PRODUCTS)
                    if first and rate == config["sample_rate"]:
                        if mechanism in ("MAR", "MNAR"):
                            selection.extend(cluster_selection(imputed, dict(keys, method=method),
                                                               config["silhouette_limit"], seed))
                        if mechanism == "MNAR" and method == "zero":
                            pca = PCA(n_components=2).fit(common.transform(complete))
                            representative.update(complete=complete, profiles=profiles, observed=observed,
                                                  mask=mask, reference=reference, aligned=aligned,
                                                  original_pca=pca.transform(common.transform(complete)),
                                                  imputed_pca=pca.transform(common.transform(imputed)))
        print(f"Factorial seed {seed} complete", flush=True)
    return {"factorial": pd.DataFrame(rows), "missingness": pd.DataFrame(missingness),
            "imputation_bias": pd.DataFrame(bias), "cluster_selection": pd.DataFrame(selection),
            "benchmarks": pd.DataFrame(benchmarks)}, representative


def run_sample_sizes(config):
    rows = []
    largest = max(config["sample_sizes"])
    for seed in config["seeds"]:
        evaluation, profiles = generate(config["evaluation_stores"], seed + 20_000)
        training, _ = generate(largest, seed + 30_000)
        common, benchmark = fit_kmeans(training, seed)
        reference = benchmark.predict(common.transform(evaluation))
        for mechanism in config["mechanisms"]:
            observed_train, _ = apply_missingness(training, mechanism, config["sample_rate"], seed + 40_000)
            observed_eval, eval_mask = apply_missingness(evaluation, mechanism, config["sample_rate"], seed + 50_000)
            for n in config["sample_sizes"]:
                clean_scaler, clean_model = fit_kmeans(training.iloc[:n], seed)
                clean_labels = clean_model.predict(clean_scaler.transform(evaluation))
                for method in ("zero", "median"):
                    fit, test = impute(observed_train.iloc[:n], method, seed, observed_eval)
                    scaler, model = fit_kmeans(fit, seed)
                    metrics, _ = evaluate(test, scaler, model, reference, profiles, common,
                                          benchmark.cluster_centers_, config["silhouette_limit"], seed)
                    candidate = model.predict(scaler.transform(test))
                    rows.append(dict(seed=seed, mechanism=mechanism, method=method, stores=n,
                                     realized_train_rate=observed_train.iloc[:n][PRODUCTS].isna().to_numpy().mean(),
                                     realized_eval_rate=eval_mask[PRODUCTS].to_numpy().mean(),
                                     clean_ari=adjusted_rand_score(reference, clean_labels),
                                     same_size_ari=adjusted_rand_score(clean_labels, candidate), **metrics))
        print(f"Sample-size seed {seed} complete", flush=True)
    return pd.DataFrame(rows)


def summarize(frame, groups):
    measures = frame.select_dtypes(include="number").columns.difference([*groups, "seed"])
    summary = frame.groupby(groups)[list(measures)].agg(["mean", "std", "count"])
    summary.columns = ["_".join(parts) for parts in summary.columns]
    return summary.reset_index()


def run(config):
    tables, representative = run_factorial(config)
    tables["sample_size"] = run_sample_sizes(config)
    tables["factorial_summary"] = summarize(tables["factorial"], ["mechanism", "method", "target_rate"])
    tables["sample_size_summary"] = summarize(tables["sample_size"], ["mechanism", "method", "stores"])
    tables.update(uncertainty_analysis(representative, config))
    return tables, representative
