import { useState } from "react";
import type { LayerMetric } from "./types";

export function QuantumSummary({ metrics, layer, qubits }: { metrics: LayerMetric[]; layer: number; qubits: number }) {
  const [focus, setFocus] = useState<"radius" | "mi" | "cut">("radius");
  const current = metrics.find(row => row.layer === layer);
  if (!current) return null;
  const cutMaximum = Math.floor(qubits / 2);
  const definitions = {
    radius: { label: "Radio local medio", value: current.mean_bloch_radius, unit: "", maximum: 1, get: (r: LayerMetric) => r.mean_bloch_radius, explanation: "r mide el tamaño del vector de Bloch. Cada voz usa su propio radio para la amplitud; la pureza local se obtiene con P=(1+r²)/2." },
    mi: { label: "MI total entre pares", value: current.total_mutual_information, unit: "bits", maximum: Math.max(1e-12, ...metrics.map(r => r.total_mutual_information)), get: (r: LayerMetric) => r.total_mutual_information, explanation: "Suma I(i:j) una vez por par. Sus pesos organizan el bosque y la duración de las voces; no es una medida completa del entrelazamiento del sistema." },
    cut: { label: "Entropía del corte central", value: current.central_cut_entanglement_entropy_normalized * cutMaximum, unit: "bits", maximum: cutMaximum, get: (r: LayerMetric) => r.central_cut_entanglement_entropy_normalized * cutMaximum, explanation: "Describe una bipartición del estado global. Puede crecer mientras el radio local y la MI por pares disminuyen. Es referencia cuántica y no controla directamente el audio." },
  };
  const chosen = definitions[focus];
  const ordered = [...metrics].sort((a, b) => a.layer - b.layer), depth = ordered.at(-1)!.layer;
  return <section className="qs-panel qs-quantum-summary" aria-label="Interpretación conjunta de parámetros"><div className="qs-parameter-cards">{(["radius", "mi", "cut"] as const).map(key => <button key={key} aria-label={`Interpretar ${definitions[key].label}`} aria-pressed={focus === key} onClick={() => setFocus(key)}><span>{definitions[key].label}</span><strong>{definitions[key].value.toFixed(3)} <small>{definitions[key].unit}</small></strong></button>)}</div><div className="qs-parameter-reading"><p>{chosen.explanation}</p><svg viewBox="0 0 270 80" role="img" aria-label={`${chosen.label} por capa, con límites fijos`}><line x1={31} x2={255} y1={54} y2={54} /><text x={2} y={13}>{chosen.maximum.toFixed(focus === "mi" ? 1 : 0)}</text><text x={18} y={57}>0</text><polyline points={ordered.map(r => `${32 + r.layer / Math.max(1, depth) * 220},${54 - chosen.get(r) / chosen.maximum * 43}`).join(" ")} />{ordered.map(r => <circle key={r.layer} data-current={r.layer === layer} cx={32 + r.layer / Math.max(1, depth) * 220} cy={54 - chosen.get(r) / chosen.maximum * 43} r={r.layer === layer ? 3 : 1.6} />)}<text x={30} y={76}>L0</text><text x={224} y={76}>L{depth}</text></svg></div></section>;
}
