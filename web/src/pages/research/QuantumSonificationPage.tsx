import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Atom, Download, Pause, Play, RotateCcw, Volume2 } from "lucide-react";
import { getAudioUrl, loadSonificationData, loadSonificationManifest } from "@/features/quantum-sonification/dataLoaders";
import { SignalWorkbench, downloadJson } from "@/features/quantum-sonification/SignalWorkbench";
import { CircuitScene } from "@/features/quantum-sonification/CircuitScene";
import { RelationsExplorer } from "@/features/quantum-sonification/RelationsExplorer";
import { QuantumSummary } from "@/features/quantum-sonification/QuantumSummary";
import { gateTargets, mappedVoice } from "@/features/quantum-sonification/visualModels";
import { clamp, peakEnvelope } from "@/features/quantum-sonification/signalMath";
import { useDecodedSignal } from "@/features/quantum-sonification/useDecodedSignal";
import { segmentAt, traversalMoment } from "@/features/quantum-sonification/timeline";
import type { AudioSegment, BlochDescriptor, GateOperation, SeedMetadata, SonificationData, SonificationManifest, SonificationMode } from "@/features/quantum-sonification/types";
import "@/features/quantum-sonification/quantum-sonification.css";
import "@/features/quantum-sonification/experience-v2.css";
import "@/features/quantum-sonification/examples.css";
import { ExampleLesson } from "@/features/quantum-sonification/ExampleLesson";

const number = (value: number | undefined, digits = 3) => value === undefined || !Number.isFinite(value) ? "—" : value.toFixed(digits);
const timeLabel = (seconds: number) => `${Math.floor(Math.max(0, seconds) / 60).toString().padStart(2, "0")}:${(Math.max(0, seconds) % 60).toFixed(1).padStart(4, "0")}`;
const miLabel = (value: number) => Math.abs(value) < 0.001 && value !== 0 ? value.toExponential(2) : value.toFixed(4);


