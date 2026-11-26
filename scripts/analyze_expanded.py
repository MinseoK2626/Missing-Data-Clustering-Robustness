"""Validate seed-level artifacts and write publication statistics."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.statistics import KEYS, distribution, interactions, summarize_factorial, validate


def json_file(path, data):
    path.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")) + "\n")


def analysis(raw, ledger, benchmark, config):
    planned = validate(raw, ledger, benchmark, config)
    summary, paired, ranking = summarize_factorial(raw, ledger, config)
    compared = raw.merge(benchmark[["seed", "silhouette"]], on="seed",
                         suffixes=("", "_reference"), validate="many_to_one")
    compared["silhouette_delta"] = compared.silhouette - compared.silhouette_reference
    improved = compared[compared.silhouette_delta > 0]
    substantial = improved[improved.change_rate >= .10]
    lower_ari = improved[improved.ari < .50]
    example = improved.sort_values(["ari", "seed"]).iloc[0].to_dict() if len(improved) else None
    return {
        "design": dict(planned=planned, completed=len(raw), seeds=int(raw.seed.nunique()),
                       seed_target=len(config["seeds"]), configurations=len(summary),
                       failures=int(ledger.status.eq("failed").sum()),
                       warnings=int(ledger.status.eq("convergence_warning").sum()),
                       unattempted=planned-len(ledger)),
        "validation": dict(improved=len(improved), changed_ten_percent=len(substantial),
                           ari_below_half=len(lower_ari), example=example,
                           spearman=float(spearmanr(compared.silhouette, compared.ari).statistic)),
        "summary": summary, "paired": paired, "ranking": ranking, "interactions": interactions(raw),
    }, compared


def publish(directory, manifest, original):
    config = manifest["config"]
    raw = pd.read_csv(directory / "factorial.csv")
    benchmark = pd.read_csv(directory / "benchmarks.csv")
    if original:
        ledger = raw[["seed", *KEYS]].assign(status="success")
    else:
        ledger = pd.read_csv(directory / "diagnostics.csv")
    result, compared = analysis(raw, ledger, benchmark, config)
    result["version"] = "Original (8-seed factorial)" if original else "Expanded factorial"
    if original:
        result["design"]["warnings"] = None  # No run-level warning ledger was retained.
    return result, compared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/expanded"))
    args = parser.parse_args()
    directory = args.input
    result, compared = publish(directory, json.loads((directory / "manifest.json").read_text()), False)
    json_file(directory / "summary.json", result)
    compared.to_csv(directory / "validation.csv", index=False, float_format="%.12g")
    for name in ("paired", "ranking", "interactions"):
        pd.DataFrame(result[name]).to_csv(directory / f"{name}.csv", index=False, float_format="%.12g")
    flat = pd.json_normalize(result["summary"], sep="_")
    flat.to_csv(directory / "factorial_summary.csv", index=False, float_format="%.12g")
    print(json.dumps(result["design"], indent=2))


if __name__ == "__main__":
    main()
