"""Render the paper's figures in deterministic, noninteractive formats."""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

from .data_generation import PRODUCTS

NAVY = "#24294b"
LAVENDER = "#a497cf"
COLORS = [NAVY, "#65558f", LAVENDER, "#777886"]
MARKERS = ["o", "s", "^", "D"]


def render(directory, tables, example, config):
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "text.color": NAVY, "axes.labelcolor": NAVY,
                         "axes.titlecolor": NAVY, "svg.hashsalt": "retail-study", "legend.frameon": False})

    def save(fig, name):
        fig.savefig(directory / f"{name}.png", dpi=300, facecolor="white")
        fig.savefig(directory / f"{name}.svg", metadata={"Date": None})
        plt.close(fig)

    def single(x, y):
        fig, ax = plt.subplots(figsize=(7.4, 4.4), layout="constrained")
        ax.set(xlabel=x, ylabel=y)
        ax.grid(axis="y", color="#e9e8ef")
        ax.set_axisbelow(True)
        return fig, ax

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), layout="constrained")
    for ax, feature in zip(axes, ["ready_to_eat", "household"]):
        full = np.log1p(example["complete"][feature])
        observed = np.log1p(example["observed"][feature].dropna())
        bins = np.linspace(0, full.max(), 30)
        ax.hist(full, bins=bins, density=True, color=LAVENDER, label="Complete")
        ax.hist(observed, bins=bins, density=True, histtype="step", color=NAVY, lw=1.6, label="Observed")
        ax.set(title=feature.replace("_", " ").title(), xlabel="log(1 + monthly sales)", ylabel="Density")
    axes[0].legend()
    fig.suptitle("Product sales before and after MNAR masking")
    save(fig, "01_distributions")

    fig, ax = plt.subplots(figsize=(7.4, 4.3), layout="constrained")
    image = ax.imshow(example["mask"][PRODUCTS].iloc[:100].T, aspect="auto",
                      cmap=ListedColormap(["#eeedf3", "#57467e"]), interpolation="nearest")
    ax.set(yticks=range(len(PRODUCTS)), yticklabels=[x.replace("_", " ") for x in PRODUCTS],
           xlabel="Store ID", title="MNAR mask for the first 100 stores")
    fig.colorbar(image, ax=ax, ticks=[0, 1]).ax.set_yticklabels(["Observed", "Masked"])
    save(fig, "02_missingness_heatmap")

    factorial = tables["factorial_summary"]
    selected = factorial[factorial.target_rate == config["sample_rate"]]
    mechanisms = config["mechanisms"]
    methods = config["methods"]
    for name, metric, label in [("03_imputation_error", "rmse", "Masked-cell RMSE"),
                                ("06_centroid_displacement", "centroid_displacement",
                                 "Mean centroid displacement (standardized units)")]:
        fig, ax = single("Missingness mechanism", label)
        x = np.arange(len(mechanisms))
        for i, method in enumerate(methods):
            data = selected[selected.method == method].set_index("mechanism").loc[mechanisms]
            ax.bar(x + (i - (len(methods) - 1) / 2) * .19, data[f"{metric}_mean"], width=.18,
                   yerr=data[f"{metric}_std"], capsize=2, color=COLORS[i], label=method)
        ax.set_xticks(x, mechanisms)
        ax.set_title(f"{config['sample_rate']:.0%} target product-cell masking · mean ± seed SD")
        ax.legend(ncols=2)
        save(fig, name)

    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(11.8, 3.9), layout="constrained")
    for ax, mechanism in zip(axes, mechanisms):
        for i, method in enumerate(methods):
            data = factorial[(factorial.mechanism == mechanism) & (factorial.method == method)]
            ax.errorbar(100 * data.target_rate, data.ari_mean, yerr=data.ari_std,
                        color=COLORS[i], marker=MARKERS[i], capsize=2, label=method)
        ax.set(title=mechanism, xlabel="Target product-cell masking (%)")
    axes[0].set_ylabel("ARI vs complete-data K-means")
    axes[-1].legend()
    save(fig, "04_ari_by_missingness")

    fig, axes = plt.subplots(1, 3, sharex=True, sharey=True, figsize=(11.8, 4), layout="constrained")
    raw = tables["factorial"]
    for ax, mechanism in zip(axes, mechanisms):
        for i, method in enumerate(methods):
            data = raw[(raw.mechanism == mechanism) & (raw.method == method)]
            ax.scatter(data.silhouette, data.ari, s=14 + 100 * data.target_rate, alpha=.65,
                       color=COLORS[i], marker=MARKERS[i], label=method)
        ax.axvline(tables["benchmarks"].silhouette.mean(), ls="--", color="#777886", lw=1)
        ax.set(title=mechanism, xlabel="Silhouette")
    axes[0].set_ylabel("ARI vs complete-data K-means")
    axes[-1].legend()
    fig.suptitle("Internal cluster separation and benchmark agreement")
    save(fig, "05_silhouette_vs_ari")

    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(11.8, 4), layout="constrained")
    sample = tables["sample_size_summary"]
    for ax, mechanism in zip(axes, mechanisms):
        data = sample[sample.mechanism == mechanism]
        for i, method in enumerate(("zero", "median")):
            group = data[data.method == method]
            ax.errorbar(group.stores, 1 - group.ari_mean, yerr=group.ari_std, label=method,
                        color=COLORS[i], marker=MARKERS[i], capsize=3)
        clean = data[data.method == "zero"]
        ax.plot(clean.stores, 1 - clean.clean_ari_mean, color=COLORS[3], marker=".",
                ls="--", label="complete training")
        ax.set(title=mechanism, xlabel="Training stores (log scale)", xscale="log")
    axes[0].set_ylabel("Distortion (1 − ARI)")
    axes[-1].legend()
    save(fig, "07_sample_size")

    fig, axes = plt.subplots(1, 2, sharex=True, sharey=True, figsize=(8.7, 4.2), layout="constrained")
    for ax, coordinates, labels, title in zip(
            axes, [example["original_pca"], example["imputed_pca"]],
            [example["reference"], example["aligned"]], ["Complete data", "MNAR with zero imputation"]):
        for k, color in enumerate(COLORS):
            points = coordinates[labels == k]
            ax.scatter(*points.T, c=color, alpha=.42, s=10, edgecolors="none", label=f"Cluster {k + 1}")
        ax.set(title=title, xlabel="Complete-data PC 1")
    axes[0].set_ylabel("Complete-data PC 2")
    axes[-1].legend(markerscale=1.5)
    save(fig, "08_pca_clusters")

    stores = tables["store_stability"]
    for name, column, x in [("09_store_stability", "stability", "Share assigned to the modal cluster"),
                            ("10_gmm_entropy", "gmm_entropy", "Normalized GMM membership entropy")]:
        fig, ax = single(x, "Stores")
        ax.hist(stores[column], bins=np.linspace(0, 1, 22), color=LAVENDER, edgecolor=NAVY, lw=.5)
        save(fig, name)

    fig, ax = single("Shift (observed positive-sales IQRs)", "Agreement or share of stores")
    sensitivity = tables["sensitivity"]
    for i, (column, label) in enumerate([("ari", "ARI vs complete data"),
                                         ("change_from_base", "Assignment changed"),
                                         ("decision_change_rate", "Decision changed")]):
        ax.plot(sensitivity.iqr_shift, sensitivity[column], marker=MARKERS[i], color=COLORS[i], label=label)
    ax.legend()
    save(fig, "11_mnar_sensitivity")

    fig, ax = single("Cross-scenario assignment stability", "Maximum GMM posterior")
    for i, action in enumerate(["Cluster strategy", "Managerial review", "Collect more data"]):
        group = stores[stores.decision == action]
        ax.scatter(group.stability, group.gmm_max_posterior, s=10, alpha=.5,
                   color=COLORS[i], marker=MARKERS[i], label=f"{action} ({len(group):,})")
    ax.set(xlim=(.2, 1.02), ylim=(.22, 1.02))
    ax.legend(loc="lower right")
    save(fig, "12_retail_decisions")
