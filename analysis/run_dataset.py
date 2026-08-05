"""Generate, feature-extract and validate a deterministic multi-seed dataset."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from pathlib import Path


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["seed", "status", "runtime_sec", "run_dir", "error"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-count", type=int, required=True)
    parser.add_argument("--num-qubits", type=int, default=15)
    parser.add_argument("--layers", type=int, default=10)
    parser.add_argument("--root", type=int, default=7)
    parser.add_argument("--edge-tolerance", type=float, default=1e-10)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.seed_count < 1:
        raise ValueError("seed-count must be positive")

    repo = Path(__file__).resolve().parents[1]
    generator = repo / "src" / "rqc_sonification.py"
    extractor = repo / "analysis" / "extract_stft_features.py"
    validator = repo / "scripts" / "validate_run.py"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "dataset_manifest.csv"
    manifest: list[dict[str, object]] = []

    for seed in range(args.seed_start, args.seed_start + args.seed_count):
        started = time.perf_counter()
        run_dir = output / f"seed_{seed:06d}"
        row: dict[str, object] = {
            "seed": seed,
            "status": "failed",
            "runtime_sec": 0.0,
            "run_dir": str(run_dir),
            "error": "",
        }
        try:
            command = [
                sys.executable,
                str(generator),
                "--num-qubits", str(args.num_qubits),
                "--layers", str(args.layers),
                "--seed", str(seed),
                "--root", str(args.root),
                "--edge-tolerance", str(args.edge_tolerance),
                "--output-dir", str(output),
                "--save-statevectors",
            ]
            if args.overwrite:
                command.append("--overwrite")
            run_command(command)

            run_command([
                sys.executable,
                str(extractor),
                str(run_dir),
                "--output", str(run_dir / "audio_features.csv"),
            ])
            run_command([
                sys.executable,
                str(validator),
                str(run_dir),
                "--num-qubits", str(args.num_qubits),
                "--layers", str(args.layers),
                "--root", str(args.root),
                "--edge-tolerance", str(args.edge_tolerance),
                "--require-statevectors",
            ])
            row["status"] = "passed"
        except Exception as exc:
            row["error"] = repr(exc)
            raise
        finally:
            row["runtime_sec"] = round(time.perf_counter() - started, 6)
            manifest.append(row)
            write_manifest(manifest_path, manifest)

    print(f"DATASET GENERATION PASSED: {len(manifest)} seeds")


if __name__ == "__main__":
    main()
