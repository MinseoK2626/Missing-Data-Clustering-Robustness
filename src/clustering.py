"""Reproducible clustering with a common estimator recipe."""
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def fit_kmeans(frame, seed, k=4):
    scaler = StandardScaler().fit(frame)
    model = KMeans(n_clusters=k, n_init=12, random_state=seed).fit(scaler.transform(frame))
    return scaler, model
