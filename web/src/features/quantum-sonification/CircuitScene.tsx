import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { AudioSegment, GateOperation, SonificationData } from "./types";
import type { DecodedSignal } from "./signalMath";
import { compactCircuit, gatePresentation, gateTargets, wireWindow } from "./visualModels";

export function CircuitScene({ data, layer, segment, currentTime, signal, activeNodes, selectedQubit, inspectedGate, playing, onQubit, onGate, onInspection }: {
  data: SonificationData; layer: number; segment: AudioSegment | null; currentTime: number; signal: DecodedSignal | null; activeNodes: number[]; selectedQubit: number; inspectedGate: number | null; playing: boolean; onQubit: (q: number) => void; onGate: (gate: GateOperation) => void; onInspection: (state: unknown) => void;
}) {
  const n = data.metadata!.num_qubits!;
  const layout = useMemo(() => compactCircuit(data.gates, n), [data.gates, n]);
  const presentation = gatePresentation(data.gates, layer, segment, currentTime);
  const [complete, setComplete] = useState(false), [follow, setFollow] = useState(true);
  const scroll = useRef<HTMLDivElement>(null);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const columnWidth = 54, height = 70 + n * 31, width = Math.max(760, 34 + layout.columns * columnWidth);
  const shown = layout.placed.filter(item => complete || item.gate.operation_index < presentation.count);
  const selected = shown.find(item => item.gate.operation_index === inspectedGate)?.gate || presentation.latest;
  const selectedIndex = shown.findIndex(item => item.gate.operation_index === selected?.operation_index);
  const waveform = reduced ? [] : wireWindow(signal, currentTime);
  useEffect(() => { onInspection({ display: complete ? "complete_record" : "progressive", follow_layer: follow, shown_operations: shown.length, visual_introduction_seconds: presentation.introductionSeconds, columns: layout.columns, timing: "reading presentation; no per-gate quantum states", strings: "normalized actual mixed PCM; no isolated voices" }); }, [complete, follow, shown.length, presentation.introductionSeconds, layout.columns]);
  useEffect(() => {
    if (!follow || !scroll.current) return;
    const element = scroll.current;
    const band = layout.bands.find(item => item.layer === layer);
    const x = (band?.first || 0) * columnWidth;
    const center = () => element.scrollTo({ left: Math.max(0, x - element.clientWidth * .4), behavior: reduced ? "auto" : "smooth" });
    center();
    const resize = new ResizeObserver(center);
    resize.observe(element);
    return () => resize.disconnect();
  }, [follow, layer, layout, reduced]);
  const inspectAdjacent = (delta: number) => {
    const next = shown[Math.max(0, Math.min(shown.length - 1, selectedIndex + delta))];
    if (next) onGate(next.gate);
  };
  return <section className="qs-panel qs-circuit-panel" id="qs-circuit">
    <div className="qs-section-heading"><div><div className="qs-kicker">Circuito</div><h2>La capa se construye ante tus ojos.</h2><p className="qs-muted">Columnas compactas; los números conservan el orden de las operaciones.</p></div><button className="qs-small-button" aria-pressed={complete} onClick={() => setComplete(!complete)}>{complete ? "Volver al avance" : "Ver registro completo"}</button></div>
    <div className="qs-circuit-tools"><span className="qs-presentation-status" aria-live="off">{complete ? `${data.gates.length} operaciones registradas` : `${presentation.count} / ${presentation.referenceCount} puertas presentadas · capa ${layer}`}</span><button className="qs-text-button" aria-pressed={follow} onClick={() => setFollow(!follow)}>{follow ? "Seguir capa" : "Vista libre"}</button></div>
    <div className="qs-circuit-frame"><div className="qs-circuit-labels" style={{ height }}><span>qubit</span>{Array.from({ length: n }, (_, q) => <button key={q} aria-label={`Inspeccionar qubit ${q}`} aria-pressed={q === selectedQubit} style={{ top: 36 + q * 31 }} onClick={() => onQubit(q)}>q{q}</button>)}</div>
      <div className="qs-circuit-scroll" ref={scroll} onWheel={event => { if (Math.abs(event.deltaX) > .1 || event.shiftKey) setFollow(false); }}><svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Circuito progresivo; presentación del orden, no estados por compuerta">
        {layout.bands.map(band => <g key={band.layer}><rect className="qs-circuit-band" data-current={band.layer === layer} x={12 + band.first * columnWidth} y={3} width={band.columns * columnWidth - 3} height={height - 10} rx={4} /><text className="qs-svg-text qs-layer-title" data-future={band.layer > layer} x={19 + band.first * columnWidth} y={22}>L{String(band.layer).padStart(2, "0")}</text></g>)}
        {Array.from({ length: n }, (_, q) => {
          const y = 50 + q * 31, active = activeNodes.includes(q);
          const x0 = 14 + (layout.bands.find(b => b.layer === layer)?.first || 0) * columnWidth;
          const x1 = Math.min(width - 5, x0 + Math.max(150, (layout.bands.find(b => b.layer === layer)?.columns || 2) * columnWidth));
          const points = waveform.map((value, i) => `${x0 + i / Math.max(1, waveform.length - 1) * (x1 - x0)},${y - value * 7}`).join(" ");
          return <g key={q}><line className="qs-rail" data-selected={selectedQubit === q} x1={8} x2={width - 8} y1={y} y2={y} />{active && <polyline className="qs-wire-wave" data-qubit={q} data-playing={playing} points={points || `${x0},${y} ${x1},${y}`} />}</g>;
        })}
        {shown.map(({ gate, column }) => {
          const qs = gateTargets(gate), x = 25 + column * columnWidth, y = 50 + Math.min(...qs) * 31, h = (Math.max(...qs) - Math.min(...qs)) * 31 + 24;
          const current = gate.operation_index === presentation.latest?.operation_index && !complete && presentation.count < presentation.referenceCount;
          return <g key={gate.operation_index} className="qs-gate qs-progressive-gate" data-operation={gate.operation_index} data-selected={gate.operation_index === inspectedGate} data-newest={current} data-fsim={gate.gate_label.toLowerCase() === "fsim"} data-multiqubit={qs.length > 1} role="button" tabIndex={gate.operation_index === (selected?.operation_index ?? shown[0]?.gate.operation_index) ? 0 : -1} aria-label={`Operación ${gate.operation_index + 1}: ${gate.gate_label} en ${qs.map(q => `q${q}`).join(" y ")}`} onClick={() => onGate(gate)} onKeyDown={e => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onGate(gate); }
            else if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); const index = shown.findIndex(item => item.gate.operation_index === gate.operation_index); const next = shown[Math.max(0, Math.min(shown.length - 1, index + (e.key === "ArrowRight" ? 1 : -1)))]; if (next) { onGate(next.gate); (e.currentTarget.parentElement?.querySelector(`[data-operation="${next.gate.operation_index}"]`) as SVGElement)?.focus(); } }
          }}><rect x={x} y={y - 12} width={32} height={h} rx={3} /><text x={x + 16} y={y + (h - 24) / 2 + 4} textAnchor="middle">{gate.gate_label}</text><text className="qs-operation-index" x={x - 4} y={y - 7} textAnchor="end">{gate.operation_index + 1}</text></g>;
        })}
      </svg></div>
    </div>
    <div className="qs-gate-readout"><button className="qs-icon-button" aria-label="Inspeccionar operación anterior" disabled={selectedIndex <= 0} onClick={() => inspectAdjacent(-1)}><ChevronLeft size={16} /></button><span>{selected ? <><strong>OP {selected.operation_index + 1} · {selected.gate_label}</strong> · {gateTargets(selected).map(q => `q${q}`).join(" ↔ ")} · capa {selected.layer_added}</> : "Estado inicial · ninguna compuerta presentada"}</span><button className="qs-icon-button" aria-label="Inspeccionar operación siguiente" disabled={selectedIndex < 0 || selectedIndex >= shown.length - 1} onClick={() => inspectAdjacent(1)}><ChevronRight size={16} /></button></div>
    <details className="qs-quiet-details"><summary>Cómo leer esta animación</summary><p>Las compuertas de una capa aparecen en su orden registrado durante una breve introducción visual. Avanzar o retroceder el cursor vuelve a calcular esa presentación. El audio y el vector de Bloch corresponden al estado registrado al terminar el bloque. La aparición animada no añade estados entre esos registros.</p><p>Operaciones sobre qubits disjuntos comparten columna porque no dependen unas de otras. Las cuerdas resaltan qubits del calendario sonoro y copian la forma del PCM mezclado, amplificada para su lectura. No son voces aisladas ni una vibración física del qubit.</p></details>
  </section>;
}
