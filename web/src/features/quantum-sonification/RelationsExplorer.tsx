import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import type { GraphBackboneLayer, GraphEdge } from "./types";
import type { traversalMoment } from "./timeline";
import { edgeKey, maximumForestTrace, matrixFromEdges } from "./visualModels";
import { matrixColor } from "./colorScale";

const valueLabel = (x: number) => x !== 0 && Math.abs(x) < .001 ? x.toExponential(2) : x.toFixed(4);
type Pair = [number, number] | null;
type Props = { graph: GraphBackboneLayer | null; matrix: number[][] | null; reference: number[][] | null; layer: number; depth: number; n: number; root: number; tolerance: number; maximum: number; moment: ReturnType<typeof traversalMoment>; currentTime: number; selectedQubit: number; pair: Pair; onQubit: (q: number) => void; onPair: (pair: [number, number]) => void; pauseAudio: () => void; onInspection: (state: unknown) => void };

export function RelationsExplorer(p: Props & { referenceLayer: number; onReference: (layer: number) => void }) {
  const [view, setView] = useState<"route" | "matrix" | "delta">("route");
  const [network, setNetwork] = useState(false), [building, setBuilding] = useState(false), [step, setStep] = useState(0), [animating, setAnimating] = useState(false);
  const [logarithmic, setLogarithmic] = useState(false);
  const trace = useMemo(() => maximumForestTrace(p.graph?.allEdges ? matrixFromEdges(p.graph.allEdges, p.n) : p.matrix || [], p.tolerance), [p.graph, p.matrix, p.n, p.tolerance]);
  const referenceForest = p.graph?.forest || p.graph?.edges || [];
  const supplied = new Set(referenceForest.map(e => edgeKey(e.source, e.target)));
  const traceMatches = p.graph !== null && trace.forest.length === referenceForest.length && trace.forest.every(e => supplied.has(edgeKey(e.source, e.target)));
  const progress = trace.steps[step - 1] || null;
  const edges = building ? progress?.kept || [] : referenceForest;
  const background = network || (building && step < trace.steps.length) ? trace.candidates : [];
  const pairEdge = p.pair ? referenceForest.find(e => edgeKey(e.source, e.target) === edgeKey(...p.pair!)) : null;
  useEffect(() => { setStep(0); setAnimating(false); }, [p.layer]);
  useEffect(() => {
    if (!animating) return;
    const id = window.setInterval(() => setStep(old => { if (old >= trace.steps.length) { setAnimating(false); return old; } return old + 1; }), 480);
    return () => clearInterval(id);
  }, [animating, trace.steps.length]);
  useEffect(() => { p.onInspection({ view, logarithmic, global_mi_max_bits: p.maximum, delta_reference_layer: p.referenceLayer, network, construction_step: building ? step : null, algorithm: "Kruskal descending MI; root-independent", trace_matches_recorded_forest: traceMatches }); }, [view, logarithmic, p.maximum, p.referenceLayer, network, building, step, traceMatches]);
  const openConstruction = () => { p.pauseAudio(); setBuilding(!building); setNetwork(false); setStep(0); setAnimating(false); };
  const displayed = view === "delta" && p.matrix && p.reference ? p.matrix.map((row, i) => row.map((x, j) => x - p.reference![i][j])) : view === "matrix" ? p.matrix : null;
  const selectedValue = p.pair && p.matrix ? p.matrix[p.pair[0]][p.pair[1]] : null;
  return <section className="qs-panel qs-relations-panel" id="qs-relations">
    <div className="qs-section-heading"><div><div className="qs-kicker">Relaciones</div><h2>De la red al recorrido.</h2></div><div className="qs-mode-buttons" role="group" aria-label="Vista de relaciones">{[["route", "Bosque"], ["matrix", "MI"], ["delta", "ΔMI"]].map(([key, label]) => <button key={key} aria-pressed={view === key} onClick={() => { setView(key as typeof view); setAnimating(false); }}>{label}</button>)}</div></div>
    {view === "route" ? <>
      <div className="qs-graph-controls"><button className="qs-small-button" aria-pressed={network} disabled={!p.graph} onClick={() => { setNetwork(!network); setBuilding(false); setAnimating(false); }}>{network ? "Ver sólo el bosque" : "Ver red completa"}</button><button className="qs-text-button" aria-expanded={building} disabled={!traceMatches || !trace.steps.length} onClick={openConstruction}>{building ? "Cerrar construcción" : "Cómo se forma"}</button></div>
      {!p.graph ? <p className="qs-empty">El bosque registrado no está disponible; no se reconstruye un recorrido de audio.</p> : <NetworkView {...p} edges={edges} background={background} currentCandidate={building ? progress?.edge || null : null} rejected={building && progress ? !progress.accepted : false} building={building} network={network} />}
      {building && <div className="qs-construction"><div className="qs-build-heading"><strong>{step === 0 ? "Primero, todas las conexiones con MI sobre el umbral." : progress!.accepted ? `Elegimos q${progress!.edge.source}—q${progress!.edge.target}.` : `Saltamos q${progress!.edge.source}—q${progress!.edge.target}: cerraría un ciclo.`}</strong><span>{step}/{trace.steps.length} decisiones · {edges.length} conexiones elegidas</span></div><div className="qs-build-transport"><button className="qs-icon-button" aria-label="Arista anterior en la construcción" disabled={step === 0} onClick={() => { setAnimating(false); setStep(step - 1); }}><ChevronLeft size={16} /></button><button className="qs-icon-button" aria-label={animating ? "Pausar construcción" : "Animar construcción"} onClick={() => { if (step === trace.steps.length) setStep(0); setAnimating(!animating); }}>{animating ? <Pause size={16} /> : <Play size={16} />}</button><input aria-label="Paso de construcción del bosque" type="range" min={0} max={trace.steps.length} value={step} onChange={e => { setAnimating(false); setStep(Number(e.target.value)); }} /><button className="qs-icon-button" aria-label="Arista siguiente en la construcción" disabled={step === trace.steps.length} onClick={() => { setAnimating(false); setStep(step + 1); }}><ChevronRight size={16} /></button></div><p>Ordenamos por MI, de mayor a menor; unimos componentes sin formar ciclos. {progress && <>Peso de esta conexión: <b>{valueLabel(progress.edge.weight)} bits</b>. </>}{step === trace.steps.length && <>El resultado coincide con el bosque que usa este audio.</>}</p></div>}
      <div className="qs-graph-summary"><span>{network ? `${trace.candidates.length} conexiones de la red` : `${referenceForest.length} conexiones del bosque`} · {p.graph?.components?.length ?? trace.components} componentes</span><span>Peso elegido: {valueLabel(referenceForest.reduce((sum, e) => sum + e.weight, 0))} bits</span></div>
      <details className="qs-quiet-details"><summary>¿Por qué empieza en q{p.root}?</summary><p>q{p.root} es la raíz fijada en la configuración de esta muestra. No se elige por tener más MI ni es un origen físico privilegiado. Primero se obtiene el bosque de máximo peso; después la raíz organiza BFS y DFS. Las otras componentes, si existen, comienzan en su qubit de menor índice.</p><p>El algoritmo maximiza la suma de los pesos elegidos, no cada conexión de manera independiente. En una red desconectada el resultado es un bosque, no un único árbol. El dibujo muestra un calendario sonoro, no transporte físico de información.</p></details>
      {!building && <RouteStrip moment={p.moment} />}
    </> : <>
      <div className="qs-matrix-tools">{view === "delta" && <label>Comparar con capa<select aria-label="Capa de referencia MI" value={p.referenceLayer} onChange={e => p.onReference(Number(e.target.value))}>{Array.from({ length: p.depth + 1 }, (_, i) => <option key={i} value={i}>{i}</option>)}</select></label>}<label>Lectura<select aria-label="Contraste de matriz MI" value={logarithmic ? "log" : "linear"} onChange={e => setLogarithmic(e.target.value === "log")}><option value="linear">Lineal · magnitud</option><option value="log">Log · detalle débil</option></select></label><span>{view === "delta" ? `MI(${p.layer}) − MI(${p.referenceLayer})` : `MI de la capa ${p.layer}`}</span></div>
      <MatrixView matrix={displayed} maximum={p.maximum} signed={view === "delta"} logarithmic={logarithmic} pair={p.pair} onPair={p.onPair} />
    </>}
    {p.pair && selectedValue !== null && <div className="qs-pair-readout"><strong>q{p.pair[0]} ↔ q{p.pair[1]}</strong><span>MI actual <b>{valueLabel(selectedValue)} bits</b></span>{view === "delta" && p.reference && <span>Referencia <b>{valueLabel(p.reference[p.pair[0]][p.pair[1]])}</b> · Δ <b>{valueLabel(selectedValue - p.reference[p.pair[0]][p.pair[1]])} bits</b></span>}<span>{pairEdge ? "Elegida en el bosque" : "Fuera del bosque"}</span><div>{p.pair.map(q => <button key={q} className="qs-text-button" aria-pressed={p.selectedQubit === q} onClick={() => p.onQubit(q)}>Inspeccionar q{q}</button>)}</div></div>}
    <details className="qs-quiet-details"><summary>Qué expresa la MI y cómo leer los colores</summary><p>MI mide correlaciones entre un par de qubits, tanto clásicas como cuánticas. Más MI implica una conexión más pesada; no certifica entrelazamiento por sí sola. La matriz absoluta usa una escala secuencial: más brillo significa más MI. En ΔMI, azul significa disminución, ámbar aumento y el neutro representa cero.</p><p>Los límites se mantienen fijos entre capas. La lectura logarítmica amplifica diferencias débiles sin cambiar sus valores: referencia 1e−6 bits. La matriz es simétrica; cada par aparece dos veces, pero la suma de MI cuenta cada par una sola vez. Los colores son convenciones de lectura, no clases de estados cuánticos.</p></details>
  </section>;
}

