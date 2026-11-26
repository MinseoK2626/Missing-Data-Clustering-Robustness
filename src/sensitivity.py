"""Evaluate uncertainty on a fixed population and vary missing sales assumptions."""
import numpy as np
import pandas as pd
from scipy.special import xlogy
from scipy.stats import spearmanr
from sklearn.mixture import GaussianMixture

from .clustering import fit_kmeans
from .data_generation import PRODUCTS
from .evaluation import agreement, align, boundary_margin, centroid_displacement
from .imputation import impute
from .missingness import apply_missingness


def decision(stability, posterior):
    return np.select([(stability >= .80) & (posterior >= .80),
                      (stability < .60) | (posterior < .55)],
                     ["Cluster strategy", "Collect more data"], default="Managerial review")


def entropy(probabilities):
    return -xlogy(probabilities, probabilities).sum(axis=1) / np.log(probabilities.shape[1])


def uncertainty_analysis(example, config):
    seed = config["seeds"][0]
    complete, profiles = example["complete"], example["profiles"]
    common, benchmark = fit_kmeans(complete, seed)
    reference = benchmark.labels_
    labels, missing_counts = [], []
    for trial in range(config["stability_repeats"]):
        for mechanism in config["mechanisms"]:
            observed, mask = apply_missingness(complete, mechanism, config["sample_rate"], seed + 60_000 + trial)
            missing_counts.append(mask.sum(axis=1))
            for method in config["methods"]:
                frame, _ = impute(observed, method, seed + trial)
                _, model = fit_kmeans(frame, seed + trial)
                labels.append(align(reference, model.labels_)[0])
    assignments = np.asarray(labels).T
    probabilities = np.column_stack([(assignments == k).mean(axis=1) for k in range(4)])
    stability = probabilities.max(axis=1)
    missing = np.mean(missing_counts, axis=0)
    margin = boundary_margin(common.transform(complete), benchmark.cluster_centers_)

    base, _ = impute(example["observed"], "iterative", seed)
    base_scaler, base_cluster = fit_kmeans(base, seed)
    mixture = GaussianMixture(n_components=4, covariance_type="full", n_init=5,
                              reg_covar=1e-5, random_state=seed)
    posterior = mixture.fit(base_scaler.transform(base)).predict_proba(base_scaler.transform(base))
    top_two = np.sort(posterior, axis=1)[:, -2:]
    base_action = decision(stability, top_two[:, 1])
    stores = pd.DataFrame(dict(store_id=complete.index, profile=profiles.to_numpy(), benchmark=reference,
                               modal_cluster=probabilities.argmax(axis=1), stability=stability,
                               scenario_entropy=entropy(probabilities),
                               change_frequency=(assignments != reference[:, None]).mean(axis=1),
                               mean_masked_features=missing, boundary_margin=margin,
                               gmm_max_posterior=top_two[:, 1], gmm_entropy=entropy(posterior),
                               gmm_posterior_gap=top_two[:, 1] - top_two[:, 0], decision=base_action))
    left, right = np.triu_indices(len(complete), k=1) if len(complete) <= 650 else sample_pairs(len(complete), seed)
    pairs = pd.DataFrame(dict(store_a=left, store_b=right,
                              co_cluster_frequency=(assignments[left] == assignments[right]).mean(axis=1),
                              same_benchmark=reference[left] == reference[right]))

    results, store_shifts = [], []
    base_labels = align(reference, base_cluster.labels_)[0]
    shifts = [-.50, -.25, 0, .25, .50]
    for shift in shifts:
        frame = base.copy()
        for feature in PRODUCTS:
            masked = example["mask"][feature]
            positive = example["observed"].loc[example["observed"][feature] > 0, feature]
            iqr = positive.quantile(.75) - positive.quantile(.25)
            frame.loc[masked, feature] = (base.loc[masked, feature] + shift * iqr).clip(lower=0)
        scaler, model = fit_kmeans(frame, seed)
        metrics, aligned, mapping = agreement(reference, model.labels_, profiles)
        centers = common.transform(pd.DataFrame(
            scaler.inverse_transform(model.cluster_centers_), columns=frame.columns))
        changed = aligned != base_labels
        # Escalate cluster-strategy stores when the actionable segment changes.
        action = np.where(changed & (base_action == "Cluster strategy"), "Managerial review", base_action)
        results.append(dict(iqr_shift=shift, **metrics,
                            centroid_displacement=centroid_displacement(benchmark.cluster_centers_, centers, mapping),
                            change_from_base=changed.mean(), decision_change_rate=(action != base_action).mean()))
        store_shifts.append(pd.DataFrame(dict(store_id=complete.index, iqr_shift=shift, cluster=aligned,
                                              changed_from_base=changed, decision=action)))
    return {"store_stability": stores, "pair_stability": pairs, "sensitivity": pd.DataFrame(results),
            "sensitivity_stores": pd.concat(store_shifts, ignore_index=True),
            "stability_associations": pd.DataFrame([
                dict(variable="boundary_margin", spearman_rho=spearmanr(margin, stability).statistic),
                dict(variable="mean_masked_features", spearman_rho=spearmanr(missing, stability).statistic),
            ])}


def sample_pairs(n, seed):
    rng = np.random.default_rng(seed)
    left = rng.integers(0, n, 30_000)
    right = rng.integers(0, n, 30_000)
    pairs = np.unique(np.sort(np.column_stack([left[left != right], right[left != right]]), axis=1), axis=0)
    return pairs.T
