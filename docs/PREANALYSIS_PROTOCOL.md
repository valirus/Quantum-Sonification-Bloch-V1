# Pre-analysis protocol

## 1. Confirmatory question

Does deterministic Bloch-plus-MI-graph sonification preserve local and relational structure across random quantum-circuit trajectories beyond depth-matched null pairings?

## 2. Frozen instrument configuration

```text
num_qubits = 15
applied_layers = 10
snapshots = 0..10
root_qubit = 7
edge_tolerance = 1e-10
sample_rate = 22050 Hz
primary_modes = BFS, DFS
statevectors_saved = true
combined_and_continuous = excluded from primary inference
```

The gate ensemble, fixed fSim parameters, acoustic mapping and STFT defaults are frozen at Git tag `paper-pipeline-v1.0.0`.

## 3. Experimental units

- Independent unit: one circuit seed.
- Repeated measurements: layers 0–10 within a seed.
- Acoustic conditions: BFS and DFS within each seed/layer.
- Layers must not be treated as independent samples.

## 4. Dataset split

- Engineering pilot: seeds 0–19. Used only for runtime, file-integrity and diagnostic checks.
- Confirmatory dataset: seeds 1000–1099 (100 independent trajectories).
- Pilot observations are excluded from confirmatory inferential results.
- Increasing the confirmatory count is allowed only before inspecting confirmatory associations and must be recorded in a protocol amendment.

## 5. Primary quantum representations

### Local representation

For every seed, layer and qubit:

```text
x, y, z, theta, phi, r, linear_entropy, von_neumann_entropy
```

The primary local distance is the mean Euclidean distance between aligned Bloch vectors `(x,y,z)` across qubits. Angles are not used directly in Euclidean distance.

### Relational representation

The primary relational object is the full symmetric all-pairs MI matrix. The primary MI distance is Frobenius distance between upper-triangular matrices.

### Global reference

Central-cut entanglement entropy across `A={q0,...,q6}` and `B={q7,...,q14}` is retained as a non-sonified reference variable. It is not used as an acoustic control parameter.

## 6. Primary acoustic representation

The confirmatory acoustic vector uses the precomputed BFS/DFS layer features:

```text
duration_sec
rms_joint
spectral_centroid_mean_hz
spectral_bandwidth_mean_hz
spectral_entropy_mean
spectral_flux_mean
stereo_balance
stereo_correlation
```

Features are standardized using parameters fitted on the confirmatory dataset at analysis time. The raw values remain archived.

## 7. Confirmatory hypotheses

- H1: Bloch-space dissimilarity is positively associated with acoustic-feature dissimilarity.
- H2: MI-matrix dissimilarity is positively associated with acoustic-feature dissimilarity.
- H3: The observed H1/H2 associations exceed depth-matched permutation nulls.

BFS-versus-DFS differences are secondary; neither mode is assumed superior in advance.

## 8. Null model

The primary permutation null shuffles acoustic observations among seeds within the same layer and mode. This preserves circuit depth, duration distribution and mode while breaking the state-to-audio correspondence.

At least 5,000 permutations are used for final p-values. Bootstrap confidence intervals resample seeds, not individual layers.

## 9. Covariates and dependence

Depth/layer is controlled explicitly. Mixed-effects or cluster-robust models use seed as the clustering/grouping variable. No test may count 1,100 layer rows as 1,100 independent circuits.

## 10. Multiple comparisons

Primary endpoints are H1 and H2 for BFS and DFS. False-discovery-rate correction is applied across these four primary tests. All additional features, PCA visualizations and correlations are exploratory.

## 11. Direct-mapping caveat

The mappings `theta→frequency`, `r→amplitude`, `linear entropy→AM depth`, and `MI→duration` are designed into the instrument. Correlations between each source variable and its directly assigned acoustic parameter are implementation checks, not the main scientific finding.

## 12. Exclusions

A seed is excluded only when:

- pipeline validation fails;
- statevector normalization fails;
- a matrix contains non-finite values or violates symmetry/range checks;
- an audio file clips or is missing;
- metadata does not match the frozen configuration.

Every exclusion and reason is recorded in `dataset_manifest.csv`. No seed is excluded because its sound or quantum metrics appear unusual.
