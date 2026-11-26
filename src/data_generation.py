"""Generate overlapping synthetic retail profiles and genuine assortment zeros."""
import numpy as np
import pandas as pd
from scipy.special import expit

PRODUCTS = ["beverages", "snacks", "ready_to_eat", "household", "personal_care"]
PROFILES = ["Urban commuter", "Residential", "University-area", "Suburban family"]


def generate(n, seed):
    rng = np.random.default_rng(seed)
    profile = rng.choice(4, n, p=[.26, .29, .20, .25])
    volume = rng.normal(0, .40, n) + np.array([.25, -.14, .08, .05])[profile]
    basket = rng.normal(0, .24, n) + np.array([-.05, .08, -.16, .16])[profile]
    traffic = np.rint(4300 * np.exp(volume))
    transaction = 12 * np.exp(basket)
    total = traffic * transaction
    weekend = expit(np.array([-.95, -.40, -.70, -.20])[profile] + rng.normal(0, .42, n))
    evening = expit(np.array([-.85, -.63, -.33, -.70])[profile] + rng.normal(0, .44, n))
    shifts = np.array([[.32, -.06, .38, -.33, -.12], [-.10, -.05, -.11, .35, .17],
                       [.24, .30, .12, -.35, -.06], [-.11, .15, -.18, .29, .18]])
    weights = np.exp(np.log([.22, .16, .17, .10, .07]) + shifts[profile]
                     + rng.normal(0, .45, (n, 5)))
    absent = rng.random((n, 5)) < expit(np.array([-4, -3.6, -2.1, -1.65, -1.8])
                                       - shifts[profile] - .65 * volume[:, None])
    weights[absent] = 0
    sales = total[:, None] * weights / (.40 + weights.sum(axis=1, keepdims=True))
    features = pd.DataFrame(sales, columns=PRODUCTS).assign(
        total_sales=total, transaction_value=transaction, traffic=traffic,
        weekend_share=weekend, evening_share=evening)
    features.index.name = "store_id"
    labels = pd.Series(np.array(PROFILES)[profile], index=features.index, name="profile")
    return features, labels
