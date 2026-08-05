"""Validate one generated seed directory before admitting it to the dataset."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expected_gate_count(num_qubits: int, layers: int) -> int:
    two_qubit = 0
    for layer in range(layers):
        start = 0 if layer % 2 == 0 else 1
        two_qubit += len(range(start, num_qubits - 1, 2))
    return num_qubits * layers + two_qubit


def validate(args: argparse.Namespace) -> None:
    run = args.run_dir.resolve()
    snapshots = args.layers + 1
    metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))

    assert metadata["qft_enabled"] is False
    assert metadata["num_qubits"] == args.num_qubits
    assert metadata["layers"] == args.layers
    assert metadata["preferred_root"] == args.root
    assert np.isclose(metadata["edge_tolerance"], args.edge_tolerance)
    if args.require_statevectors:
        assert metadata["statevectors_saved"] is True

    circuits = sorted((run / "circuits").glob("circuit_layer_*.qpy"))
    matrices = sorted((run / "mutual_information_matrices").glob("mi_layer_*.npy"))
    states = sorted((run / "statevectors").glob("statevector_layer_*.npy"))
    assert len(circuits) == snapshots
    assert len(matrices) == snapshots
    if args.require_statevectors:
        assert len(states) == snapshots

    dimension = 2**args.num_qubits
    for path in states:
        state = np.load(path)
        assert state.shape == (dimension,)
        assert np.all(np.isfinite(state))
        assert np.isclose(np.vdot(state, state).real, 1.0, atol=1e-10)

    for path in matrices:
        matrix = np.load(path)
        assert matrix.shape == (args.num_qubits, args.num_qubits)
        assert np.all(np.isfinite(matrix))
        assert np.allclose(matrix, matrix.T, atol=1e-10)
        assert np.allclose(np.diag(matrix), 0.0, atol=1e-10)
        assert np.min(matrix) >= -1e-10
        assert np.max(matrix) <= 2.0 + 1e-10

    for mode in ("bfs", "dfs", "combined"):
        wavs = sorted((run / "audio" / mode).glob("layer_*.wav"))
        assert len(wavs) == snapshots
        for path in wavs:
            _, audio = wavfile.read(path)
            assert audio.ndim == 2 and audio.shape[1] == 2
            assert np.all(np.isfinite(audio))
            assert np.max(np.abs(audio)) <= 1.0 + 1e-7

    layer_rows = read_rows(run / "layer_metrics.csv")
    assert len(layer_rows) == snapshots
    required_metrics = {
        "central_cut_entanglement_entropy_bits",
        "central_cut_entanglement_entropy_normalized",
        "total_mutual_information",
        "mean_bloch_radius",
    }
    assert required_metrics.issubset(layer_rows[0])

    assert len(read_rows(run / "circuit_metrics.csv")) == snapshots
    assert len(read_rows(run / "bloch_descriptors.csv")) == snapshots * args.num_qubits
    assert len(read_rows(run / "gate_manifest.csv")) == expected_gate_count(
        args.num_qubits, args.layers
    )
    assert len(read_rows(run / "audio_features.csv")) == snapshots * 2

    for mode in ("bfs", "dfs", "combined"):
        assert (run / "audio" / f"{mode}_continuous.wav").is_file()
        assert len(read_rows(run / "audio" / f"{mode}_segments.csv")) == snapshots

    print(f"VALIDATION PASSED: {run}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--num-qubits", type=int, required=True)
    parser.add_argument("--layers", type=int, required=True)
    parser.add_argument("--root", type=int, required=True)
    parser.add_argument("--edge-tolerance", type=float, default=1e-10)
    parser.add_argument("--require-statevectors", action="store_true")
    validate(parser.parse_args())


if __name__ == "__main__":
    main()
