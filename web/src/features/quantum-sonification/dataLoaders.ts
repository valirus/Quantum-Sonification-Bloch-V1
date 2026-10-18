import Papa from "papaparse";
import type { AudioSegment, BlochDescriptor, GateOperation, GraphBackboneDataset, LayerMetric, MutualInformationDataset, SeedMetadata, SonificationData, SonificationManifest, SonificationMode } from "./types";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`No se pudo cargar ${path}: HTTP ${response.status}`);
  return response.json() as Promise<T>;
}

function number(row: Record<string, string>, key: string): number {
  if (row[key] === undefined || row[key].trim() === "") throw new Error(`Falta el valor ${key}; no se sustituye por cero.`);
  const value = Number(row[key]);
  if (!Number.isFinite(value)) throw new Error(`Valor inválido en ${key}`);
  return value;
}

async function csv<T>(path: string, map: (row: Record<string, string>) => T): Promise<T[]> {
  if (!path) throw new Error("Falta una ruta de datos en el manifiesto.");
  const response = await fetch(path);
  if (!response.ok) throw new Error(`No se pudo cargar ${path}: HTTP ${response.status}`);
  const parsed = Papa.parse<Record<string, string>>(await response.text(), { header: true, skipEmptyLines: true });
  if (parsed.errors.length) throw new Error(`CSV inválido en ${path}: ${parsed.errors[0].message}`);
  return parsed.data.map(map);
}

export async function loadSonificationManifest() {
  const manifest = await fetchJson<SonificationManifest>("/sonification/manifest.json");
  if (!manifest.seeds?.length) throw new Error("El manifiesto no contiene muestras precargadas.");
  const response = await fetch("/sonification/examples_manifest.json");
  if (response.status === 404) return manifest;
  if (!response.ok) throw new Error(`No se pudo cargar la colección didáctica: HTTP ${response.status}`);
  const examples = await response.json() as SonificationManifest;
  if (!Array.isArray(examples.seeds) || examples.seeds.some(s => s.kind !== "illustrative" || !s.lesson || s.seed !== null)) throw new Error("La colección didáctica no declara su procedencia.");
  const seeds = [...manifest.seeds, ...examples.seeds.map(seed => ({ ...seed, dataset_version: examples.version }))];
  if (new Set(seeds.map(s => s.id)).size !== seeds.length) throw new Error("Identificador de muestra duplicado entre colecciones.");
  return { ...manifest, seeds };
}

