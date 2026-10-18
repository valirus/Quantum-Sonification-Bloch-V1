export type SonificationMode = "bfs" | "dfs" | "mix";

export interface SonificationManifest {
  version: string;
  dataset: string;
  audioBaseUrl?: string;
  seeds: SonificationSeedAsset[];
}

export interface SonificationSeedAsset {
  id: string;
  seed: number | null;
  label: string;
  kind?: "illustrative";
  dataset?: string;
  dataset_version?: string;
  lesson?: {
    question: string;
    steps: Array<{ layer: number; label: string; caption: string; target_probability: number | null }>;
    target_bitstring: string | null;
    validation: Array<{ name: string; value: number; analytic?: number }>;
    statement: string;
  };
  metadata: string;
  layerMetrics: string;
  blochDescriptors: string;
  gateManifest: string;
  graphBackbones?: string;
  miMatrices?: string;
  audioAnalysis?: string;
  segments: Partial<Record<SonificationMode, string>>;
  audio: Partial<Record<SonificationMode, string>>;
}

export interface SeedMetadata {
  scientific_scope?: string;
  num_qubits?: number;
  layers?: number;
  seed?: number | null;
  preferred_root?: number;
  edge_tolerance?: number;
  mapping?: Record<string, string>;
  renderer_sha256?: string;
  state_resolution?: string;
  audio_config?: {
    sample_rate?: number;
    frequency_min_hz?: number;
    frequency_max_hz?: number;
    bloch_direction_epsilon?: number;
    amplitude_floor?: number;
    voice_gain?: number;
  };
}

export interface LayerMetric {
  layer: number;
  mean_bloch_radius: number;
  mean_von_neumann_entropy: number;
  central_cut_entanglement_entropy_normalized: number;
  total_mutual_information: number;
  positive_edge_density: number;
  backbone_edges: number;
  backbone_components: number;
}

export interface BlochDescriptor {
  layer: number;
  qubit: number;
  x: number;
  y: number;
  z: number;
  theta: number;
  phi: number;
  r: number;
  linear_entropy: number;
  von_neumann_entropy: number;
}

export interface GateOperation {
  layer_added: number;
  operation_index: number;
  gate_label: string;
  qubits: string;
}

export interface GateMoment {
  index: number;
  label: string;
  qubits: number[];
  layer: number;
  time: number;
  intervalStart: number;
  intervalEnd: number;
}

export interface AudioSegment {
  layer: number;
  start_sec: number;
  end_sec: number;
}

export interface SonificationData {
  warnings: string[];
  manifest: SonificationManifest;
  seed: SonificationSeedAsset;
  metadata: SeedMetadata | null;
  layers: LayerMetric[];
  bloch: BlochDescriptor[];
  gates: GateOperation[];
  segments: Partial<Record<SonificationMode, AudioSegment[]>>;
  graphBackbones: GraphBackboneDataset | null;
  miMatrices: MutualInformationDataset | null;
  audioAnalysis: Partial<Record<SonificationMode, AudioAnalysis>>;
}

export interface AudioAnalysis {
  sampleRate: number;
  duration: number;
  waveform: number[];
  spectrum: {
    rows: number;
    cols: number;
    values: number[];
  };
}

export interface GraphBackboneDataset {
  root: number;
  layers: GraphBackboneLayer[];
}

export interface GraphBackboneLayer {
  layer: number;
  allEdges?: GraphEdge[];
  forest?: GraphEdge[];
  edges: GraphEdge[];
  components?: number[][];
  layout?: GraphLayoutNode[];
  events?: {
    bfs: GraphAudioEvent[];
    dfs: GraphAudioEvent[];
  };
  bfs: GraphTraversalNode[];
  dfs: GraphTraversalNode[];
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
}

export interface GraphTraversalNode {
  qubit: number;
  depth: number;
  parent: number | null;
  weight: number;
}

export interface GraphLayoutNode {
  qubit: number;
  x: number;
  y: number;
  depth: number;
  parent: number | null;
  incomingWeight: number | null;
}

export interface GraphAudioEvent {
  kind: "sound" | "silence";
  nodes: number[];
  edges: Array<Pick<GraphEdge, "source" | "target">>;
  depth: number | null;
  incomingMi: number | null;
  start: number;
  end: number;
}

export interface MutualInformationDataset {
  layers: MutualInformationLayer[];
}

export interface MutualInformationLayer {
  layer: number;
  matrix: number[][];
}
