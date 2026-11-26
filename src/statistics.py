"""Descriptive summaries and percentile bootstrap intervals for seed-level estimates."""
from itertools import combinations, product

import numpy as np
import pandas as pd

KEYS = ["mechanism", "target_rate", "method"]
METRICS = ["ari", "silhouette", "change_rate", "realized_product_rate",
           "realized_overall_rate", "centroid_displacement", "rmse"]
BOOTSTRAP_REPLICATES = 4000
BOOTSTRAP_SEED = 41027


def distribution(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    n = len(values)
    if not n:
        return dict(n=0, mean=None, median=None, sd=None, q05=None, q25=None,
                    q75=None, q95=None, iqr=None, low=None, high=None)
    q05, q25, median, q75, q95 = np.quantile(values, [.05, .25, .50, .75, .95])
    low, high = None, None
    if n > 1:
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        means = values[rng.integers(n, size=(BOOTSTRAP_REPLICATES, n))].mean(axis=1)
        low, high = np.quantile(means, [.025, .975])
    return dict(n=n, mean=values.mean(), median=median, sd=values.std(ddof=1) if n > 1 else None,
                q05=q05, q25=q25, q75=q75, q95=q95, iqr=q75-q25, low=low, high=high)


def validate(raw, ledger, benchmarks, config):
    identity = ["seed", *KEYS]
    expected = set(product(config["seeds"], config["mechanisms"], config["rates"], config["methods"]))
    def identities(frame):
        if frame[identity].duplicated().any():
            raise ValueError("Duplicate experiment identities")
        return set(frame[identity].itertuples(index=False, name=None))

    completed = identities(raw)
    attempted = identities(ledger)
    valid_status = {"success", "convergence_warning", "failed"}
    if not attempted <= expected or not set(ledger.status) <= valid_status:
        raise ValueError("Unexpected run in the diagnostic ledger")
    if completed != identities(ledger[ledger.status != "failed"]):
        raise ValueError("Usable runs disagree with the diagnostic ledger")
    if benchmarks.seed.duplicated().any() or set(benchmarks.seed) != set(ledger.seed):
        raise ValueError("Each attempted seed must have exactly one reference")
    paired = raw.groupby(["seed", "mechanism", "target_rate"])
    if paired[["realized_product_rate", "realized_overall_rate"]].nunique().gt(1).any().any():
        raise ValueError("Methods disagree on realized missingness within a paired split")
    if "mask_digest" in ledger and ledger.groupby(identity[:-1]).mask_digest.nunique().gt(1).any():
        raise ValueError("Methods do not share a mask")
    if not np.isfinite(raw[METRICS].to_numpy()).all():
        raise ValueError("Nonfinite metrics in successful runs")
    return len(expected)


def summarize_factorial(raw, ledger, config):
    rows, paired_rows, ranking = [], [], []
    for mechanism, rate in product(config["mechanisms"], config["rates"]):
        group = raw[(raw.mechanism == mechanism) & (raw.target_rate == rate)]
        cell = ledger[(ledger.mechanism == mechanism) & (ledger.target_rate == rate)]
        for method in config["methods"]:
            values = group[group.method == method].sort_values("seed")
            statuses = cell.loc[cell.method == method, "status"]
            mode = dict(mechanism=mechanism, target_rate=rate, method=method)
            rows.append(dict(mode, completed=len(values), failed=int(statuses.eq("failed").sum()),
                             warnings=int(statuses.eq("convergence_warning").sum()),
                             planned=len(config["seeds"]),
                             metrics={metric: distribution(values[metric]) for metric in METRICS}))
        wide = group.pivot(index="seed", columns="method", values="ari").reindex(columns=config["methods"])
        complete = wide.dropna()
        winners = complete.eq(complete.max(axis=1), axis=0)
        weights = winners.div(winners.sum(axis=1), axis=0)
        ranking.extend(dict(mechanism=mechanism, target_rate=rate, method=method,
                            n=len(complete), win_share=weights[method].mean() if len(complete) else None)
                       for method in config["methods"])
        for left, right in combinations(config["methods"], 2):
            paired_rows.append(dict(mechanism=mechanism, target_rate=rate, left=left, right=right,
                                    **distribution(wide[left] - wide[right])))
    return rows, paired_rows, ranking


def interactions(raw):
    """Matched differences-in-differences on the ARI scale."""
    wide = raw.pivot(index="seed", columns=KEYS, values="ari")
    results = []
    for mechanism in ("MAR", "MNAR"):
        for method in ("median", "knn", "iterative"):
            for rate in (.05, .10, .20, .30, .40):
                contrast = [(mechanism, rate, method), (mechanism, rate, "zero"),
                            ("MCAR", rate, method), ("MCAR", rate, "zero")]
                results.append(("mechanism × method", contrast))
    for mechanism in ("MCAR", "MAR", "MNAR"):
        for method in ("median", "knn", "iterative"):
            results.append(("severity × method", [(mechanism, .40, method), (mechanism, .40, "zero"),
                                                  (mechanism, .05, method), (mechanism, .05, "zero")]))
    for mechanism in ("MAR", "MNAR"):
        for method in ("zero", "median", "knn", "iterative"):
            results.append(("mechanism × severity", [(mechanism, .40, method), (mechanism, .05, method),
                                                     ("MCAR", .40, method), ("MCAR", .05, method)]))
    return [dict(interaction=name, contrast=str(keys),
                 **distribution(wide.reindex(columns=keys).to_numpy() @ np.array([1, -1, -1, 1])))
            for name, keys in results]