export async function loadSonificationData(seedId?: string, providedManifest?: SonificationManifest): Promise<SonificationData> {
  const manifest = providedManifest || await loadSonificationManifest();
  const seed = seedId ? manifest.seeds.find(item => item.id === seedId) : manifest.seeds[0];
  if (!seed) throw new Error("La muestra seleccionada no existe en el manifiesto.");
  const warnings: string[] = [];
  const optionalJson = async <T>(path: string | undefined, label: string): Promise<T | null> => {
    if (!path) { warnings.push(`${label}: no suministrado.`); return null; }
    try { return await fetchJson<T>(path); }
    catch (error) { warnings.push(`${label}: ${error instanceof Error ? error.message : String(error)}`); return null; }
  };
  const [metadata, layers, bloch, gates, graphBackbones, miMatrices, audioAnalysis] = await Promise.all([
    fetchJson<SeedMetadata>(seed.metadata),
    csv<LayerMetric>(seed.layerMetrics, row => ({ layer: number(row, "layer"), mean_bloch_radius: number(row, "mean_bloch_radius"), mean_von_neumann_entropy: number(row, "mean_von_neumann_entropy"), central_cut_entanglement_entropy_normalized: number(row, "central_cut_entanglement_entropy_normalized"), total_mutual_information: number(row, "total_mutual_information"), positive_edge_density: number(row, "positive_edge_density"), backbone_edges: number(row, "backbone_edges"), backbone_components: number(row, "backbone_components") })),
    csv<BlochDescriptor>(seed.blochDescriptors, row => ({ layer: number(row, "layer"), qubit: number(row, "qubit"), x: number(row, "x"), y: number(row, "y"), z: number(row, "z"), theta: number(row, "theta"), phi: number(row, "phi"), r: number(row, "r"), linear_entropy: number(row, "linear_entropy"), von_neumann_entropy: number(row, "von_neumann_entropy") })),
    csv<GateOperation>(seed.gateManifest, row => ({ layer_added: number(row, "layer_added"), operation_index: number(row, "operation_index"), gate_label: row.gate_label || row.gate_name || "?", qubits: row.qubits || "" })),
    optionalJson<GraphBackboneDataset>(seed.graphBackbones, "Bosque"),
    optionalJson<MutualInformationDataset>(seed.miMatrices, "Matrices MI"),
    optionalJson<SonificationData["audioAnalysis"]>(seed.audioAnalysis, "Análisis histórico"),
  ]);
  if (!Number.isInteger(metadata.num_qubits) || !Number.isInteger(metadata.layers) || !metadata.num_qubits || metadata.layers! < 0) throw new Error("Los metadatos no declaran qubits y capas válidos.");
  const n = metadata.num_qubits!, depth = metadata.layers!;
  const orderedGates = [...gates].sort((a, b) => a.operation_index - b.operation_index);
  if (depth > 0 && !orderedGates.length) throw new Error("El registro de compuertas está vacío para un circuito con capas.");
  orderedGates.forEach((gate, index) => {
    const targets = gate.qubits.split(";").filter(Boolean).map(Number);
    if (gate.operation_index !== index) throw new Error(`Orden de compuertas inválido en operación ${gate.operation_index}.`);
    if (!Number.isInteger(gate.layer_added) || gate.layer_added < 1 || gate.layer_added > depth || targets.some(q => !Number.isInteger(q) || q < 0 || q >= n)) throw new Error(`Capa o qubit inválido en operación ${index}.`);
    const label = gate.gate_label.toLowerCase();
    const expected = seed.kind === "illustrative" ? ({ h: 1, x: 1, cx: 2, ccz: 3 } as Record<string, number>)[label] : label === "fsim" ? 2 : 1;
    if (!expected || targets.length !== expected || new Set(targets).size !== expected) throw new Error(`Destinos de compuerta inválidos en operación ${index}.`);
  });
  for (let layer = 0; layer <= depth; layer += 1) {
    if (layers.filter(item => item.layer === layer).length !== 1) throw new Error(`Métrica ausente o duplicada en capa ${layer}.`);
    const descriptors = bloch.filter(item => item.layer === layer);
    if (descriptors.length !== n || new Set(descriptors.map(item => item.qubit)).size !== n || descriptors.some(item => item.qubit < 0 || item.qubit >= n || item.r < -1e-8 || item.r > 1 + 1e-8)) throw new Error(`Descriptores Bloch incompletos o inválidos en capa ${layer}.`);
    if (descriptors.some(item => Math.abs(Math.hypot(item.x, item.y, item.z) - item.r) > 1e-6)) throw new Error(`El radio de Bloch no coincide con sus coordenadas en capa ${layer}.`);
  }
  const segments: SonificationData["segments"] = {};
  await Promise.all((["bfs", "dfs", "mix"] as SonificationMode[]).map(async mode => {
    if (!seed.segments[mode]) return;
    const rows = await csv<AudioSegment>(seed.segments[mode]!, row => ({ layer: number(row, "layer"), start_sec: number(row, "start_sec"), end_sec: number(row, "end_sec") }));
    rows.sort((a, b) => a.start_sec - b.start_sec);
    rows.forEach((row, i) => {
      if (row.start_sec < 0 || row.end_sec <= row.start_sec || !Number.isInteger(row.layer) || row.layer < 0 || row.layer > depth || (i && row.start_sec < rows[i - 1].end_sec - 1e-6)) throw new Error(`Segmentos ${mode.toUpperCase()} inválidos o solapados.`);
    });
    segments[mode] = rows;
  }));
  if (!segments.bfs?.length && !segments.dfs?.length && !segments.mix?.length) throw new Error("Falta el calendario de las capas de audio.");
  for (const layer of miMatrices?.layers || []) {
    if (layer.matrix.length !== n || layer.matrix.some(row => row.length !== n || row.some(value => !Number.isFinite(value)))) throw new Error(`Matriz MI inválida en capa ${layer.layer}.`);
    if (layer.matrix.some((row, i) => row.some((value, j) => value < -1e-8 || Math.abs(value - layer.matrix[j][i]) > 1e-8 || (i === j && Math.abs(value) > 1e-8)))) throw new Error(`La matriz MI debe ser simétrica, no negativa y con diagonal cero en capa ${layer.layer}.`);
  }
  return { manifest, seed, metadata, layers, bloch, gates, graphBackbones, miMatrices, audioAnalysis: audioAnalysis || {}, segments, warnings };
}

export function getAudioUrl(seed: SonificationData["seed"], mode: SonificationMode, audioBaseUrl?: string) {
  if (seed.audio[mode]) return seed.audio[mode]!;
  if (!audioBaseUrl) return "";
  return `${audioBaseUrl.replace(/\/$/, "")}/${seed.id}/${mode === "mix" ? "combined" : mode}_continuous.opus`;
}