export default function QuantumSonificationPage() {
  const [manifest, setManifest] = useState<SonificationManifest | null>(null);
  const [seedId, setSeedId] = useState("");
  const [data, setData] = useState<SonificationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [mode, setMode] = useState<SonificationMode>("bfs");
  const [layer, setLayer] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [mediaDuration, setMediaDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.65);
  const [loopLayer, setLoopLayer] = useState(false);
  const [loopWhole, setLoopWhole] = useState(false);
  const [selectedQubit, setSelectedQubit] = useState(7);
  const [selectedPair, setSelectedPair] = useState<[number, number] | null>(null);
  const [referenceLayer, setReferenceLayer] = useState(0);

  const [inspectedGate, setInspectedGate] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const pendingSeek = useRef(0);
  const changingSource = useRef(false);
  const inspectionRef = useRef<unknown>(null);
  const relationsRef = useRef<unknown>(null);
  const circuitRef = useRef<unknown>(null);
  const segments = data?.segments[mode] || [];
  const audioUrl = data ? getAudioUrl(data.seed, mode, data.manifest.audioBaseUrl) : "";
  const decoded = useDecodedSignal(audioUrl);
  const endOfSchedule = segments.at(-1)?.end_sec || 0;
  const duration = mediaDuration || decoded.signal?.duration || endOfSchedule;
  const activeSegment = segmentAt(segments, currentTime);
  const n = data?.metadata?.num_qubits || 15;
  const depth = data?.metadata?.layers ?? 10;
  const root = data?.metadata?.preferred_root ?? 7;
  const metric = data?.layers.find(item => item.layer === layer);
  const descriptors = data?.bloch.filter(item => item.layer === layer) || [];
  const graph = data?.graphBackbones?.layers.find(item => item.layer === layer) || null;
  const mi = data?.miMatrices?.layers.find(item => item.layer === layer)?.matrix || null;
  const referenceMi = data?.miMatrices?.layers.find(item => item.layer === referenceLayer)?.matrix || null;
  const globalMiMax = useMemo(() => Math.max(0, ...(data?.miMatrices?.layers.flatMap(item => item.matrix.flat()) || [])), [data]);
  const nativeRate = data?.metadata?.audio_config?.sample_rate || 22050;
  const moment = traversalMoment(graph, activeSegment, mode, currentTime, nativeRate);
  const timingCompatible = moment.compatible;

  const activeNodes = moment.activeNodes;

  const selectedDescriptor = descriptors.find(item => item.qubit === selectedQubit) || null;
  const voice = mappedVoice(selectedDescriptor, data?.metadata || null);
  const selectQubit = (q: number) => { setSelectedQubit(q); if (!selectedPair?.includes(q)) setSelectedPair(null); };
  const selectPair = (pair: [number, number]) => { setSelectedPair(pair); setSelectedQubit(pair[0]); };
  const availableModes = (["bfs", "dfs", "mix"] as SonificationMode[]).filter(item => data?.segments[item]?.length && data && getAudioUrl(data.seed, item, data.manifest.audioBaseUrl));

  useEffect(() => {
    let live = true;
    void loadSonificationManifest().then(value => { if (live) { setManifest(value); setSeedId(value.seeds[0].id); } }).catch(reason => { if (live) setError(String(reason.message || reason)); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    if (!manifest || !seedId) return;
    let live = true;
    audioRef.current?.pause(); setPlaying(false); setData(null); setError(null); setCurrentTime(0); setLayer(0); setSelectedPair(null); setReferenceLayer(0); pendingSeek.current = 0;
    void loadSonificationData(seedId, manifest).then(value => {
      if (!live) return;
      setData(value); setSelectedQubit(value.metadata?.preferred_root ?? 7); setInspectedGate(null);
      const initial = (["bfs", "dfs", "mix"] as SonificationMode[]).find(m => value.segments[m]?.length && getAudioUrl(value.seed, m, value.manifest.audioBaseUrl));
      if (initial) setMode(initial);
    }).catch(reason => { if (live) setError(String(reason.message || reason)); });
    return () => { live = false; };
  }, [manifest, seedId]);
  useEffect(() => {
    changingSource.current = Boolean(audioUrl);
    setMediaDuration(0); setAudioError(null);
    const media = audioRef.current;
    if (media) { media.pause(); media.volume = volume; media.loop = loopWhole; }
    setPlaying(false);
  }, [audioUrl]);
  useEffect(() => { if (audioRef.current) { audioRef.current.volume = volume; audioRef.current.loop = loopWhole; } }, [volume, loopWhole]);

  const seek = (time: number) => {
    const bounded = clamp(time, 0, duration || endOfSchedule || 0);
    const segment = segmentAt(segments, bounded);
    if (segment) setLayer(segment.layer);
    if (audioRef.current?.readyState) audioRef.current.currentTime = bounded;
    else pendingSeek.current = bounded;
    setCurrentTime(bounded); setInspectedGate(null);
  };
  const selectLayer = (value: number) => {
    const segment = segments.find(item => item.layer === value);
    if (segment) seek(segment.start_sec);
  };
  const changeMode = (value: SonificationMode) => {
    if (value === mode || !data) return;
    changingSource.current = true;
    audioRef.current?.pause(); setPlaying(false);
    const nextTime = data.segments[value]?.find(item => item.layer === layer)?.start_sec || 0;
    pendingSeek.current = nextTime; setCurrentTime(nextTime); setMode(value); setInspectedGate(null);
  };
  const playToggle = async () => {
    const audio = audioRef.current;
    if (!audio || !audioUrl) return;
    if (!audio.paused) { audio.pause(); return; }
    try { await audio.play(); setAudioError(null); }
    catch (reason) { setAudioError(`No se pudo reproducir el archivo: ${reason instanceof Error ? reason.message : String(reason)}`); }
  };
  const tick = () => {
    const audio = audioRef.current;
    if (!audio || changingSource.current) return;
    let time = audio.currentTime;
    const selected = segments.find(item => item.layer === layer);
    if (loopLayer && selected && time >= selected.end_sec - 1e-6) { audio.currentTime = selected.start_sec; time = selected.start_sec; }
    setCurrentTime(time);
    const segment = segmentAt(segments, time);
    if (segment) setLayer(segment.layer);
  };
  useEffect(() => {
    if (!playing) return;
    let frame = 0, last = -Infinity;
    const animate = (now: number) => { if (now - last >= 1000 / 30) { tick(); last = now; } frame = requestAnimationFrame(animate); };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [playing, data, mode, layer, loopLayer]);
  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (event.defaultPrevented || target.closest("input,select,button,textarea,a,[role=button],[contenteditable=true],details")) return;
      if (event.code === "Space") { event.preventDefault(); void playToggle(); }
      else if (event.key === "ArrowLeft") { event.preventDefault(); selectLayer(Math.max(0, layer - 1)); }
      else if (event.key === "ArrowRight") { event.preventDefault(); selectLayer(Math.min(depth, layer + 1)); }
    };
    window.addEventListener("keydown", keyboard);
    return () => window.removeEventListener("keydown", keyboard);
  });

  const exportSession = () => {
    if (!data) return;
    downloadJson({ interface_version: "sonification-ui-v3", interface_base_commit: "2b84bc268fe43533c5218cb00e2399ec44fb33c3", dataset: data.seed.dataset || data.manifest.dataset, dataset_role: data.seed.kind || "study_sample", example_id: data.seed.kind ? data.seed.id : null, renderer_sha256: data.metadata?.renderer_sha256 || null, dataset_version: data.seed.dataset_version || data.manifest.version, seed: data.seed.seed, layer, time_sec: currentTime, traversal: mode, root, selected_qubit: selectedQubit, inspected_operation: inspectedGate, quantum_time_resolution: data.metadata?.state_resolution || "layer snapshots; gate inspection does not recompute states", audio: { url: audioUrl, sha256: decoded.signal?.sha256 || null, decoded_sample_rate: decoded.signal?.sampleRate || null, channels: decoded.signal?.channels || null, media_duration_sec: mediaDuration || null, volume, loop_layer: loopLayer, loop_whole: loopWhole, source_version_verified_against_frozen_engine: false }, visualization: inspectionRef.current, relations: relationsRef.current, circuit: circuitRef.current, selected_pair: selectedPair, gate_presentation: "bounded reading animation; not physical execution timing", graph_schedule_duration_compatible: timingCompatible, schedule_alignment_sample_rate: nativeRate, quantum_layer_is_active: Boolean(activeSegment), mapping: data.metadata?.mapping, warnings: data.warnings }, `session-${data.seed.id}-${mode}-L${layer}.json`);
  };

  return <main className="qs-page">
    <header className="qs-topbar"><a className="qs-brand" href="#qs-content"><span className="qs-logo"><Atom size={40} strokeWidth={1.3} /></span><span><strong>Quantum Sonification</strong><small>{data ? `${data.seed.label} · ${n} qubits · ${depth} capas` : "Cargando muestra"}</small></span></a><nav className="qs-scene-links" aria-label="Secciones de la experiencia"><a href="#qs-circuit">Circuito</a><a href="#qs-relations">Relaciones</a><a href="#signal-title">Señal</a></nav></header>
    <div className="qs-shell" id="qs-content">
      <section className="qs-intro qs-simple-intro"><div><h1>Escucha cómo se organiza<br /><em>la información.</em></h1><p>Un mismo estado; distintas maneras de recorrerlo. Explora del circuito a la señal.</p></div><span className="qs-sample-context">Muestra precargada · simulación</span></section>
      {error && <div className="qs-error" role="alert"><AlertTriangle size={18} /><span>{error}</span></div>}
      {!data && !error && <div className="qs-panel qs-loading" role="status">Cargando los datos precargados…</div>}
      {data && <>
        {(manifest?.seeds.length || 0) > 1 && <div className="qs-example-picker"><label>Muestra<select aria-label="Muestra de sonificación" value={seedId} onChange={event => setSeedId(event.target.value)}><optgroup label="Muestra del estudio">{manifest?.seeds.filter(seed => !seed.kind).map(seed => <option key={seed.id} value={seed.id}>{seed.label}</option>)}</optgroup><optgroup label="Ejemplos didácticos · simulación ideal">{manifest?.seeds.filter(seed => seed.kind).map(seed => <option key={seed.id} value={seed.id}>{seed.label}</option>)}</optgroup></select></label><span>{data.seed.kind ? "Ejemplo ilustrativo · fuera de las cohortes estadísticas" : "Muestra original · seed 1060"}</span></div>}
        <ExampleLesson seed={data.seed} layer={layer} />
        <section className="qs-transport" aria-label="Reproducción y comparación de recorridos">
          <div className="qs-transport-main"><div className="qs-mode-buttons" role="group" aria-label="Recorrido del mismo estado">{availableModes.map(item => <button key={item} data-mode={item} aria-pressed={mode === item} onClick={() => changeMode(item)}>{item === "mix" ? "Combinado" : item.toUpperCase()}</button>)}</div><button className="qs-play" aria-label={playing ? "Pausar audio" : "Reproducir audio"} disabled={!audioUrl} onClick={() => void playToggle()}>{playing ? <Pause size={19} /> : <Play size={19} />}</button><button className="qs-icon-button" aria-label="Volver al inicio de la capa" onClick={() => selectLayer(layer)}><RotateCcw size={16} /></button><span className="qs-clock">{timeLabel(currentTime)} <span>/ {timeLabel(duration)}</span></span><details className="qs-listening-options"><summary>Escucha</summary><div><label className="qs-volume"><Volume2 size={15} /> Volumen<input aria-label="Volumen de escucha" type="range" min={0} max={1} step={0.01} value={volume} onChange={e => setVolume(Number(e.target.value))} /></label><label className="qs-check"><input type="checkbox" checked={loopLayer} onChange={e => { setLoopLayer(e.target.checked); if (e.target.checked) setLoopWhole(false); }} /> Repetir capa</label><label className="qs-check"><input type="checkbox" checked={loopWhole} onChange={e => { setLoopWhole(e.target.checked); if (e.target.checked) setLoopLayer(false); }} /> Repetir archivo</label></div></details></div>
          <input className="qs-seek" aria-label="Tiempo del audio" type="range" min={0} max={duration || 1} step={0.01} value={Math.min(currentTime, duration || 1)} onChange={e => seek(Number(e.target.value))} />
          <div className="qs-layer-navigation"><span>Capa</span>{Array.from({ length: depth + 1 }, (_, value) => <button key={value} aria-label={`Escuchar capa ${value}`} aria-pressed={layer === value} disabled={!segments.some(segment => segment.layer === value)} onClick={() => selectLayer(value)}>{String(value).padStart(2, "0")}</button>)}<span className="qs-transport-note">{data.seed.kind ? "Audio del estado al terminar el paso" : "Audio del estado final de la capa"} {layer}</span></div>
        </section>
                <audio ref={audioRef} src={audioUrl || undefined} preload="metadata" onPlay={() => setPlaying(true)} onPause={() => { tick(); setPlaying(false); }} onEnded={() => { const audio = audioRef.current; const segment = segments.find(item => item.layer === layer); if (loopLayer && audio && segment) { audio.currentTime = segment.start_sec; setCurrentTime(segment.start_sec); void audio.play().catch(reason => setAudioError(String(reason))); } else { setPlaying(false); tick(); } }} onTimeUpdate={tick} onSeeked={tick} onLoadedMetadata={() => { const audio = audioRef.current; if (!audio) return; setMediaDuration(audio.duration); audio.currentTime = Math.min(pendingSeek.current, Number.isFinite(audio.duration) ? audio.duration : pendingSeek.current); pendingSeek.current = 0; changingSource.current = false; tick(); }} onError={() => { setPlaying(false); setAudioError("El archivo de audio no pudo cargarse. Comprueba su URL en el manifiesto."); }} />
        {audioError && <div className="qs-error" role="alert"><AlertTriangle size={17} />{audioError}</div>}
        {mediaDuration > 0 && Math.abs(mediaDuration - endOfSchedule) > 0.04 && <p className="qs-notice">El archivo dura {number(mediaDuration, 3)} s y el calendario termina en {number(endOfSchedule, 3)} s. Verifica que ambos procedan de la misma versión antes de interpretar su sincronización.</p>}

        <CircuitScene data={data} layer={layer} segment={activeSegment} currentTime={currentTime} signal={decoded.signal} activeNodes={activeNodes} selectedQubit={selectedQubit} inspectedGate={inspectedGate} playing={playing} onInspection={state => { circuitRef.current = state; }} onQubit={selectQubit} onGate={gate => { setInspectedGate(gate.operation_index); selectQubit(gateTargets(gate)[0]); }} />
        <div className="qs-now-listening"><span>{moment.active.length ? moment.active.map(item => `${item.branch.toUpperCase()}: ${item.event.kind === "sound" ? item.event.nodes.map(q => `q${q}`).join(" + ") : "pausa"}`).join(" · ") : "Transición entre capas"}</span><small>Voces del calendario · selección visual no aísla audio</small></div>
        <div className="qs-context-grid"><RelationsExplorer graph={graph} matrix={mi} reference={referenceMi} layer={layer} depth={depth} n={n} root={root} tolerance={data.metadata?.edge_tolerance ?? 1e-10} maximum={globalMiMax} moment={moment} currentTime={currentTime} selectedQubit={selectedQubit} pair={selectedPair} onQubit={selectQubit} onPair={selectPair} pauseAudio={() => audioRef.current?.pause()} onInspection={state => { relationsRef.current = state; }} referenceLayer={referenceLayer} onReference={setReferenceLayer} /><aside className="qs-context-side"><QubitInspector descriptor={selectedDescriptor} history={data.bloch.filter(item => item.qubit === selectedQubit)} metadata={data.metadata} layer={layer} n={n} onQubit={selectQubit} selectedQubit={selectedQubit} /></aside></div>
        <QuantumSummary metrics={data.layers} layer={layer} qubits={n} />
        <SignalWorkbench load={decoded} currentTime={currentTime} referenceVoice={voice ? { qubit: selectedQubit, frequency: voice.frequency } : null} onInspectionChange={inspection => { inspectionRef.current = inspection; }} />
        <Overview load={decoded} segments={segments} currentTime={currentTime} duration={duration} activeLayer={layer} onSeek={seek} />
        <section className="qs-panel qs-provenance" id="qs-session"><div><div className="qs-kicker">Registro de la exploración</div><h2>{data.seed.label} · L{layer} · {mode === "mix" ? "Combinado" : mode.toUpperCase()}</h2><p className="qs-muted">Datos y audio precargados; motor de referencia conservado.</p></div><button className="qs-small-button" onClick={exportSession}><Download size={15} /> Exportar sesión</button><details><summary>Procedencia y resolución de los datos</summary><p>Dataset {data.seed.dataset || data.manifest.dataset} · versión {data.seed.dataset_version || data.manifest.version} · raíz q{root}. Los estados cuánticos se observan al terminar cada bloque registrado; la aparición de compuertas es una presentación de su orden.</p><p className="qs-hash">SHA-256 audio: {decoded.signal?.sha256 || "pendiente de lectura"}</p><p>Se analiza el PCM decodificado del archivo, antes del volumen de escucha. Estas medidas no sustituyen los WAV científicos. Las curvas acústicas no reconstruyen el estado cuántico ni certifican entrelazamiento. La sesión guarda escalas, referencia MI, selección y parámetros de inspección.</p>{data.warnings.length > 0 && <ul>{data.warnings.map(warning => <li key={warning}>{warning}</li>)}</ul>}</details></section>
      </>}
    </div><footer className="qs-page-footer">Espacio: reproducir / pausar · ← →: cambiar capa · Explora un qubit o un par para conectar las vistas.</footer>
  </main>;
}

