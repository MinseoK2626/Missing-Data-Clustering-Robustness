"""Run the synthetic retail study from a YAML configuration."""
import argparse
import gzip
import json
from pathlib import Path
import platform
from importlib.metadata import version

import yaml
from threadpoolctl import threadpool_limits

from src.experiments import run
from src.visualization import render


def validate_config(config):
    seeds = config["seeds"]
    if len(seeds) < 2 or len(set(seeds)) != len(seeds):
        raise ValueError("Use at least two distinct simulation seeds")
    rates = config["rates"]
    if not all(0 < rate < 1 for rate in rates) or config["sample_rate"] not in rates:
        raise ValueError("Masking rates must lie in (0, 1) and include sample_rate")
    for key, required in [("mechanisms", {"MCAR", "MAR", "MNAR"}),
                          ("methods", {"zero", "median", "knn", "iterative"})]:
        if set(config[key]) != required or len(config[key]) != len(required):
            raise ValueError(f"{key} must contain each of {', '.join(sorted(required))}")
    if min(config["stores"], config["evaluation_stores"], config["silhouette_limit"],
           *config["sample_sizes"]) < 30:
        raise ValueError("Use at least 30 stores per cohort and in the silhouette sample")
    if config["stability_repeats"] < 1:
        raise ValueError("Use at least one stability repeat")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--output", type=Path, help="Override the configured output directory")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    validate_config(config)
    output = args.output or Path(config["output"])
    tables_directory = output / "tables"
    tables_directory.mkdir(parents=True, exist_ok=True)
    with threadpool_limits(limits=1):
        tables, example = run(config)
    for name, table in tables.items():
        table.to_csv(tables_directory / f"{name}.csv", index=False, float_format="%.10g")
    data_directory = output / "data"
    data_directory.mkdir(exist_ok=True)
    for name in ("complete", "profiles", "observed", "mask"):
        with gzip.GzipFile(data_directory / f"{name}.csv.gz", "wb", mtime=0) as stream:
            stream.write(example[name].to_csv(float_format="%.12g").encode())
    manifest = dict(python=platform.python_version(), config=config,
                    versions={name: version(name) for name in
                              ("numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "PyYAML")})
    render(output / "figures", tables, example, config)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Artifacts written to {output}")


if __name__ == "__main__":
    main()
