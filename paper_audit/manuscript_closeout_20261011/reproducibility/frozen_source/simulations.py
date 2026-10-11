"""Quantum descriptors for the Bloch + mutual-information graph paper branch."""

from __future__ import annotations

from itertools import combinations
from typing import Any

import networkx as nx
import numpy as np
from qiskit.quantum_info import Statevector, entropy, partial_trace

from circuit import apply_random_circuit

MI_MAX_BITS_TWO_QUBITS = 2.0


def simulate_statevector(circuit) -> np.ndarray:
    """Simulate a noiseless circuit without backend/transpiler side effects."""
    state = np.asarray(Statevector.from_instruction(circuit).data, dtype=complex)
    norm = float(np.vdot(state, state).real)
    if not np.isclose(norm, 1.0, atol=1e-10):
        raise ValueError(f"Statevector is not normalized: norm={norm}")
    return state


def get_bloch_data_from_statevector(
    state: np.ndarray,
    num_qubits: int,
    eps: float = 1e-12,
) -> dict[str, np.ndarray]:
    """Return local Bloch coordinates and physically defined mixedness metrics.

    ``linear_entropy`` is normalized to [0, 1] for a qubit:
        L_q = 1 - ||r_q||^2 = 2(1 - Tr(rho_q^2)).

    ``von_neumann_entropy`` is reported in bits. At r≈0, theta and phi are
    numerically set to zero only as placeholders; downstream code must use the
    Bloch radius to recognize that the direction is physically undefined.
    """
    state = np.asarray(state, dtype=complex)
    expected_dimension = 2**num_qubits
    if state.ndim != 1 or len(state) != expected_dimension:
        raise ValueError(
            f"Expected a statevector of length {expected_dimension}; got shape {state.shape}."
        )

    indices = np.arange(expected_dimension)
    data = {
        key: np.zeros(num_qubits, dtype=float)
        for key in (
            "x",
            "y",
            "z",
            "theta",
            "phi",
            "r",
            "linear_entropy",
            "von_neumann_entropy",
        )
    }

    for qubit in range(num_qubits):
        mask = 1 << qubit
        indices_zero = indices[(indices & mask) == 0]
        indices_one = indices_zero | mask

        amplitudes_zero = state[indices_zero]
        amplitudes_one = state[indices_one]

        p_zero = float(np.sum(np.abs(amplitudes_zero) ** 2))
        p_one = float(np.sum(np.abs(amplitudes_one) ** 2))
        coherence = np.vdot(amplitudes_zero, amplitudes_one)

        x = float(2.0 * np.real(coherence))
        y = float(2.0 * np.imag(coherence))
        z = float(p_zero - p_one)
        radius = float(np.clip(np.sqrt(x * x + y * y + z * z), 0.0, 1.0))

        if radius > eps:
            theta = float(np.arccos(np.clip(z / radius, -1.0, 1.0)))
            phi = float(np.mod(np.arctan2(y, x), 2.0 * np.pi))
        else:
            theta = 0.0
            phi = 0.0

        eigenvalues = np.array([(1.0 + radius) / 2.0, (1.0 - radius) / 2.0])
        positive = eigenvalues[eigenvalues > eps]
        von_neumann_entropy = float(-np.sum(positive * np.log2(positive)))

        data["x"][qubit] = x
        data["y"][qubit] = y
        data["z"][qubit] = z
        data["theta"][qubit] = theta
        data["phi"][qubit] = phi
        data["r"][qubit] = radius
        data["linear_entropy"][qubit] = 1.0 - radius**2
        data["von_neumann_entropy"][qubit] = von_neumann_entropy

    return data


def _single_qubit_entropy(state: Statevector, qubit: int, num_qubits: int) -> float:
    trace_out = [index for index in range(num_qubits) if index != qubit]
    return float(np.real(entropy(partial_trace(state, trace_out), base=2)))



def central_cut_entanglement_metrics(
    state: np.ndarray,
    num_qubits: int,
) -> dict[str, float]:
    """Entanglement entropy across the fixed central bipartition.

    For the noiseless global pure state, S(rho_A) is the bipartite
    entanglement entropy between A and its complement. For 15 qubits this
    uses A={0,...,6} and B={7,...,14}.
    """
    if num_qubits < 2:
        return {
            "central_cut_entanglement_entropy_bits": 0.0,
            "central_cut_entanglement_entropy_normalized": 0.0,
        }

    left_size = num_qubits // 2
    trace_out = list(range(left_size, num_qubits))
    reduced_left = partial_trace(
        Statevector(np.asarray(state, dtype=complex)),
        trace_out,
    )
    entropy_bits = float(np.real(entropy(reduced_left, base=2)))
    maximum_bits = float(min(left_size, num_qubits - left_size))
    normalized = entropy_bits / maximum_bits if maximum_bits > 0.0 else 0.0

    return {
        "central_cut_entanglement_entropy_bits": entropy_bits,
        "central_cut_entanglement_entropy_normalized": normalized,
    }


