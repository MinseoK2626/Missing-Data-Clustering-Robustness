"""Assemble the static publication from validated CSVs and generated demonstrations."""
import argparse
import json
from pathlib import Path
import shutil

import pandas as pd
from threadpoolctl import threadpool_limits

from scripts.analyze_expanded import json_file, publish
from src.clustering import fit_kmeans
from src.data_generation import generate
from src.evaluation import align
from src.imputation import METHODS, impute
from src.missingness import apply_missingness
from src.statistics import distribution


def records(table):
    return json.loads(table.to_json(orient="records", double_precision=12))


def store_details(frame, labels, mechanism, rate, ids, seed):
    observed, mask = apply_missingness(frame, mechanism, rate, seed + 1000)
    values, assignments = {}, {}
    for method in METHODS:
        imputed, _ = impute(observed, method, seed)
        _, fitted = fit_kmeans(imputed, seed)
        values[method] = imputed.loc[ids].to_numpy().round(2).tolist()
        assignments[method] = align(labels, fitted.labels_)[0][ids].tolist()
    return dict(mask=mask.loc[ids].to_numpy().tolist(), observed=observed.loc[ids].to_numpy().tolist(),
                values=values, assignments=assignments)


def build_demonstrations(destination):
    seed = 11
    example, _ = generate(120, seed)
    _, reference = fit_kmeans(example, seed)
    ids = list(range(8))
    cases = {}
    for mechanism in ("MCAR", "MAR", "MNAR"):
        for rate in (.05, .10, .20, .30, .40):
            details = store_details(example, reference.labels_, mechanism, rate, ids, seed)
            details["observed"] = [[None if pd.isna(value) else round(value, 2) for value in row]
                                   for row in details["observed"]]
            cases[f"{mechanism}/{round(rate * 100)}"] = details
    json_file(destination / "demo.json",
              dict(stores=len(example), ids=ids, columns=example.columns.tolist(),
                   complete=example.loc[ids].to_numpy().round(2).tolist(),
                   reference=reference.labels_[ids].tolist(), cases=cases))


def build_uncertainty(destination):
    preserved = Path("results/tables")
    stores = pd.read_csv(preserved / "store_stability.csv")
    stores["discordant"] = (stores.gmm_max_posterior >= .80) & (stores.stability < .60)
    details_ids = list(dict.fromkeys([*stores[stores.discordant].head(16).store_id,
                                     *stores.sort_values("boundary_margin").head(12).store_id,
                                     *stores.sort_values("stability", ascending=False).head(12).store_id]))
    frame, _ = generate(len(stores), 11)
    scaler, model = fit_kmeans(frame, 11)
    if (model.predict(scaler.transform(frame)) != stores.benchmark.to_numpy()).any():
        raise ValueError("Regenerated reference labels differ from the original uncertainty cohort")
    result = store_details(frame, model.labels_, "MNAR", .30, details_ids, 11)
    result.pop("observed")
    result.update(ids=details_ids, columns=frame.columns.tolist(),
                  complete=frame.loc[details_ids].to_numpy().round(2).tolist())
    columns = ["store_id", "profile", "benchmark", "stability", "gmm_max_posterior",
               "change_frequency", "discordant"]
    json_file(destination / "uncertainty.json",
              dict(stores=records(stores[columns]), detail=result,
                   discordant=int(stores.discordant.sum()),
                   sensitivity=records(pd.read_csv(preserved / "sensitivity.csv"))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("_site"))
    parser.add_argument("--original", action="store_true", help="Build against the preserved 480-run study")
    args = parser.parse_args()
    original = Path("results")
    expanded = original / "expanded"
    source = original / "tables" if args.original else expanded
    manifest = original / "manifest.json" if args.original else expanded / "manifest.json"
    facts, raw = publish(source, json.loads(manifest.read_text()), args.original)
    output = args.output
    shutil.copytree("site", output, dirs_exist_ok=True)
    data = output / "data"
    data.mkdir(exist_ok=True)
    columns = ["seed", "mechanism", "target_rate", "method", "ari", "silhouette", "silhouette_delta",
               "change_rate", "realized_product_rate", "realized_overall_rate", "centroid_displacement", "rmse"]
    facts["sample"] = []
    for (mechanism, method, stores), group in pd.read_csv(original / "tables/sample_size.csv").groupby(
            ["mechanism", "method", "stores"]):
        facts["sample"].append(dict(mechanism=mechanism, method=method, stores=int(stores),
                                    **distribution(group.ari), seeds=records(group[["seed", "ari"]])))
    facts["sample_runs"] = sum(row["n"] for row in facts["sample"])
    facts["pdf"] = not args.original and Path("reports/expanded_report.pdf").is_file()
    json_file(data / "study.json", facts)
    json_file(data / "runs.json", records(raw[columns]))
    with threadpool_limits(limits=1):
        build_demonstrations(data)
        build_uncertainty(data)
    for name in ("figures", "tables"):
        shutil.copytree(original / name, output / "results" / name, dirs_exist_ok=True)
    if not args.original:
        shutil.copytree(expanded, output / "results/expanded", dirs_exist_ok=True)
        pdf = Path("reports/expanded_report.pdf")
        if pdf.is_file():
            shutil.copyfile(pdf, output / "research-report.pdf")
    print(f"Built {facts['version']} site with {facts['design']['completed']} usable runs at {output}")


if __name__ == "__main__":
    main()
