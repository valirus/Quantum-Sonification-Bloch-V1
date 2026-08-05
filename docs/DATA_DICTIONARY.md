# Data dictionary

## `layer_metrics.csv`

One row per seed and circuit snapshot.

- `mean_bloch_radius`, `std_bloch_radius`: local purity geometry summaries.
- `mean_linear_entropy`: mean `1-r^2`; redundant with radius and treated accordingly.
- `mean_von_neumann_entropy`: mean qubit-versus-rest entanglement entropy for the pure global state.
- `mean_theta_radius_weighted`: radius-weighted polar angle summary.
- `phi_circular_variance_radius_weighted`: radius-weighted circular dispersion.
- `central_cut_entanglement_entropy_bits`: bipartite entropy across the fixed central cut.
- `central_cut_entanglement_entropy_normalized`: central-cut entropy divided by 7 for 15 qubits.
- `total_mutual_information`: sum of retained upper-triangular MI weights.
- `mean_pair_mutual_information`: mean over all possible pairs after thresholding sub-tolerance values to zero.
- `positive_edge_density`: fraction of all pairs above tolerance.
- `edge_weight_entropy`: Shannon entropy of retained normalized edge weights.
- `mean_node_strength`, `max_node_strength`: MI-weighted node-strength summaries.
- `backbone_edges`, `backbone_components`: traversal-forest descriptors, not full-graph scientific summaries.

## `bloch_descriptors.csv`

One row per seed × layer × qubit. Angles at `r≈0` are numeric placeholders and must not be interpreted without the radius.

## `audio_features.csv`

One row per seed × layer × primary mode. `combined` and continuous WAVs are excluded.

## Binary artifacts

- `statevectors/*.npy`: complex amplitudes in Qiskit little-endian ordering.
- `mutual_information_matrices/*.npy`: symmetric all-pairs MI matrices in bits.
- `circuits/*.qpy`: exact Qiskit circuit snapshots.
