"""Deterministic sonification of Bloch descriptors over an MI graph backbone."""

from __future__ import annotations

from collections import deque
from typing import Iterable

import networkx as nx
import numpy as np
from scipy.io import wavfile

MI_MAX_BITS_TWO_QUBITS = 2.0

DEFAULT_CONFIG = {
    "sample_rate": 22050,
    "frequency_min_hz": 110.0,
    "frequency_max_hz": 880.0,
    "amplitude_floor": 0.12,
    "voice_gain": 0.22,
    "am_rate_hz": 6.0,
    "am_depth_max": 0.30,
    "bloch_direction_epsilon": 1e-8,
    "attack_fraction_bfs": 0.20,
    "attack_fraction_dfs": 0.05,
    "event_duration_min_sec": 0.10,
    "event_duration_max_sec": 0.60,
    "root_duration_sec": 0.30,
    "component_gap_sec": 0.12,
    "layer_gap_sec": 0.20,
    "combined_bfs_gain": 0.5,
    "combined_dfs_gain": 0.5,
}


def merge_config(overrides=None) -> dict:
    config = DEFAULT_CONFIG.copy()
    if overrides:
        config.update(overrides)
    return config


def make_envelope(num_samples: int, attack_fraction: float) -> np.ndarray:
    if num_samples <= 1:
        return np.ones(max(1, num_samples), dtype=float)
    attack = max(1, min(num_samples - 1, int(num_samples * attack_fraction)))
    decay = num_samples - attack
    return np.concatenate(
        [
            np.linspace(0.0, 1.0, attack, endpoint=False),
            np.linspace(1.0, 0.0, decay, endpoint=True),
        ]
    )


def theta_to_frequency(theta: float, config: dict) -> float:
    """Map theta monotonically to a logarithmic audible frequency range."""
    fraction = float(np.clip(theta / np.pi, 0.0, 1.0))
    low = float(config["frequency_min_hz"])
    high = float(config["frequency_max_hz"])
    return low * (high / low) ** fraction


def phi_to_equal_power_pan(signal: np.ndarray, phi: float) -> np.ndarray:
    pan = float(np.mod(phi, 2.0 * np.pi) / (2.0 * np.pi))
    left = signal * np.cos(pan * np.pi / 2.0)
    right = signal * np.sin(pan * np.pi / 2.0)
    return np.column_stack([left, right])


def mutual_information_to_duration(weight: float, config: dict) -> float:
    """Use the fixed physical range I in [0,2] bits; no per-layer renormalization."""
    normalized = float(np.clip(weight / MI_MAX_BITS_TWO_QUBITS, 0.0, 1.0))
    minimum = float(config["event_duration_min_sec"])
    maximum = float(config["event_duration_max_sec"])
    return maximum - normalized * (maximum - minimum)


def synthesize_bloch_note(
    node: int,
    duration_sec: float,
    bloch_data: dict[str, np.ndarray],
    config: dict,
    percussive: bool,
) -> np.ndarray:
    sample_rate = int(config["sample_rate"])
    num_samples = max(1, int(round(sample_rate * duration_sec)))
    time = np.arange(num_samples, dtype=float) / sample_rate

    theta = float(bloch_data["theta"][node])
    phi = float(bloch_data["phi"][node])
    radius = float(bloch_data["r"][node])
    linear_entropy = float(bloch_data["linear_entropy"][node])

    # At r≈0 the Bloch direction is undefined. Keep the qubit audible because
    # the graph may still carry strong relational information, but use a neutral
    # carrier and centered pan instead of the numerical theta=phi=0 placeholders.
    if radius <= float(config["bloch_direction_epsilon"]):
        theta = np.pi / 2.0
        phi = np.pi

    frequency = theta_to_frequency(theta, config)
    amplitude = float(config["voice_gain"]) * (
        float(config["amplitude_floor"])
        + (1.0 - float(config["amplitude_floor"])) * radius
    )
    am_depth = float(config["am_depth_max"]) * linear_entropy
    modulation = 1.0 + am_depth * np.sin(
        2.0 * np.pi * float(config["am_rate_hz"]) * time
    )
    mono = amplitude * modulation * np.sin(2.0 * np.pi * frequency * time)

    attack_key = "attack_fraction_dfs" if percussive else "attack_fraction_bfs"
    mono *= make_envelope(num_samples, float(config[attack_key]))
    return phi_to_equal_power_pan(mono, phi)


def _sorted_neighbors(graph: nx.Graph, node: int) -> list[int]:
    return sorted(
        graph.neighbors(node),
        key=lambda neighbor: (-float(graph[node][neighbor]["weight"]), int(neighbor)),
    )


def _ordered_components(graph: nx.Graph, preferred_root: int) -> list[set[int]]:
    components = [set(component) for component in nx.connected_components(graph)]
    return sorted(
        components,
        key=lambda component: (
            0 if preferred_root in component else 1,
            min(component),
        ),
    )


def _component_root(component: set[int], preferred_root: int) -> int:
    return preferred_root if preferred_root in component else min(component)


def weighted_bfs_frontiers(
    graph: nx.Graph,
    preferred_root: int,
) -> list[list[tuple[int, float]]]:
    """Return BFS frontiers with deterministic weight-sorted neighbours."""
    frontiers: list[list[tuple[int, float]]] = []

    for component in _ordered_components(graph, preferred_root):
        root = _component_root(component, preferred_root)
        queue = deque([(root, 0, 0.0)])
        visited = {root}
        by_depth: dict[int, list[tuple[int, float]]] = {}

        while queue:
            node, depth, incoming_weight = queue.popleft()
            by_depth.setdefault(depth, []).append((node, incoming_weight))
            for neighbor in _sorted_neighbors(graph, node):
                if neighbor in component and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(
                        (neighbor, depth + 1, float(graph[node][neighbor]["weight"]))
                    )

        frontiers.extend(by_depth[depth] for depth in sorted(by_depth))
        frontiers.append([])

    return frontiers[:-1] if frontiers else []


