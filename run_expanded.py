"""Run the expanded factorial study with atomic, seed-level checkpoints."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from importlib.metadata import version
import json
from pathlib import Path
import platform
import time

import pandas as pd
from threadpoolctl import threadpool_limits
import yaml

from src.experiments import run_factorial


TABLES = ("factorial", "missingness", "imputation_bias", "benchmarks", "diagnostics")


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, allow_nan=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def run_seed(config, seed, path):
    with threadpool_limits(limits=1):
        tables, _ = run_factorial(dict(config, seeds=[seed]), primary_only=True)
    write_json(path, {name: json.loads(tables[name].to_json(orient="records", double_precision=15))
                      for name in TABLES})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/expanded.yaml"))
    parser.add_argument("--output", type=Path, default=Path("results/expanded"))
    parser.add_argument("--checkpoints", type=Path, default=Path(".checkpoints/expanded"))
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--collect-only", action="store_true",
                        help="Combine existing checkpoints without running missing seeds")
    args = parser.parse_args()
    start = time.monotonic()
    config = yaml.safe_load(args.config.read_text())
    for key in ("seeds", "rates", "methods", "mechanisms"):
        if not config[key] or len(set(config[key])) != len(config[key]):
            parser.error(f"{key} must be a nonempty list of unique values")
    signature = dict(config=config, python=platform.python_version(),
                     versions={name: version(name) for name in
                               ("numpy", "pandas", "scipy", "scikit-learn", "threadpoolctl")})
    args.checkpoints.mkdir(parents=True, exist_ok=True)
    metadata = args.checkpoints / "design.json"
    if args.collect_only and not metadata.is_file():
        parser.error("There are no checkpoints to collect")
    if metadata.exists() and json.loads(metadata.read_text()) != signature:
        parser.error("Checkpoint configuration or numerical environment differs. Use a fresh directory.")
    write_json(metadata, signature)
    paths = {seed: args.checkpoints / f"seed-{seed}.json" for seed in config["seeds"]}
    pending = [(seed, path) for seed, path in paths.items() if not path.exists()]
    worker_errors = []
    if not args.collect_only and pending:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            tasks = {pool.submit(run_seed, config, seed, path): seed for seed, path in pending}
            for task in as_completed(tasks):
                try:
                    task.result()
                except Exception as error:
                    worker_errors.append(dict(seed=tasks[task], message=f"{type(error).__name__}: {error}"))
                    print(worker_errors[-1], flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    inputs = [json.loads(path.read_text()) for path in paths.values() if path.exists()]
    if not inputs:
        raise SystemExit("No completed seed checkpoints to aggregate")
    for name in TABLES:
        table = pd.DataFrame(row for checkpoint in inputs for row in checkpoint[name])
        table.to_csv(args.output / f"{name}.csv", index=False, float_format="%.12g")
    write_json(args.output / "manifest.json",
               dict(signature, seed_checkpoints=len(inputs), workers=args.jobs,
                    invocation_seconds=round(time.monotonic() - start, 1), worker_errors=worker_errors))
    if worker_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
