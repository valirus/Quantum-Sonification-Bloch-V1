import numpy as np
from qiskit.circuit.library import UnitaryGate

sqrt_X_mat = np.array([
    [1 / np.sqrt(2), -1j / np.sqrt(2)],
    [-1j / np.sqrt(2), 1 / np.sqrt(2)]
], dtype=complex)

sqrt_Y_mat = np.array([
    [1 / np.sqrt(2), -1 / np.sqrt(2)],
    [1 / np.sqrt(2), 1 / np.sqrt(2)]
], dtype=complex)

sqrt_W_mat = np.array([
    [1 / np.sqrt(2), -(1 + 1j) / 2],
    [(1 - 1j) / 2, 1 / np.sqrt(2)]
], dtype=complex)

gate_X = UnitaryGate(sqrt_X_mat, label="√X")
gate_Y = UnitaryGate(sqrt_Y_mat, label="√Y")
gate_W = UnitaryGate(sqrt_W_mat, label="√W")

single_q_gates = [gate_X, gate_Y, gate_W]
