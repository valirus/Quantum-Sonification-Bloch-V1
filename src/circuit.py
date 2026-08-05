"""Random-quantum-circuit construction for the paper pipeline."""

from __future__ import annotations

import random

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate

from gates import single_q_gates


def create_fsim_gate(theta: float = np.pi / 2, phi: float = np.pi / 6) -> UnitaryGate:
    """Return the nearest-neighbour fSim interaction used by the RQC ensemble."""
    matrix = np.array(
        [
            [1, 0, 0, 0],
            [0, np.cos(theta), -1j * np.sin(theta), 0],
            [0, -1j * np.sin(theta), np.cos(theta), 0],
            [0, 0, 0, np.exp(-1j * phi)],
        ],
        dtype=complex,
    )
    return UnitaryGate(matrix, label="fSim")


def apply_random_circuit(num_qubits: int, layers: int, seed: int = 42) -> QuantumCircuit:
    """Build a deterministic prefix-consistent RQC.

    Reusing the same seed guarantees that the circuit with ``layers=L`` is a
    strict prefix of the circuit with ``layers=L+1``. This is essential when
    layers are interpreted as one temporal quantum evolution.
    """
    if num_qubits < 1:
        raise ValueError("num_qubits must be at least 1")
    if layers < 0:
        raise ValueError("layers must be non-negative")

    rng = random.Random(seed)
    circuit = QuantumCircuit(num_qubits)
    fsim_gate = create_fsim_gate()
    previous_gate = [-1] * num_qubits

    for layer_index in range(layers):
        for qubit in range(num_qubits):
            choices = list(range(len(single_q_gates)))
            if previous_gate[qubit] != -1:
                choices.remove(previous_gate[qubit])
            selected = rng.choice(choices)
            circuit.append(single_q_gates[selected], [qubit])
            previous_gate[qubit] = selected

        start = 0 if layer_index % 2 == 0 else 1
        for qubit in range(start, num_qubits - 1, 2):
            circuit.append(fsim_gate, [qubit, qubit + 1])

    return circuit
