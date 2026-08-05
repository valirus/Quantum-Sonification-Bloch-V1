"""Command-line entry point for the paper-ready Bloch + MI graph pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
from qiskit import qpy

from simulations import generate_bloch_graph_data
from sonification import (
    DEFAULT_CONFIG,
    concatenate_with_gaps,
    render_layer_audio,
    write_wav,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-qubits", type=int, default=15)
    parser.add_argument("--layers", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--root", type=int, default=None)
    parser.add_argument("--edge-tolerance", type=float, default=1e-10)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../outputs/paper_bloch_graph"),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete an existing seed directory before generating a fresh run.",
    )
    parser.add_argument(
        "--save-statevectors",
        action="store_true",
        help="Persist the complex statevector for every circuit layer.",
    )
    return parser.parse_args()


def _package_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not-installed"


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_layer_metrics(records, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["seed", "num_qubits", "layer", *records[0]["metrics"].keys()]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "seed": record["seed"],
                    "num_qubits": record["num_qubits"],
                    "layer": record["layer"],
                    **record["metrics"],
                }
            )


def write_bloch_descriptors(
    layer_data,
    seed: int,
    num_qubits: int,
    path: Path,
) -> None:
    fieldnames = [
        "seed",
        "num_qubits",
        "layer",
        "qubit",
        "x",
        "y",
        "z",
        "theta",
        "phi",
        "r",
        "linear_entropy",
        "von_neumann_entropy",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in layer_data:
            bloch = item["bloch"]
            for qubit in range(num_qubits):
                writer.writerow(
                    {
                        "seed": seed,
                        "num_qubits": num_qubits,
                        "layer": int(item["layer"]),
                        "qubit": qubit,
                        **{
                            key: float(bloch[key][qubit])
                            for key in fieldnames[4:]
                        },
                    }
                )


def write_circuit_metrics(
    layer_data,
    seed: int,
    num_qubits: int,
    path: Path,
) -> None:
    fieldnames = [
        "seed",
        "num_qubits",
        "layer",
        "circuit_depth",
        "circuit_size",
        "single_qubit_gate_count",
        "two_qubit_gate_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for item in layer_data:
            circuit = item["circuit"]
            single_count = sum(
                1 for instruction in circuit.data
                if instruction.operation.num_qubits == 1
            )
            two_count = sum(
                1 for instruction in circuit.data
                if instruction.operation.num_qubits == 2
            )
            writer.writerow(
                {
                    "seed": seed,
                    "num_qubits": num_qubits,
                    "layer": int(item["layer"]),
                    "circuit_depth": int(circuit.depth()),
                    "circuit_size": int(circuit.size()),
                    "single_qubit_gate_count": single_count,
                    "two_qubit_gate_count": two_count,
                }
            )


def _serialize_parameter(parameter) -> str:
    if isinstance(parameter, (str, int, float, complex, np.number)):
        return repr(parameter)
    array = np.asarray(parameter)
    if array.ndim == 0:
        return repr(array.item())
    return f"<array shape={array.shape} dtype={array.dtype}>"


def write_gate_manifest(layer_data, path: Path) -> None:
    """Record only the gates newly introduced at each RQC layer."""
    fieldnames = [
        "layer_added",
        "operation_index",
        "gate_name",
        "gate_label",
        "qubits",
        "parameters",
    ]
    previous_size = 0
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for item in layer_data:
            layer = int(item["layer"])
            circuit = item["circuit"]
            current_size = len(circuit.data)

            for operation_index in range(previous_size, current_size):
                instruction = circuit.data[operation_index]
                operation = instruction.operation
                qubits = ";".join(
                    str(circuit.find_bit(qubit).index)
                    for qubit in instruction.qubits
                )
                writer.writerow(
                    {
                        "layer_added": layer,
                        "operation_index": operation_index,
                        "gate_name": operation.name,
                        "gate_label": operation.label or "",
                        "qubits": qubits,
                        "parameters": ";".join(
                            _serialize_parameter(parameter)
                            for parameter in operation.params
                        ),
                    }
                )

            previous_size = current_size


def write_segments(boundaries, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["layer", "start_sec", "end_sec"],
        )
        writer.writeheader()
        for layer, (start, end) in enumerate(boundaries):
            writer.writerow(
                {
                    "layer": layer,
                    "start_sec": start,
                    "end_sec": end,
                }
            )


def main() -> None:
    args = parse_args()
    preferred_root = args.num_qubits // 2 if args.root is None else args.root
    if not 0 <= preferred_root < args.num_qubits:
        raise ValueError("root must be a valid qubit index")

    run_dir = args.output_dir / f"seed_{args.seed:06d}"
    if run_dir.exists():
        if not args.overwrite:
            raise FileExistsError(
                f"{run_dir} already exists. Use --overwrite to replace it."
            )
        shutil.rmtree(run_dir)

    audio_root = run_dir / "audio"
    matrix_root = run_dir / "mutual_information_matrices"
    circuit_root = run_dir / "circuits"
    statevector_root = run_dir / "statevectors"
    matrix_root.mkdir(parents=True, exist_ok=True)
    circuit_root.mkdir(parents=True, exist_ok=True)
    if args.save_statevectors:
        statevector_root.mkdir(parents=True, exist_ok=True)

    layer_data = generate_bloch_graph_data(
        num_qubits=args.num_qubits,
        layers=args.layers,
        seed=args.seed,
        edge_tolerance=args.edge_tolerance,
    )

    rendered_by_mode = {"bfs": [], "dfs": [], "combined": []}
    metric_records = []

    for item in layer_data:
        layer = int(item["layer"])
        audio = render_layer_audio(
            item["sonification_backbone"],
            item["bloch"],
            preferred_root=preferred_root,
            config=DEFAULT_CONFIG,
        )

        for mode, signal in audio.items():
            write_wav(
                audio_root / mode / f"layer_{layer:02d}.wav",
                signal,
                int(DEFAULT_CONFIG["sample_rate"]),
            )
            rendered_by_mode[mode].append(signal)

        np.save(
            matrix_root / f"mi_layer_{layer:02d}.npy",
            item["mutual_information_matrix"],
        )

        with (circuit_root / f"circuit_layer_{layer:02d}.qpy").open("wb") as file:
            qpy.dump(item["circuit"], file)

        if args.save_statevectors:
            np.save(
                statevector_root / f"statevector_layer_{layer:02d}.npy",
                item["statevector"],
            )

        metric_records.append(
            {
                "seed": args.seed,
                "num_qubits": args.num_qubits,
                "layer": layer,
                "metrics": item["metrics"],
            }
        )

    write_layer_metrics(metric_records, run_dir / "layer_metrics.csv")
    write_bloch_descriptors(
        layer_data,
        args.seed,
        args.num_qubits,
        run_dir / "bloch_descriptors.csv",
    )
    write_circuit_metrics(
        layer_data,
        args.seed,
        args.num_qubits,
        run_dir / "circuit_metrics.csv",
    )
    write_gate_manifest(layer_data, run_dir / "gate_manifest.csv")

    for mode, chunks in rendered_by_mode.items():
        continuous, boundaries = concatenate_with_gaps(
            chunks,
            gap_sec=float(DEFAULT_CONFIG["layer_gap_sec"]),
            sample_rate=int(DEFAULT_CONFIG["sample_rate"]),
        )
        write_wav(
            audio_root / f"{mode}_continuous.wav",
            continuous,
            int(DEFAULT_CONFIG["sample_rate"]),
        )
        write_segments(
            boundaries,
            audio_root / f"{mode}_segments.csv",
        )

    metadata = {
        "scientific_scope": (
            "Bloch descriptors plus all-pairs mutual-information graph"
        ),
        "num_qubits": args.num_qubits,
        "layers": args.layers,
        "seed": args.seed,
        "preferred_root": preferred_root,
        "edge_tolerance": args.edge_tolerance,
        "audio_config": DEFAULT_CONFIG,
        "mapping": {
            "theta": "log-frequency",
            "phi": "equal-power stereo pan",
            "bloch_radius": "amplitude with fixed floor",
            "normalized_linear_entropy": (
                "deterministic amplitude-modulation depth"
            ),
            "mutual_information": (
                "event duration using the fixed 0-to-2-bit range"
            ),
            "graph": (
                "all-pairs MI for analysis; maximum-spanning forest for traversal"
            ),
        },
        "qft_enabled": False,
        "statevectors_saved": bool(args.save_statevectors),
        "circuits_saved_as_qpy": True,
        "gate_manifest_saved": True,
        "software": {
            "python": platform.python_version(),
            "numpy": _package_version("numpy"),
            "scipy": _package_version("scipy"),
            "networkx": _package_version("networkx"),
            "qiskit": _package_version("qiskit"),
            "git_commit": _git_commit(),
        },
        "output_roles": {
            "bloch_descriptors.csv": "per-qubit local quantum descriptors",
            "layer_metrics.csv": "layer-level quantum summaries",
            "circuit_metrics.csv": "circuit depth and gate-count summaries",
            "gate_manifest.csv": "gates introduced at each RQC layer",
            "circuits/*.qpy": "exact Qiskit circuit snapshots",
            "statevectors/*.npy": (
                "optional exact complex amplitudes for every layer"
            ),
            "mutual_information_matrices/*.npy": (
                "full all-pairs MI matrices"
            ),
            "audio/bfs and audio/dfs": "primary acoustic observations",
            "audio/combined and *_continuous.wav": (
                "listening and visualization aids"
            ),
        },
    }
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Completed paper pipeline: {run_dir.resolve()}")


if __name__ == "__main__":
    main()
