import type { AudioSegment, BlochDescriptor, GateOperation, GraphEdge, SeedMetadata } from "./types";
import type { DecodedSignal } from "./signalMath";

export const gateTargets = (gate: GateOperation) => gate.qubits.split(";").filter(Boolean).map(Number);
export const edgeKey = (a: number, b: number) => `${Math.min(a, b)}-${Math.max(a, b)}`;

/** The graph preserves unrounded weights. The separately shipped heatmap is rounded. */
export function matrixFromEdges(edges: GraphEdge[], qubits: number) {
  const matrix = Array.from({ length: qubits }, () => Array(qubits).fill(0));
  for (const edge of edges) matrix[edge.source][edge.target] = matrix[edge.target][edge.source] = edge.weight;
  return matrix;
}

/** Disjoint operations share a column; dependencies and recorded indices remain intact. */
export function compactCircuit(gates: GateOperation[], qubits: number) {
  const placed: Array<{ gate: GateOperation; column: number; localColumn: number }> = [];
  const bands: Array<{ layer: number; first: number; columns: number }> = [];
  let offset = 0;
  for (const layer of [...new Set(gates.map(g => g.layer_added))].sort((a, b) => a - b)) {
    const last = Array(qubits).fill(-1);
    for (const gate of gates.filter(g => g.layer_added === layer).sort((a, b) => a.operation_index - b.operation_index)) {
      const targets = gateTargets(gate), column = 1 + Math.max(...targets.map(q => last[q]));
      targets.forEach(q => { last[q] = column; });
      placed.push({ gate, column: offset + column, localColumn: column });
    }
    const columns = Math.max(...last) + 1;
    bands.push({ layer, first: offset, columns }); offset += columns;
  }
  return { placed, bands, columns: offset };
}

/** A bounded reading animation. This is NOT a physical gate execution schedule. */
export function gatePresentation(gates: GateOperation[], layer: number, segment: AudioSegment | null, time: number) {
  const ordered = [...gates].sort((a, b) => a.operation_index - b.operation_index);
  const past = ordered.filter(g => g.layer_added < layer).length;
  const current = ordered.filter(g => g.layer_added === layer);
  if (layer === 0) return { count: 0, referenceCount: 0, introductionSeconds: 0, latest: null };
  const introductionSeconds = segment ? Math.min(1.25, .35 * (segment.end_sec - segment.start_sec)) : 0;
  const progress = introductionSeconds > 0 ? Math.max(0, Math.min(1, (time - segment!.start_sec) / introductionSeconds)) : 1;
  const count = past + Math.min(current.length, Math.floor(progress * current.length + 1e-8));
  return { count, referenceCount: past + current.length, introductionSeconds, latest: ordered[count - 1] || null };
}

/** A schematic wire copies the mixed PCM, not an invented isolated quantum voice. */
export function wireWindow(signal: DecodedSignal | null, time: number, points = 160) {
  if (!signal) return [];
  const end = Math.max(0, Math.min(signal.left.length - 1, Math.floor(time * signal.sampleRate)));
  const samples = Math.round(signal.sampleRate * .032);
  const values = Array.from({ length: points }, (_, i) => {
    const index = end - samples + Math.floor(i * samples / (points - 1));
    return index < 0 ? 0 : (signal.left[index] + signal.right[index]) / 2;
  });
  const peak = Math.max(...values.map(Math.abs));
  return values.map(value => peak > 1e-8 ? value / peak : 0);
}

export function mappedVoice(descriptor: BlochDescriptor | null, metadata: SeedMetadata | null) {
  if (!descriptor) return null;
  const c = metadata?.audio_config;
  const neutral = descriptor.r <= (c?.bloch_direction_epsilon ?? 1e-8);
  const theta = neutral ? Math.PI / 2 : descriptor.theta;
  const phi = neutral ? Math.PI : descriptor.phi;
  const pan = ((phi % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI)) / (2 * Math.PI);
  const low = c?.frequency_min_hz ?? 110, high = c?.frequency_max_hz ?? 880;
  return { frequency: low * (high / low) ** Math.max(0, Math.min(1, theta / Math.PI)), leftPower: Math.cos(pan * Math.PI / 2) ** 2, rightPower: Math.sin(pan * Math.PI / 2) ** 2, amplitude: (c?.voice_gain ?? .22) * ((c?.amplitude_floor ?? .12) + (1 - (c?.amplitude_floor ?? .12)) * descriptor.r), purity: (1 + descriptor.r ** 2) / 2, neutral };
}

/** Kruskal in descending MI order. Root selection is deliberately absent. */
export function maximumForestTrace(matrix: number[][], tolerance: number) {
  const n = matrix.length;
  const candidates: GraphEdge[] = [];
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (matrix[i][j] > tolerance) candidates.push({ source: i, target: j, weight: matrix[i][j] });
  candidates.sort((a, b) => b.weight - a.weight || a.source - b.source || a.target - b.target);
  const parents = Array.from({ length: n }, (_, i) => i), kept: GraphEdge[] = [];
  const find = (q: number): number => parents[q] === q ? q : (parents[q] = find(parents[q]));
  const steps: Array<{ edge: GraphEdge; accepted: boolean; kept: GraphEdge[]; components: number }> = [];
  let components = n;
  for (const edge of candidates) {
    const a = find(edge.source), b = find(edge.target), accepted = a !== b;
    if (accepted) { parents[a] = b; kept.push(edge); components--; }
    steps.push({ edge, accepted, kept: [...kept], components });
    if (components === 1) break; // every remaining edge would create a cycle
  }
  return { candidates, steps, forest: kept, components, totalWeight: candidates.reduce((sum, e) => sum + e.weight, 0), forestWeight: kept.reduce((sum, e) => sum + e.weight, 0) };
}
