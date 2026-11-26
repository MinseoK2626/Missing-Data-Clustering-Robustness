"""Mask product columns while retaining fully observed covariates."""
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.special import expit

from .data_generation import PRODUCTS


def standardize(values):
    return (values - values.mean(axis=0)) / np.maximum(values.std(axis=0), 1e-12)


def apply_missingness(complete, mechanism, rate, seed):
    if not 0 < rate < 1:
        raise ValueError("Masking rate must be between zero and one")
    products = complete[PRODUCTS].to_numpy()
    if mechanism == "MCAR":
        probability = rate
    else:
        if mechanism == "MAR":
            traffic = standardize(np.log1p(complete["traffic"].to_numpy()))
            evening = standardize(complete["evening_share"].to_numpy())
            score = (-traffic + .55 * evening)[:, None] + np.linspace(-.35, .35, len(PRODUCTS))
        elif mechanism == "MNAR":
            score = -1.25 * standardize(np.log1p(products))
        else:
            raise ValueError(f"Unknown mechanism {mechanism}")
        intercept = brentq(lambda b: expit(score + b).mean() - rate, -100, 100)
        probability = expit(score + intercept)
    mask = pd.DataFrame(False, index=complete.index, columns=complete.columns)
    mask[PRODUCTS] = np.random.default_rng(seed).random(products.shape) < probability
    return complete.mask(mask), mask
