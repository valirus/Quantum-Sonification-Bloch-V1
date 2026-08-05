"""Aggregate per-seed CSV outputs into analysis-ready dataset tables."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


TABLES = (
    "layer_metrics.csv",
    "bloch_descriptors.csv",
    "circuit_metrics.csv",
    "gate_manifest.csv",
    "audio_features.csv",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write for {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    seeds = sorted(path for path in args.dataset_dir.glob("seed_*") if path.is_dir())
    if not seeds:
        raise FileNotFoundError(f"No seed directories under {args.dataset_dir}")

    for table in TABLES:
        rows: list[dict[str, str]] = []
        for seed_dir in seeds:
            path = seed_dir / table
            if not path.is_file():
                raise FileNotFoundError(path)
            seed_rows = read_rows(path)
            if table == "gate_manifest.csv":
                seed_value = int(seed_dir.name.split("_")[-1])
                for row in seed_rows:
                    row = {"seed": str(seed_value), **row}
                    rows.append(row)
            else:
                rows.extend(seed_rows)
        write_rows(args.output_dir / table, rows)
        print(f"Wrote {len(rows)} rows: {args.output_dir / table}")


if __name__ == "__main__":
    main()