function NetworkView(p: Props & { edges: GraphEdge[]; background: GraphEdge[]; currentCandidate: GraphEdge | null; rejected: boolean; building: boolean; network: boolean }) {
  const referenceEdges = p.graph?.forest || p.graph?.edges || [];
  const nodes = referenceEdges.length && p.graph?.layout ? p.graph.layout : Array.from({ length: p.n }, (_, qubit) => ({ qubit, x: 62 + (qubit % 5) * 96, y: 65 + Math.floor(qubit / 5) * 118, parent: null, depth: 0 }));
  const positions = new Map(nodes.map(node => [node.qubit, node]));
  const candidateMax = Math.max(1e-12, ...p.background.map(e => e.weight));
  const activity = new Set(p.building ? [] : p.moment.active.flatMap(item => item.event.edges.map(e => edgeKey(e.source, e.target))));
  const renderEdge = (edge: GraphEdge, background: boolean, candidate = false) => {
    let a = positions.get(edge.source), b = positions.get(edge.target); if (!a || !b) return null;
    if (a.parent === b.qubit) [a, b] = [b, a];
    const selected = p.pair && edgeKey(edge.source, edge.target) === edgeKey(...p.pair);
    const active = activity.has(edgeKey(edge.source, edge.target));
    return <g key={`${background ? "bg" : candidate ? "candidate" : "kept"}-${edgeKey(edge.source, edge.target)}`} className="qs-network-edge" data-pair={edgeKey(edge.source, edge.target)}><line className={background ? "qs-mi-network-edge" : candidate ? "qs-candidate-edge" : "qs-kept-edge"} data-selected={selected} data-rejected={candidate && p.rejected} x1={a.x} y1={a.y} x2={b.x} y2={b.y} style={background ? { opacity: .14 + .45 * edge.weight / candidateMax } : undefined} />{active && !background && <line className="qs-route-flow" x1={a.x} y1={a.y} x2={b.x} y2={b.y} strokeDasharray="6 13" strokeDashoffset={-p.currentTime * 34} />}<line className="qs-edge-hit" x1={a.x} y1={a.y} x2={b.x} y2={b.y} role="button" tabIndex={selected ? 0 : -1} aria-label={`MI entre q${edge.source} y q${edge.target}: ${valueLabel(edge.weight)} bits`} onClick={() => p.onPair([edge.source, edge.target])} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); p.onPair([edge.source, edge.target]); } }}><title>{`q${edge.source} ↔ q${edge.target} · ${valueLabel(edge.weight)} bits`}</title></line>{(selected || candidate) && <text className="qs-edge-value" x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 7} textAnchor="middle">{valueLabel(edge.weight)} bits</text>}</g>;
  };
  return <div className="qs-network"><svg viewBox="0 0 525 440" role="group" aria-label={p.building ? "Selección de conexiones por Kruskal" : p.network ? "Red completa de información mutua con el bosque destacado" : "Bosque máximo del audio"}>
    {p.background.map(edge => renderEdge(edge, true))}{p.edges.map(edge => renderEdge(edge, false))}{p.currentCandidate && renderEdge(p.currentCandidate, false, true)}
    {nodes.map(node => <g key={node.qubit} className="qs-forest-node" data-root={node.qubit === p.root} data-active={!p.building && p.moment.activeNodes.includes(node.qubit)} data-selected={p.selectedQubit === node.qubit || p.pair?.includes(node.qubit)}><circle cx={node.x} cy={node.y} r={18} />{node.qubit === p.root && <circle className="qs-root-ring" cx={node.x} cy={node.y} r={23} />}<text x={node.x} y={node.y + 4} textAnchor="middle">q{node.qubit}</text><foreignObject x={node.x - 23} y={node.y - 23} width={46} height={46}><button aria-label={`Seleccionar q${node.qubit} en la red`} onClick={() => p.onQubit(node.qubit)} /></foreignObject></g>)}
  </svg><p className="qs-chart-note">{p.network ? "Red: todas las conexiones sobre el umbral. Ámbar: las elegidas en el bosque; fondo gris: las demás." : p.building ? "Ámbar: conexiones elegidas. Azul discontinuo: candidata descartada por ciclo. La raíz no decide qué aristas entran." : `Raíz q${p.root} · pulsa un nodo para conectar circuito, estado local y señal.`} Posiciones fijas para comparar. La construcción usa los pesos precisos del grafo; la matriz web se entrega redondeada.</p></div>;
}

