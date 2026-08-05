"""Small end-to-end pipeline test using two qubits and one applied layer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_end_to_end_pipeline(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    output = tmp_path / "runs"
    run = output / "seed_000005"

    subprocess.run(
        [
            sys.executable,
            str(repo / "src" / "rqc_sonification.py"),
            "--num-qubits", "2",
            "--layers", "1",
            "--seed", "5",
            "--root", "0",
            "--output-dir", str(output),
            "--save-statevectors",
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(repo / "analysis" / "extract_stft_features.py"),
            str(run),
            "--output", str(run / "audio_features.csv"),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(repo / "scripts" / "validate_run.py"),
            str(run),
            "--num-qubits", "2",
            "--layers", "1",
            "--root", "0",
            "--require-statevectors",
        ],
        check=True,
    )