def weighted_dfs_events(
    graph: nx.Graph,
    preferred_root: int,
) -> list[tuple[int, float] | None]:
    """Return deterministic DFS events; None marks a component separator."""
    events: list[tuple[int, float] | None] = []

    for component in _ordered_components(graph, preferred_root):
        root = _component_root(component, preferred_root)
        visited: set[int] = set()

        def visit(node: int, incoming_weight: float) -> None:
            visited.add(node)
            events.append((node, incoming_weight))
            for neighbor in _sorted_neighbors(graph, node):
                if neighbor in component and neighbor not in visited:
                    visit(neighbor, float(graph[node][neighbor]["weight"]))

        visit(root, 0.0)
        events.append(None)

    return events[:-1] if events else []


def _silence(duration_sec: float, sample_rate: int) -> np.ndarray:
    return np.zeros((max(1, int(round(duration_sec * sample_rate))), 2), dtype=float)


def render_bfs(
    backbone: nx.Graph,
    bloch_data: dict[str, np.ndarray],
    preferred_root: int,
    config: dict,
) -> np.ndarray:
    sample_rate = int(config["sample_rate"])
    pieces: list[np.ndarray] = []

    for frontier in weighted_bfs_frontiers(backbone, preferred_root):
        if not frontier:
            pieces.append(_silence(float(config["component_gap_sec"]), sample_rate))
            continue

        incoming_weights = [weight for _, weight in frontier if weight > 0.0]
        weight = float(np.mean(incoming_weights)) if incoming_weights else 0.0
        duration = (
            float(config["root_duration_sec"])
            if not incoming_weights
            else mutual_information_to_duration(weight, config)
        )
        layer = np.zeros((max(1, int(round(duration * sample_rate))), 2), dtype=float)
        for node, _ in frontier:
            note = synthesize_bloch_note(
                node, duration, bloch_data, config, percussive=False
            )
            layer += note / len(frontier)
        pieces.append(layer)

    return (
        np.concatenate(pieces)
        if pieces
        else _silence(config["root_duration_sec"], sample_rate)
    )


def render_dfs(
    backbone: nx.Graph,
    bloch_data: dict[str, np.ndarray],
    preferred_root: int,
    config: dict,
) -> np.ndarray:
    sample_rate = int(config["sample_rate"])
    pieces: list[np.ndarray] = []

    for event in weighted_dfs_events(backbone, preferred_root):
        if event is None:
            pieces.append(_silence(float(config["component_gap_sec"]), sample_rate))
            continue
        node, incoming_weight = event
        duration = (
            float(config["root_duration_sec"])
            if incoming_weight <= 0.0
            else mutual_information_to_duration(incoming_weight, config)
        )
        pieces.append(
            synthesize_bloch_note(
                node, duration, bloch_data, config, percussive=True
            )
        )

    return (
        np.concatenate(pieces)
        if pieces
        else _silence(config["root_duration_sec"], sample_rate)
    )


def pad_with_zeros(audio: np.ndarray, length: int) -> np.ndarray:
    if len(audio) >= length:
        return audio[:length]
    return np.pad(audio, ((0, length - len(audio)), (0, 0)))


def render_layer_audio(
    backbone: nx.Graph,
    bloch_data: dict[str, np.ndarray],
    preferred_root: int,
    config=None,
) -> dict[str, np.ndarray]:
    """Render BFS, DFS and a non-looped listening mix.

    BFS and DFS remain separate primary outputs. The combined file is only a
    listening aid; it must not replace branch-specific quantitative analysis.
    """
    config = merge_config(config)
    bfs = render_bfs(backbone, bloch_data, preferred_root, config)
    dfs = render_dfs(backbone, bloch_data, preferred_root, config)

    target_length = max(len(bfs), len(dfs))
    combined = (
        float(config["combined_bfs_gain"]) * pad_with_zeros(bfs, target_length)
        + float(config["combined_dfs_gain"]) * pad_with_zeros(dfs, target_length)
    )

    for name, audio in {"bfs": bfs, "dfs": dfs, "combined": combined}.items():
        peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
        if peak > 1.0 + 1e-9:
            raise ValueError(
                f"{name} audio would clip (peak={peak:.3f}); reduce fixed gains."
            )

    return {
        "bfs": bfs.astype(np.float32),
        "dfs": dfs.astype(np.float32),
        "combined": combined.astype(np.float32),
    }


def write_wav(path, audio: np.ndarray, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, sample_rate, audio.astype(np.float32))


def concatenate_with_gaps(
    chunks: Iterable[np.ndarray],
    gap_sec: float,
    sample_rate: int,
) -> tuple[np.ndarray, list[tuple[float, float]]]:
    pieces: list[np.ndarray] = []
    boundaries: list[tuple[float, float]] = []
    cursor = 0
    gap = _silence(gap_sec, sample_rate)

    for index, chunk in enumerate(chunks):
        start = cursor / sample_rate
        pieces.append(chunk)
        cursor += len(chunk)
        end = cursor / sample_rate
        boundaries.append((start, end))
        if index >= 0:
            pieces.append(gap)
            cursor += len(gap)

    if pieces:
        pieces.pop()
    return (
        np.concatenate(pieces) if pieces else _silence(0.1, sample_rate),
        boundaries,
    )
