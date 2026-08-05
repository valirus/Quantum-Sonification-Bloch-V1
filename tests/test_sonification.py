import sys
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sonification import render_layer_audio


def test_render_is_deterministic_and_does_not_clip():
    graph = nx.Graph()
    graph.add_nodes_from([0, 1])
    graph.add_edge(0, 1, weight=1.0)
    bloch = {
        "theta": np.array([0.0, np.pi]),
        "phi": np.array([0.0, np.pi]),
        "r": np.array([1.0, 0.5]),
        "linear_entropy": np.array([0.0, 0.75]),
    }

    first = render_layer_audio(graph, bloch, preferred_root=0)
    second = render_layer_audio(graph, bloch, preferred_root=0)

    for mode in first:
        assert np.array_equal(first[mode], second[mode])
        assert np.max(np.abs(first[mode])) <= 1.0


def test_zero_radius_direction_uses_neutral_non_silent_carrier():
    graph = nx.Graph()
    graph.add_node(0)
    bloch = {
        "theta": np.array([0.0]),
        "phi": np.array([0.0]),
        "r": np.array([0.0]),
        "linear_entropy": np.array([1.0]),
    }

    audio = render_layer_audio(graph, bloch, preferred_root=0)
    assert np.max(np.abs(audio["bfs"])) > 0.0

    left_rms = np.sqrt(np.mean(audio["bfs"][:, 0] ** 2))
    right_rms = np.sqrt(np.mean(audio["bfs"][:, 1] ** 2))
    assert np.isclose(left_rms, right_rms, rtol=1e-5, atol=1e-8)
