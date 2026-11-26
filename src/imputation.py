"""Fit preprocessing using observed training data only."""
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler

from .data_generation import PRODUCTS

METHODS = ("zero", "median", "knn", "iterative")


def impute(train, method, seed, test=None):
    if method not in METHODS:
        raise ValueError(f"Unknown imputation method {method}")
    if method in ("zero", "median"):
        estimator = (SimpleImputer(strategy="constant", fill_value=0)
                     if method == "zero" else SimpleImputer(strategy="median"))
        scaler = None
        fitted = train
    else:
        scaler = StandardScaler().fit(train)
        fitted = scaler.transform(train)
        estimator = (KNNImputer(n_neighbors=5, weights="distance")
                     if method == "knn" else
                     IterativeImputer(random_state=seed, max_iter=15, tol=.01))
    if train.isna().all().any():
        raise ValueError("Every feature needs at least one observed training value")
    estimator.fit(fitted)

    def transform(frame):
        values = estimator.transform(frame if scaler is None else scaler.transform(frame))
        if scaler is not None:
            values = scaler.inverse_transform(values)
        result = pd.DataFrame(values, index=frame.index, columns=frame.columns)
        result[PRODUCTS] = result[PRODUCTS].clip(lower=0)
        return frame.fillna(result)

    return transform(train), None if test is None else transform(test)
