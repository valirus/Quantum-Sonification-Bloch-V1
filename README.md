# Quantum Sonification of Random Quantum Circuits

Publication pipeline for deterministic sonification of random quantum-circuit trajectories using:

1. local single-qubit Bloch geometry;
2. all-pairs quantum mutual information (MI) as a weighted correlation graph;
3. deterministic BFS/DFS traversal over a maximum-spanning forest;
4. a non-sonified central-bipartition entanglement entropy used as a global reference.

QFT, Schmidt-spectrum, negativity, MPS and legacy prototype modes are intentionally excluded from this repository.

## Scientific scope

| Quantum quantity | Role |
|---|---|
| Bloch polar angle `theta` | logarithmic carrier frequency |
| Bloch azimuth `phi` | equal-power stereo pan |
| Bloch radius `r` | amplitude with a fixed floor |
| normalized linear entropy `1-r^2` | deterministic AM depth |
| pairwise MI `I(i:j)` | event duration on the fixed 0–2 bit range |
| all-pairs MI matrix | primary relational quantum representation |
| maximum-spanning forest | deterministic traversal backbone only |
| central-cut entropy | global entanglement reference; not sonified |

MI represents total pairwise correlation, not exclusively entanglement. For the noiseless pure global state, single-qubit entropy measures entanglement between that qubit and the remaining register.

## Fixed experiment

The confirmatory configuration is defined in `docs/PREANALYSIS_PROTOCOL.md`.

- 15 qubits;
- 10 applied circuit layers plus layer 0;
- fixed root qubit 7;
- MI edge tolerance `1e-10`;
- primary acoustic modes: BFS and DFS;
- `combined` and continuous WAV files are listening/visualization aids only.

Qiskit statevector indexing follows little-endian convention: index bits represent `|q_(N-1)...q_1 q_0>`.

## Environment

Use Python 3.11 in a dedicated environment.

```bash
conda create -n quantum_sonification_paper python=3.11 -y
conda activate quantum_sonification_paper
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip freeze > requirements-lock.txt
```

## Validate the code

```bash
python -m py_compile src/*.py analysis/*.py scripts/*.py tests/*.py
python -m pytest -q
```

## Generate one canonical run

Run from the repository root:

```bash
python src/rqc_sonification.py \
  --num-qubits 15 \
  --layers 10 \
  --seed 42 \
  --root 7 \
  --edge-tolerance 1e-10 \
  --output-dir outputs/paper_bloch_graph \
  --save-statevectors
```

Extract the primary acoustic features:

```bash
python analysis/extract_stft_features.py \
  outputs/paper_bloch_graph/seed_000042 \
  --output outputs/paper_bloch_graph/seed_000042/audio_features.csv
```

Validate the run:

```bash
python scripts/validate_run.py \
  outputs/paper_bloch_graph/seed_000042 \
  --num-qubits 15 \
  --layers 10 \
  --root 7 \
  --require-statevectors
```

## Build the dataset

First run the pilot seeds defined in the protocol. After the protocol is frozen, run the confirmatory seeds:

```bash
python analysis/run_dataset.py \
  --seed-start 1000 \
  --seed-count 100 \
  --num-qubits 15 \
  --layers 10 \
  --root 7 \
  --output-dir outputs/confirmatory_dataset
```

Aggregate analysis-ready tables:

```bash
python analysis/aggregate_dataset.py \
  outputs/confirmatory_dataset \
  --output-dir outputs/confirmatory_dataset/tables
```

## Per-seed outputs

```text
seed_XXXXXX/
├── metadata.json
├── layer_metrics.csv
├── bloch_descriptors.csv
├── circuit_metrics.csv
├── gate_manifest.csv
├── circuits/*.qpy
├── statevectors/*.npy
├── mutual_information_matrices/*.npy
└── audio/
    ├── bfs/layer_XX.wav
    ├── dfs/layer_XX.wav
    ├── combined/layer_XX.wav
    ├── *_continuous.wav
    └── *_segments.csv
```

`audio_features.csv` contains only BFS/DFS layer observations: 11 layers × 2 modes = 22 rows per seed.

## Claims that this code supports

The instrument supports quantitative testing of whether local and relational quantum-state structure remains distinguishable in acoustic feature space. Direct mapping correlations alone are not evidence of scientific preservation; confirmatory results must be compared against predeclared permutation controls and analyzed with circuit seed as the independent experimental unit.
