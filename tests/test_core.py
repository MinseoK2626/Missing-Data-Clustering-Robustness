import numpy as np
import pandas as pd
import pytest

from src.data_generation import PRODUCTS, generate
from src.evaluation import agreement, reconstruction
from src.imputation import METHODS, impute
from src.missingness import apply_missingness


@pytest.mark.parametrize("mechanism", ["MCAR", "MAR", "MNAR"])
def test_masks(mechanism):
    data, _ = generate(10000, 14)
    observed, mask = apply_missingness(data, mechanism, .30, 25)
    pd.testing.assert_frame_equal(observed.isna(), mask)
    pd.testing.assert_frame_equal(mask, apply_missingness(data, mechanism, .30, 25)[1])
    assert abs(mask[PRODUCTS].to_numpy().mean() - .30) < .015
    assert not mask.drop(columns=PRODUCTS).to_numpy().any()
    assert ((data[PRODUCTS] == 0) & ~mask[PRODUCTS]).to_numpy().any()
    rate = mask["beverages"].groupby(pd.qcut(data["traffic"], 5, labels=False)).mean()
    if mechanism == "MAR":
        assert rate.iloc[0] > rate.iloc[-1] + .2
    if mechanism == "MNAR":
        assert mask.loc[data["beverages"] == 0, "beverages"].mean() > .60


@pytest.mark.parametrize("method", METHODS)
def test_imputation(method):
    data, _ = generate(400, 7)
    observed, mask = apply_missingness(data, "MAR", .3, 9)
    result, heldout = impute(observed, method, 9, observed.iloc[:30])
    pd.testing.assert_frame_equal(result.where(~mask), observed)
    pd.testing.assert_frame_equal(result.iloc[:30], heldout)
    assert not result.isna().to_numpy().any()
    if method == "zero":
        assert (result.to_numpy()[mask.to_numpy()] == 0).all()
    if method == "median":
        for feature in PRODUCTS:
            assert result.loc[mask[feature], feature].eq(observed[feature].median()).all()
    np.testing.assert_allclose(reconstruction(data, result, mask)[0]["mae"],
                               np.abs(result.to_numpy() - data.to_numpy())[mask].mean())


def test_label_alignment():
    labels = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    candidate = np.array([3, 0, 1, 2])[labels]
    scores, aligned, _ = agreement(labels, candidate, labels)
    np.testing.assert_array_equal(labels, aligned)
    assert scores["ari"] == 1
    assert scores["change_rate"] == 0


def test_heldout_data_does_not_change_fitted_imputation():
    train, _ = generate(400, 7)
    observed, _ = apply_missingness(train, "MCAR", .3, 9)
    heldout = observed.iloc[:100] * 1000
    for method in METHODS:
        expected, _ = impute(observed, method, 5)
        actual, _ = impute(observed, method, 5, heldout)
        pd.testing.assert_frame_equal(expected, actual)


def test_reported_centroid_distance_is_label_invariant():
    from src.evaluation import centroid_displacement

    centers = np.arange(12).reshape(4, 3)
    mapping = np.array([2, 3, 0, 1])
    assert centroid_displacement(centers, centers[mapping], mapping) == 0
    np.testing.assert_allclose(centroid_displacement(centers, centers[mapping] + 1, mapping),
                               np.sqrt(3))


def test_uncertainty_summary_and_decisions():
    from src.sensitivity import decision, entropy

    posterior = np.array([[1, 0, 0, 0], [.25, .25, .25, .25], [.70, .10, .10, .10]])
    np.testing.assert_allclose(entropy(posterior)[:2], [0, 1])
    assert decision(np.array([.8, .95, .79]), posterior.max(axis=1)).tolist() == [
        "Cluster strategy", "Collect more data", "Managerial review"]
