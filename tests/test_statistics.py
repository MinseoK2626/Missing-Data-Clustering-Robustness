import numpy as np
import pandas as pd
import pytest

from src.statistics import distribution, summarize_factorial, validate


def test_distribution_reproducibility_and_constant_interval():
    assert distribution([.42] * 5)["low"] == pytest.approx(.42)
    assert distribution([.10, .55, .87]) == distribution([.10, .55, .87])
    assert distribution([1, 2, 3, 4])["iqr"] == 1.5
    assert distribution([])["mean"] is None


def test_paired_bootstrap_uses_within_seed_difference():
    config = dict(seeds=[1, 2, 3], mechanisms=["MCAR"], rates=[.05], methods=["zero", "median"])
    rows = []
    for seed, value in enumerate([.1, .5, .6], 1):
        for index, method in enumerate(config["methods"]):
            rows.append(dict(seed=seed, mechanism="MCAR", target_rate=.05, method=method,
                             ari=value + .2 * index, silhouette=.1, change_rate=.2,
                             realized_product_rate=.05, realized_overall_rate=.025,
                             centroid_displacement=.1, rmse=1000))
    raw = pd.DataFrame(rows)
    ledger = raw[["seed", "mechanism", "target_rate", "method"]].assign(status="success")
    benchmark = pd.DataFrame({"seed": config["seeds"]})
    assert validate(raw, ledger, benchmark, config) == 6
    _, comparisons, ranking = summarize_factorial(raw, ledger, config)
    comparison = comparisons[0]
    assert comparison["n"] == 3
    np.testing.assert_allclose([comparison["low"], comparison["high"]], [-.2, -.2])
    assert [row["win_share"] for row in ranking] == [0, 1]
    wrong_mask = raw.copy()
    wrong_mask.loc[0, "realized_product_rate"] = .3
    with pytest.raises(ValueError, match="realized missingness"):
        validate(wrong_mask, ledger, benchmark, config)
    with pytest.raises(ValueError, match="Duplicate"):
        validate(pd.concat([raw, raw]), ledger, benchmark, config)


def test_mean_interval_matches_seed_resampling():
    from src.statistics import BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED

    outcomes = [0.3, 0.45, 0.7, 0.91, 0.99]
    generator = np.random.default_rng(BOOTSTRAP_SEED)
    indices = generator.integers(len(outcomes), size=(BOOTSTRAP_REPLICATES, len(outcomes)))
    estimates = [sum(outcomes[index] for index in resample) / len(resample) for resample in indices]
    summary = distribution(outcomes)
    np.testing.assert_allclose([summary["low"], summary["high"]],
                               np.percentile(estimates, [2.5, 97.5]))