def build_mutual_information_graph(
    state: np.ndarray,
    num_qubits: int,
    edge_tolerance: float = 1e-10,
) -> tuple[nx.Graph, np.ndarray]:
    """Build the all-pairs quantum-mutual-information graph.

    The graph contains only edges above ``edge_tolerance``. The full symmetric
    matrix is returned separately and remains the primary quantitative object.
    """
    statevector = Statevector(np.asarray(state, dtype=complex))
    graph = nx.Graph()
    graph.add_nodes_from(range(num_qubits))
    matrix = np.zeros((num_qubits, num_qubits), dtype=float)

    single_entropy = {
        qubit: _single_qubit_entropy(statevector, qubit, num_qubits)
        for qubit in range(num_qubits)
    }

    for qubit_a, qubit_b in combinations(range(num_qubits), 2):
        trace_out = [
            index for index in range(num_qubits) if index not in (qubit_a, qubit_b)
        ]
        pair_state = partial_trace(statevector, trace_out)
        pair_entropy = float(np.real(entropy(pair_state, base=2)))
        mutual_information = (
            single_entropy[qubit_a] + single_entropy[qubit_b] - pair_entropy
        )

        if mutual_information < -1e-8:
            raise ValueError(
                "Mutual information is negative beyond numerical tolerance: "
                f"I({qubit_a}:{qubit_b})={mutual_information}"
            )

        mutual_information = float(
            np.clip(mutual_information, 0.0, MI_MAX_BITS_TWO_QUBITS)
        )
        matrix[qubit_a, qubit_b] = mutual_information
        matrix[qubit_b, qubit_a] = mutual_information

        if mutual_information > edge_tolerance:
            graph.add_edge(qubit_a, qubit_b, weight=mutual_information)

    return graph, matrix


def build_sonification_backbone(graph: nx.Graph) -> nx.Graph:
    """Return a maximum-spanning forest used only as the traversal backbone."""
    forest = nx.Graph()
    forest.add_nodes_from(graph.nodes)
    if graph.number_of_edges() > 0:
        forest.add_edges_from(
            nx.maximum_spanning_tree(graph, weight="weight").edges(data=True)
        )
    return forest


def graph_metrics(
    matrix: np.ndarray,
    backbone: nx.Graph,
    edge_tolerance: float = 1e-10,
) -> dict[str, float]:
    """Compute compact MI descriptors using the same numerical edge tolerance."""
    num_qubits = matrix.shape[0]
    upper = matrix[np.triu_indices(num_qubits, k=1)]
    retained = np.where(upper > edge_tolerance, upper, 0.0)
    positive = retained[retained > 0.0]
    strengths = np.zeros(num_qubits, dtype=float)
    thresholded_matrix = np.where(matrix > edge_tolerance, matrix, 0.0)
    strengths[:] = thresholded_matrix.sum(axis=1)
    total = float(np.sum(retained))

    if total > 0.0:
        probabilities = positive / total
        edge_entropy = float(-np.sum(probabilities * np.log2(probabilities)))
    else:
        edge_entropy = 0.0

    possible_edges = num_qubits * (num_qubits - 1) / 2
    return {
        "total_mutual_information": total,
        "mean_pair_mutual_information": (
            float(np.mean(retained)) if len(retained) else 0.0
        ),
        "max_pair_mutual_information": float(np.max(upper)) if len(upper) else 0.0,
        "positive_edge_density": (
            float(len(positive) / possible_edges) if possible_edges else 0.0
        ),
        "edge_weight_entropy": edge_entropy,
        "mean_node_strength": float(np.mean(strengths)),
        "max_node_strength": float(np.max(strengths)),
        "backbone_edges": float(backbone.number_of_edges()),
        "backbone_components": float(nx.number_connected_components(backbone)),
    }


def bloch_metrics(
    data: dict[str, np.ndarray],
    direction_epsilon: float = 1e-10,
) -> dict[str, float]:
    """Return layer summaries without letting undefined directions dominate."""
    radius = np.asarray(data["r"], dtype=float)
    directional_weights = np.where(radius > direction_epsilon, radius, 0.0)
    weight_sum = float(np.sum(directional_weights))

    if weight_sum > 0.0:
        mean_theta = float(
            np.sum(directional_weights * data["theta"]) / weight_sum
        )
        circular_resultant = np.sum(
            directional_weights * np.exp(1j * data["phi"])
        ) / weight_sum
        phi_circular_variance = float(1.0 - np.abs(circular_resultant))
    else:
        mean_theta = 0.0
        phi_circular_variance = 0.0

    return {
        "mean_bloch_radius": float(np.mean(radius)),
        "std_bloch_radius": float(np.std(radius)),
        "mean_linear_entropy": float(np.mean(data["linear_entropy"])),
        "mean_von_neumann_entropy": float(
            np.mean(data["von_neumann_entropy"])
        ),
        "mean_theta_radius_weighted": mean_theta,
        "phi_circular_variance_radius_weighted": phi_circular_variance,
        "directional_weight_sum": weight_sum,
        "directional_qubit_fraction": float(
            np.mean(radius > direction_epsilon)
        ),
    }


def generate_bloch_graph_data(
    num_qubits: int,
    layers: int,
    seed: int = 42,
    edge_tolerance: float = 1e-10,
) -> list[dict[str, Any]]:
    """Generate one prefix-consistent RQC trajectory and its descriptors."""
    output: list[dict[str, Any]] = []

    for layer in range(layers + 1):
        circuit = apply_random_circuit(num_qubits, layer, seed=seed)
        state = simulate_statevector(circuit)
        bloch = get_bloch_data_from_statevector(state, num_qubits)
        full_graph, mi_matrix = build_mutual_information_graph(
            state, num_qubits, edge_tolerance=edge_tolerance
        )
        entanglement_metrics = central_cut_entanglement_metrics(state, num_qubits)
        backbone = build_sonification_backbone(full_graph)

        output.append(
            {
                "layer": layer,
                "circuit": circuit,
                "statevector": state,
                "bloch": bloch,
                "mutual_information_matrix": mi_matrix,
                "mutual_information_graph": full_graph,
                "sonification_backbone": backbone,
                "metrics": {
                    **bloch_metrics(bloch),
                    **entanglement_metrics,
                    **graph_metrics(
                        mi_matrix,
                        backbone,
                        edge_tolerance=edge_tolerance,
                    ),
                },
            }
        )

    return output
