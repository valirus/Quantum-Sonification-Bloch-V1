import sys
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from circuit import apply_random_circuit
from simulations import (
    bloch_metrics,
    build_mutual_information_graph,
    central_cut_entanglement_metrics,
    generate_bloch_graph_data,
    get_bloch_data_from_statevector,
    graph_metrics,
)


def test_rqc_is_prefix_consistent():
    one_layer = apply_random_circuit(4, 1, seed=7)
    two_layers = apply_random_circuit(4, 2, seed=7)
    assert two_layers.data[: len(one_layer.data)] == one_layer.data


def test_bloch_for_zero_and_plus_states():
    zero = get_bloch_data_from_statevector(
        np.array([1.0, 0.0], complex),
        1,
    )
    assert np.allclose(
        [zero["x"][0], zero["y"][0], zero["z"][0]],
        [0, 0, 1],
    )
    assert np.isclose(zero["r"][0], 1.0)
    assert np.isclose(zero["linear_entropy"][0], 0.0)

    plus = get_bloch_data_from_statevector(
        np.array([1.0, 1.0], complex) / np.sqrt(2),
        1,
    )
    assert np.allclose(
        [plus["x"][0], plus["y"][0], plus["z"][0]],
        [1, 0, 0],
    )
    assert np.isclose(plus["theta"][0], np.pi / 2)


def test_bell_state_has_mixed_local_bloch_and_two_bits_of_mi():
    bell = np.array([1.0, 0.0, 0.0, 1.0], complex) / np.sqrt(2)
    bloch = get_bloch_data_from_statevector(bell, 2)
    assert np.allclose(bloch["r"], [0.0, 0.0], atol=1e-10)
    assert np.allclose(
        bloch["linear_entropy"],
        [1.0, 1.0],
        atol=1e-10,
    )

    graph, matrix = build_mutual_information_graph(bell, 2)
    assert np.isclose(matrix[0, 1], 2.0, atol=1e-10)
    assert np.isclose(graph[0][1]["weight"], 2.0, atol=1e-10)


def test_product_state_has_zero_mutual_information():
    product = np.array([1.0, 0.0, 0.0, 0.0], complex)
    graph, matrix = build_mutual_information_graph(product, 2)
    assert np.allclose(matrix, 0.0)
    assert graph.number_of_edges() == 0



def test_central_cut_entanglement_for_product_and_bell_states():
    product = np.array([1.0, 0.0, 0.0, 0.0], complex)
    product_metrics = central_cut_entanglement_metrics(product, 2)
    assert np.isclose(
        product_metrics["central_cut_entanglement_entropy_bits"],
        0.0,
    )

    bell = np.array([1.0, 0.0, 0.0, 1.0], complex) / np.sqrt(2)
    bell_metrics = central_cut_entanglement_metrics(bell, 2)
    assert np.isclose(
        bell_metrics["central_cut_entanglement_entropy_bits"],
        1.0,
    )
    assert np.isclose(
        bell_metrics["central_cut_entanglement_entropy_normalized"],
        1.0,
    )


def test_graph_metrics_use_the_same_edge_tolerance():
    matrix = np.array(
        [
            [0.0, 1e-12, 0.5],
            [1e-12, 0.0, 0.0],
            [0.5, 0.0, 0.0],
        ]
    )
    backbone = nx.Graph()
    backbone.add_nodes_from(range(3))
    backbone.add_edge(0, 2, weight=0.5)

    metrics = graph_metrics(
        matrix,
        backbone,
        edge_tolerance=1e-10,
    )
    assert np.isclose(metrics["total_mutual_information"], 0.5)
    assert np.isclose(metrics["positive_edge_density"], 1.0 / 3.0)


def test_bloch_directional_metrics_ignore_zero_radius_qubits():
    data = {
        "r": np.array([1.0, 0.0]),
        "theta": np.array([np.pi / 2.0, 0.0]),
        "phi": np.array([np.pi, 0.0]),
        "linear_entropy": np.array([0.0, 1.0]),
        "von_neumann_entropy": np.array([0.0, 1.0]),
    }
    metrics = bloch_metrics(data)
    assert np.isclose(
        metrics["mean_theta_radius_weighted"],
        np.pi / 2.0,
    )
    assert np.isclose(metrics["directional_qubit_fraction"], 0.5)


def test_generated_layers_include_normalized_statevectors():
    data = generate_bloch_graph_data(
        num_qubits=2,
        layers=1,
        seed=3,
    )
    assert len(data) == 2
    for item in data:
        assert "statevector" in item
        assert np.isclose(
            np.vdot(item["statevector"], item["statevector"]).real,
            1.0,
        )