function Overview({ load, segments, currentTime, duration, activeLayer, onSeek }: { load: ReturnType<typeof useDecodedSignal>; segments: AudioSegment[]; currentTime: number; duration: number; activeLayer: number; onSeek: (time: number) => void }) {
  const envelope = useMemo(() => load.signal ? peakEnvelope(load.signal, 900) : null, [load.signal]);
  const points = envelope ? Array.from(envelope, (value, i) => `${i / (envelope.length - 1) * 1000},${32 - value * 90}`).join(" ") : "";
  return <section className="qs-panel qs-overview" aria-label="Mapa temporal del archivo"><div className="qs-overview-title"><strong>Mapa del archivo</strong><span>Capas y picos de amplitud · haz clic para buscar</span></div><button className="qs-overview-wave" aria-label="Buscar en la envolvente de audio" onClick={e => { const r = e.currentTarget.getBoundingClientRect(); onSeek(clamp((e.clientX - r.left) / r.width, 0, 1) * duration); }}><svg viewBox="0 0 1000 64" preserveAspectRatio="none" role="img" aria-label="Pico absoluto del audio por intervalo"><line x1={0} x2={1000} y1={32} y2={32} />{points && <polyline points={points} />}</svg><span className="qs-overview-cursor" style={{ left: `${duration ? currentTime / duration * 100 : 0}%` }} /></button><div className="qs-overview-layers">{segments.map(segment => <button key={segment.layer} style={{ left: `${segment.start_sec / Math.max(1e-8, duration) * 100}%`, width: `${(segment.end_sec - segment.start_sec) / Math.max(1e-8, duration) * 100}%` }} aria-pressed={segment.layer === activeLayer} onClick={() => onSeek(segment.start_sec)}>L{segment.layer}</button>)}</div></section>;
}

