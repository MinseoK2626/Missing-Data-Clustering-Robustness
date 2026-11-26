"""Internal fit, benchmark agreement and masked-cell reconstruction error."""
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from sklearn.metrics import (adjusted_rand_score, davies_bouldin_score,
                             normalized_mutual_info_score, silhouette_score)


def align(reference, candidate, k=4):
    counts = np.zeros((k, k), dtype=int)
    np.add.at(counts, (reference, candidate), 1)
    rows, columns = linear_sum_assignment(counts, maximize=True)
    mapping = np.empty(k, dtype=int)
    mapping[columns] = rows
    return mapping[candidate], mapping


def internal(values, labels, limit, seed):
    indices = np.random.default_rng(seed).permutation(len(labels))
    subset = indices[:limit]
    return {
        "silhouette": silhouette_score(values[subset], labels[subset]),
        "davies_bouldin": davies_bouldin_score(values, labels),
    }


def agreement(reference, labels, profiles):
    aligned, mapping = align(reference, labels)
    return {
        "ari": adjusted_rand_score(reference, labels),
        "nmi": normalized_mutual_info_score(reference, labels),
        "latent_ari": adjusted_rand_score(profiles, labels),
        "change_rate": np.mean(aligned != reference),
    }, aligned, mapping


def centroid_displacement(ref_centers, centers, mapping):
    return cdist(ref_centers, centers)[mapping, np.arange(len(mapping))].mean()


def reconstruction(complete, imputed, mask):
    error = (imputed - complete).where(mask)
    values = error.to_numpy()[mask.to_numpy()]
    return {"mae": np.abs(values).mean(), "rmse": np.sqrt(np.square(values).mean())}, error.mean()


def boundary_margin(values, centers):
    distances = np.sort(cdist(values, centers), axis=1)
    return (distances[:, 1] - distances[:, 0]) / np.maximum(distances[:, 1], 1e-12)