function MatrixView({ matrix, maximum, signed, logarithmic, pair, onPair }: { matrix: number[][] | null; maximum: number; signed: boolean; logarithmic: boolean; pair: Pair; onPair: (pair: [number, number]) => void }) {
  const [focus, setFocus] = useState<[number, number]>([0, 1]);
  const ref = useRef<HTMLDivElement>(null);
  if (!matrix) return <p className="qs-empty">Esta matriz no está disponible.</p>;
  const n = matrix.length;
  const maximumLabel = valueLabel(maximum);
  const samples = Array.from({ length: 21 }, (_, i) => matrixColor(signed ? maximum * (i / 10 - 1) : maximum * i / 20, maximum, signed, logarithmic));
  return <div className="qs-matrix-view"><div className="qs-matrix-grid qs-labeled-matrix" ref={ref} role="grid" aria-label={signed ? "Cambio de MI entre pares" : "MI absoluta entre pares"} style={{ gridTemplateColumns: `24px repeat(${n},minmax(0,1fr))` }}><span className="qs-matrix-axis">q</span>{matrix.map((_, j) => <span className="qs-matrix-axis" key={`col-${j}`}>{j}</span>)}{matrix.map((row, i) => <div key={i} role="row" className="qs-matrix-row"><span className="qs-matrix-axis">{i}</span>{row.map((value, j) => <button key={j} data-matrix-cell={`${i}-${j}`} data-selected={pair && edgeKey(...pair) === edgeKey(i, j)} role="gridcell" disabled={i === j} tabIndex={focus[0] === i && focus[1] === j ? 0 : -1} title={i === j ? "Diagonal excluida del análisis por pares" : `q${i} ↔ q${j}: ${valueLabel(value)} bits`} aria-label={`${signed ? "Delta MI" : "MI"} q${i}, q${j}: ${valueLabel(value)} bits`} style={{ background: matrixColor(value, maximum, signed, logarithmic) }} onFocus={() => setFocus([i, j])} onClick={() => onPair([i, j])} onKeyDown={e => {
        const delta: Record<string, [number, number]> = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }; if (!delta[e.key]) return; e.preventDefault();
        const [di, dj] = delta[e.key]; let a = Math.max(0, Math.min(n - 1, i + di)), b = Math.max(0, Math.min(n - 1, j + dj));
        if (a === b) { a = Math.max(0, Math.min(n - 1, a + di)); b = Math.max(0, Math.min(n - 1, b + dj)); }
        if (a === b) return; setFocus([a, b]); (ref.current?.querySelector(`[data-matrix-cell="${a}-${b}"]`) as HTMLButtonElement)?.focus();
      }}>{pair && edgeKey(...pair) === edgeKey(i, j) && <span>•</span>}</button>)}</div>)}</div><div className="qs-color-legend"><div style={{ background: `linear-gradient(90deg,${samples.join(",")})` }} /><div><span>{signed ? `−${maximumLabel}` : "0"}</span><span>{signed ? "0" : "MI"}</span><span>{signed ? "+" : ""}{maximumLabel} bits</span></div><p>{signed ? "Azul: disminuye · neutro: sin cambio · ámbar: aumenta" : "Oscuro: menor MI · claro: mayor MI"}. {logarithmic ? "Contraste logarítmico; referencia fija 1e−6 bits; amplificación visual." : "Lectura lineal."} Límites globales fijos.</p></div></div>;
}

function RouteStrip({ moment }: { moment: ReturnType<typeof traversalMoment> }) {
  return <details className="qs-quiet-details qs-route-summary"><summary>Ver el orden sonoro</summary>{moment.schedules.map(schedule => <div key={schedule.branch}><strong>{schedule.branch.toUpperCase()}</strong><div>{schedule.events.map((event, i) => <span className="qs-route-token" key={i} data-active={moment.active.some(item => item.branch === schedule.branch && item.index === i)}>{event.kind === "sound" ? `[${event.nodes.map(q => `q${q}`).join(" + ")}]` : "pausa"}</span>)}</div></div>)}</details>;
}