function QubitInspector({ descriptor, history, metadata, layer, n, selectedQubit, onQubit }: { descriptor: BlochDescriptor | null; history: BlochDescriptor[]; metadata: SeedMetadata | null; layer: number; n: number; selectedQubit: number; onQubit: (q: number) => void }) {
  const mapping = mappedVoice(descriptor, metadata);
  const project = (d: { x: number; y: number; z: number }) => [110 + (d.x * Math.cos(0.4) + d.y * Math.sin(0.4)) * 80, 110 - (d.z * Math.cos(0.3) + (d.y * Math.cos(0.4) - d.x * Math.sin(0.4)) * Math.sin(0.3)) * 80];
  const past = history.filter(item => item.layer <= layer).sort((a, b) => a.layer - b.layer);
  const points = past.map(item => project(item).join(",")).join(" ");
  const end = descriptor ? project(descriptor) : [110, 110];
  return <section className="qs-panel qs-qubit-inspector"><div className="qs-kicker">Estado reducido</div><div className="qs-inspector-title"><h2>Qubit q{selectedQubit}</h2><select aria-label="Qubit inspeccionado" value={selectedQubit} onChange={e => onQubit(Number(e.target.value))}>{Array.from({ length: n }, (_, q) => <option key={q} value={q}>q{q}</option>)}</select></div><p className="qs-chart-note">Capa {layer} · estado local y mapeo de esta voz.</p>{descriptor ? <><svg className="qs-bloch" viewBox="0 0 220 220" role="img" aria-label="Proyección del vector de Bloch en tres dimensiones; trayectoria hasta la capa actual"><circle cx={110} cy={110} r={80} /><ellipse cx={110} cy={110} rx={80} ry={80 * Math.sin(0.3)} /><line className="qs-bloch-axis" x1={110} y1={110 - 80 * Math.cos(0.3)} x2={110} y2={110 + 80 * Math.cos(0.3)} /><polyline className="qs-bloch-history" points={points} /><line className="qs-bloch-vector" x1={110} y1={110} x2={end[0]} y2={end[1]} /><circle className="qs-bloch-end" cx={end[0]} cy={end[1]} r={4} /></svg><p className="qs-vector">({number(descriptor.x)}, {number(descriptor.y)}, {number(descriptor.z)})</p><div className="qs-qubit-values"><div><span>Radio r</span><strong>{number(descriptor.r, 4)}</strong></div><div><span>Pureza local</span><strong>{number((1 + descriptor.r ** 2) / 2, 4)}</strong></div><div><span>θ · dirección polar</span><strong>{number(descriptor.theta)} rad</strong></div><div><span>φ · dirección azimutal</span><strong>{number(descriptor.phi)} rad</strong></div></div>{mapping && <div className="qs-voice-mapping"><div><span>Tono asignado</span><strong>{mapping.frequency.toFixed(1)} Hz</strong><small>θ → frecuencia · marcador en el espectro</small></div><div><span>Paneo asignado · potencia</span><strong>L {(100 * mapping.leftPower).toFixed(0)} % · R {(100 * mapping.rightPower).toFixed(0)} %</strong><small>φ → reparto estéreo de la voz</small></div></div>}{mapping && <details className="qs-quiet-details"><summary>Cómo se asigna esta voz</summary><p>θ distribuye el tono de forma exponencial entre {metadata?.audio_config?.frequency_min_hz ?? 110} y {metadata?.audio_config?.frequency_max_hz ?? 880} Hz. φ reparte la potencia entre canales. r fija la amplitud base ({mapping.amplitude.toFixed(4)} en este estado), antes de la envolvente, la modulación y la mezcla.</p>{mapping.neutral && <p>Con r próximo a cero, la dirección no está definida: el motor adopta θ=π/2 y φ=π para una voz neutral. No se interpreta esa dirección como una propiedad del qubit.</p>}</details>}<svg className="qs-radius-chart" viewBox="0 0 260 95" role="img" aria-label="Radio de Bloch por capa hasta el estado seleccionado"><line x1={20} x2={245} y1={70} y2={70} /><polyline points={past.map(item => `${20 + item.layer / Math.max(1, history.length - 1) * 220},${70 - item.r * 52}`).join(" ")} /><text x={20} y={89}>0</text><text x={222} y={89}>capa {history.length - 1}</text><text x={3} y={21}>r</text></svg><p className="qs-chart-note">θ y φ orientan el vector; r le da tamaño. P=(1+r²)/2 describe la pureza local. La trayectoria une instantáneas, no estados intermedios. Seleccionar este qubit no aísla su voz de la mezcla.</p></> : <p className="qs-empty">Descriptor no disponible para esta capa.</p>}</section>;
}
