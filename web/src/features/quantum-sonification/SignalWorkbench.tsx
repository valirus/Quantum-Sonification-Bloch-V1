import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { Download, Snowflake, Waves } from "lucide-react";
import { clamp, DB_FLOOR, FFT_HOP, FFT_SIZE, phaseCoordinates, projectSignalPoint, windowBounds, windowStatistics } from "./signalMath";
import type { PhaseView } from "./signalMath";
import type { SignalLoadState } from "./useDecodedSignal";

type SpectrumFrame = { values: Float32Array; sampleRate: number; fftSize: number; endSeconds: number };
type Inspection = { frameTime: number; windowMs: number; gain: number; view: PhaseView; delayMs: number; frozen: boolean; yawRad: number; pitchRad: number };
const frequencyLabel = (f: number) => f >= 1000 ? `${(f / 1000).toFixed(1)}k` : String(Math.round(f));
const scalar = (value: number | null, digits = 3) => value === null ? "—" : value.toFixed(digits);

function drawingSurface(canvas: HTMLCanvasElement | null) {
  if (!canvas) return null;
  const box = canvas.getBoundingClientRect();
  const width = Math.max(220, box.width), height = Math.max(80, box.height);
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  if (canvas.width !== Math.round(width * ratio)) canvas.width = Math.round(width * ratio);
  if (canvas.height !== Math.round(height * ratio)) canvas.height = Math.round(height * ratio);
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  context.font = "10px ui-monospace, monospace";
  return { context, width, height };
}

function useResponsiveCanvas(ref: RefObject<HTMLCanvasElement>, draw: () => void) {
  const latest = useRef(draw);
  latest.current = draw;
  useEffect(() => {
    draw();
  });
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(() => latest.current());
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);
}

function frameAxes(context: CanvasRenderingContext2D, width: number, height: number, yLabels: string[]) {
  context.strokeStyle = "#262831"; context.lineWidth = 1;
  context.fillStyle = "#a8a8b3";
  for (let i = 0; i < yLabels.length; i += 1) {
    const y = 16 + i * (height - 38) / Math.max(1, yLabels.length - 1);
    context.beginPath(); context.moveTo(46, y); context.lineTo(width - 12, y); context.stroke();
    context.fillText(yLabels[i], 3, y + 3);
  }
}

export function downloadJson(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function SignalWorkbench({ load, currentTime, referenceVoice, onInspectionChange }: {
  load: SignalLoadState; currentTime: number; referenceVoice?: { qubit: number; frequency: number } | null; onInspectionChange?: (inspection: Inspection) => void;
}) {
  const signal = load.signal;
  const [view, setView] = useState<PhaseView>("lr");
  const [windowMs, setWindowMs] = useState(32);
  const [gain, setGain] = useState(4);
  const [delayMs, setDelayMs] = useState(1.2);
  const [frozenTime, setFrozenTime] = useState<number | null>(null);
  const [maxFrequency, setMaxFrequency] = useState(1600);
  const [yaw, setYaw] = useState(0.65);
  const [pitch, setPitch] = useState(0.35);
  const [frames, setFrames] = useState<SpectrumFrame[]>([]);
  const [workerReady, setWorkerReady] = useState(false);
  const [workerError, setWorkerError] = useState<string | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const scopeRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef<HTMLCanvasElement>(null);
  const spectrumRef = useRef<HTMLCanvasElement>(null);
  const waterfallRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<{ x: number; y: number; yaw: number; pitch: number } | null>(null);
  const frameTime = signal ? clamp(frozenTime ?? currentTime, 0, signal.duration) : 0;
  const frameIndex = signal ? Math.floor(frameTime * signal.sampleRate / FFT_HOP) : 0;
  const latestFrameIndex = useRef(frameIndex);
  latestFrameIndex.current = frameIndex;
  const stats = useMemo(() => signal ? windowStatistics(signal, frameTime, windowMs) : null, [signal, frameTime, windowMs]);
  const phase = useMemo(() => signal ? phaseCoordinates(signal, frameTime, windowMs, view, delayMs) : null, [signal, frameTime, windowMs, view, delayMs]);
  const visibleFrames = frames.filter(frame => frame.endSeconds <= frameTime + 1e-8);
  const lastSpectrum = visibleFrames.at(-1);
  const shownMaxFrequency = signal ? (maxFrequency < 0 ? signal.sampleRate / 2 : Math.min(maxFrequency, signal.sampleRate / 2)) : maxFrequency;

  useEffect(() => {
    setFrozenTime(window.matchMedia("(prefers-reduced-motion: reduce)").matches ? currentTime : null);
    if (signal?.channels === 1) setView("delay");
  }, [signal?.sourceUrl]);

  useEffect(() => {
    setFrames([]); setWorkerReady(false); setWorkerError(null);
    if (!signal) return;
    const worker = new Worker(new URL("./spectrum.worker.ts", import.meta.url), { type: "module" });
    workerRef.current = worker;
    const left = signal.left.slice();
    const right = signal.channels > 1 ? signal.right.slice() : null;
    worker.postMessage({ type: "init", left, right, sampleRate: signal.sampleRate }, right ? [left.buffer, right.buffer] : [left.buffer]);
    worker.onmessage = event => {
      if (event.data.type === "ready") setWorkerReady(true);
      else if (event.data.type === "frames" && event.data.index === latestFrameIndex.current) setFrames(event.data.frames);
    };
    worker.onerror = () => setWorkerError("El análisis espectral no pudo iniciarse. La reproducción y el osciloscopio siguen disponibles.");
    return () => { worker.terminate(); workerRef.current = null; };
  }, [signal]);

  useEffect(() => {
    if (workerReady) workerRef.current?.postMessage({ type: "frames", index: frameIndex });
  }, [workerReady, frameIndex]);

  useEffect(() => {
    onInspectionChange?.({ frameTime, windowMs, gain, view, delayMs: phase?.actualDelayMs ?? delayMs, frozen: frozenTime !== null, yawRad: yaw, pitchRad: pitch });
  }, [frameTime, windowMs, gain, view, phase?.actualDelayMs, frozenTime, yaw, pitch]);

  useResponsiveCanvas(scopeRef, () => {
    const surface = drawingSurface(scopeRef.current);
    if (!surface || !signal) return;
    const { context: c, width: w, height: h } = surface;
    const half = (h - 46) / 2, middle = 16 + half;
    frameAxes(c, w, h, [scalar(1 / gain, 3), "0", scalar(-1 / gain, 3)]);
    const { end, count } = windowBounds(signal, frameTime, windowMs);
    const plotWidth = w - 60;
    [signal.left, ...(signal.channels > 1 ? [signal.right] : [])].forEach((channel, channelIndex) => {
      c.strokeStyle = channelIndex ? "#bbabdf" : "#f3f2ed"; c.lineWidth = 1.2; c.beginPath();
      for (let i = 0; i < count; i += 1) {
        const sample = end - count + i;
        const value = sample >= 0 && sample < channel.length ? channel[sample] : 0;
        const x = 46 + i / Math.max(1, count - 1) * plotWidth;
        const y = middle - clamp(value * gain, -1, 1) * half;
        if (i === 0) c.moveTo(x, y); else c.lineTo(x, y);
      }
      c.stroke();
    });
    c.fillStyle = "#a8a8b3";
    c.fillText(`−${windowMs} ms`, 46, h - 5); c.fillText("ahora", w - 42, h - 5);
  });

  useResponsiveCanvas(phaseRef, () => {
    const surface = drawingSurface(phaseRef.current);
    if (!surface || !phase) return;
    const { context: c, width: w, height: h } = surface;
    const cx = w / 2, cy = h / 2, radius = (Math.min(w, h) - 72) / 2;
    const is3d = view === "delay3d", scale = radius * gain / (is3d ? Math.sqrt(3) : 1);
    c.strokeStyle = "#272a34"; c.lineWidth = 1;
    for (let tick = -1; tick <= 1; tick += 0.5) {
      c.beginPath(); c.moveTo(cx + tick * radius, cy - radius); c.lineTo(cx + tick * radius, cy + radius); c.stroke();
      c.beginPath(); c.moveTo(cx - radius, cy + tick * radius); c.lineTo(cx + radius, cy + tick * radius); c.stroke();
    }
    c.fillStyle = "#a8a8b3";
    const labels = is3d ? ["u", "v"] : view === "lr" ? ["L(t)", "R(t)"] : view === "ms" ? ["M(t)", "S(t)"] : ["M(t)", "M(t−τ)"];
    c.fillText(labels[0], cx + radius - 20, cy + radius + 22);
    c.fillText(labels[1], cx - radius - 20, cy - radius - 12);
    c.fillText(`${is3d ? "u,v: " : ""}±${scalar((is3d ? Math.sqrt(3) : 1) / gain, 3)} PCM`, cx - radius, cy + radius + 22);
    if (is3d) {
      const axes: Array<[number, number, number]> = [[1 / gain, 0, 0], [0, 1 / gain, 0], [0, 0, 1 / gain]];
      axes.forEach((axis, index) => {
        const p = projectSignalPoint(axis, yaw, pitch);
        c.strokeStyle = ["#ff9b54", "#bba9df", "#8baabf"][index];
        c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + p[0] * scale, cy - p[1] * scale); c.stroke();
        c.fillStyle = c.strokeStyle; c.fillText(["M(t)", "M(t−τ)", "M(t−2τ)"][index], cx + p[0] * scale, cy - p[1] * scale - 5);
      });
    }
    const points = phase.points;
    // Age color encodes the order of REAL samples within this window.
    for (let piece = 0; piece < 8; piece += 1) {
      const start = Math.floor(piece * points.length / 8), end = Math.min(points.length, Math.ceil((piece + 1) * points.length / 8) + 1);
      c.strokeStyle = piece > 5 ? "#ffab6e" : "#ded9ec"; c.globalAlpha = 0.15 + 0.85 * (piece + 1) / 8;
      c.lineWidth = 1.1; c.beginPath();
      for (let i = start; i < end; i += 1) {
        const p = is3d ? projectSignalPoint(points[i], yaw, pitch) : points[i];
        const x = cx + clamp(p[0] * scale, -radius, radius), y = cy - clamp(p[1] * scale, -radius, radius);
        if (i === start) c.moveTo(x, y); else c.lineTo(x, y);
      }
      c.stroke();
    }
    c.globalAlpha = 1;
  });

  useResponsiveCanvas(spectrumRef, () => {
    const surface = drawingSurface(spectrumRef.current);
    if (!surface || !lastSpectrum) return;
    const { context: c, width: w, height: h } = surface;
    frameAxes(c, w, h, ["0", "−25", "−50", "−75", "−100"]);
    const lastBin = Math.min(lastSpectrum.values.length - 1, Math.floor(shownMaxFrequency * FFT_SIZE / lastSpectrum.sampleRate));
    c.beginPath(); c.moveTo(46, h - 22);
    for (let i = 0; i <= lastBin; i += 1) {
      const x = 46 + i * lastSpectrum.sampleRate / FFT_SIZE / shownMaxFrequency * (w - 58);
      const y = 16 + clamp(-lastSpectrum.values[i] / -DB_FLOOR, 0, 1) * (h - 38);
      c.lineTo(x, y);
    }
    c.lineTo(w - 12, h - 22); c.closePath();
    const gradient = c.createLinearGradient(0, 16, 0, h - 22);
    gradient.addColorStop(0, "#ffae6d99"); gradient.addColorStop(1, "#ffae6d05");
    c.fillStyle = gradient; c.fill(); c.strokeStyle = "#ffab6e"; c.lineWidth = 1.3; c.stroke();
    if (referenceVoice && referenceVoice.frequency <= shownMaxFrequency) {
      const x = 46 + referenceVoice.frequency / shownMaxFrequency * (w - 60);
      c.strokeStyle = "#c5abd8"; c.setLineDash([3, 5]); c.beginPath(); c.moveTo(x, 16); c.lineTo(x, h - 22); c.stroke(); c.setLineDash([]);
      c.fillStyle = "#d2bfdc"; c.fillText(`q${referenceVoice.qubit}`, Math.min(w - 30, x + 4), 27);
    }
    c.fillStyle = "#a8a8b3";
    for (let i = 0; i <= 4; i += 1) c.fillText(`${frequencyLabel(i * shownMaxFrequency / 4)} Hz`, 46 + i / 4 * (w - 100), h - 5);
  });

  useResponsiveCanvas(waterfallRef, () => {
    const surface = drawingSurface(waterfallRef.current);
    if (!surface || !visibleFrames.length) return;
    const { context: c, width: w, height: h } = surface;
    const end = visibleFrames.at(-1)!.endSeconds, start = end - 6;
    const plotW = w - 58, plotH = h - 30;
    for (const frame of visibleFrames) {
      const x = 46 + (frame.endSeconds - start) / 6 * plotW;
      const cellWidth = FFT_HOP / frame.sampleRate / 6 * plotW + 1;
      const maxBin = Math.min(frame.values.length - 1, Math.floor(shownMaxFrequency * FFT_SIZE / frame.sampleRate));
      for (let bin = 0; bin <= maxBin; bin += 1) {
        const intensity = clamp((frame.values[bin] - DB_FLOOR) / -DB_FLOOR, 0, 1);
        c.fillStyle = `rgb(${Math.round(10 + intensity ** 1.4 * 245)},${Math.round(12 + intensity ** 1.7 * 183)},${Math.round(19 + intensity * 111)})`;
        const cellH = plotH / (maxBin + 1);
        c.fillRect(x - cellWidth, 12 + plotH - (bin + 1) * cellH, cellWidth, Math.ceil(cellH));
      }
    }
    c.fillStyle = "#a8a8b3";
    c.fillText(`${frequencyLabel(shownMaxFrequency)}`, 3, 20); c.fillText("0 Hz", 3, h - 23);
    for (let i = 0; i <= 3; i += 1) {
      const time = start + i * 2;
      if (time >= 0) c.fillText(`${time.toFixed(1)} s`, 46 + i / 3 * (plotW - 30), h - 5);
    }
  });

  const exportCoordinates = () => {
    if (!signal || !phase) return;
    const csv = "time_sec,x_pcm,y_pcm,z_pcm\n" + phase.points.map((point, i) => `${(phase.firstSample + i) / signal.sampleRate},${point.join(",")}`).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `signal-${view}-${frameTime.toFixed(3)}s.csv`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    downloadJson({ source: signal.sourceUrl, source_sha256: signal.sha256, sample_rate_decoded: signal.sampleRate, channels: signal.channels, frame_time_sec: frameTime, mapped_frequency_reference: referenceVoice || null, window_ms: windowMs, view, delay_samples: phase.delaySamples, delay_ms: phase.actualDelayMs, display_gain: gain, projection: { method: "orthographic", yaw_rad: yaw, pitch_rad: pitch, scale_3d_divisor: Math.sqrt(3) }, volume_applied_to_coordinates: false, statistics: stats, coordinate_space: "decoded acoustic signal; not a quantum Hilbert-state reconstruction" }, `signal-${view}-${frameTime.toFixed(3)}s.json`);
  };

  return <section className="qs-panel qs-instrument" aria-labelledby="signal-title">
    <div className="qs-instrument-heading">
      <div><div className="qs-kicker"><Waves size={15} /> 03 · Audio, espectro y trayectoria</div><h2 id="signal-title">La señal, en movimiento.</h2><p className="qs-muted">Cada punto procede del archivo de audio. Onda y trayectorias siguen el cursor; las medidas conservan su escala antes del volumen de escucha.</p></div>
      <span className="qs-source-badge">{load.status === "ready" ? "PCM decodificado" : load.status === "loading" ? "Leyendo audio…" : "PCM no disponible"}</span>
    </div>
    {load.status !== "ready" && <div className="qs-empty-signal" role={load.status === "error" ? "alert" : "status"}><Waves size={28} /><strong>{load.status === "loading" ? "Preparando la señal del archivo…" : "Sin muestras, no dibujamos una señal."}</strong><span>{load.message || "Las vistas aparecerán cuando termine la lectura del audio seleccionado."}</span></div>}
    {signal && <>
      <div className="qs-instrument-controls">
        <label>Ventana de onda<select aria-label="Ventana de señal" value={windowMs} onChange={e => setWindowMs(Number(e.target.value))}>{[16, 32, 64, 128].map(n => <option key={n} value={n}>{n} ms</option>)}</select></label>
        <label>Escala de onda<select aria-label="Ganancia visual común" value={gain} onChange={e => setGain(Number(e.target.value))}>{[1, 2, 4, 8, 16].map(n => <option key={n} value={n}>×{n}</option>)}{![1, 2, 4, 8, 16].includes(gain) && <option value={gain}>×{gain.toFixed(1)} · ajustada</option>}</select></label>
        <button className="qs-small-button" disabled={!stats?.count} onClick={() => { const peak = Math.max(stats?.peak || 0, ...(phase?.points.flatMap(point => point.map(Math.abs)) || [0])); if (peak > 1e-10) setGain(Math.min(1000, 0.85 / peak)); }}>Ajustar a esta ventana</button>
        <button className="qs-small-button" aria-pressed={frozenTime !== null} onClick={() => setFrozenTime(frozenTime === null ? currentTime : null)}><Snowflake size={14} />{frozenTime === null ? "Congelar vistas" : "Seguir audio"}</button>
        {frozenTime !== null && <button className="qs-small-button" onClick={() => setFrozenTime(currentTime)}>Nueva captura</button>}
        <span className="qs-instrument-time">{frozenTime !== null ? "Captura" : "Cursor"} · {frameTime.toFixed(3)} s</span>
      </div>
      {stats && stats.peak * gain > 1 && <p className="qs-notice">Hay recorte visual a ×{gain}. Baja la escala para ver toda la amplitud. El audio permanece intacto.</p>}
      <div className="qs-signal-grid">
        <div className="qs-signal-left">
          <figure className="qs-signal-card"><figcaption><strong>Osciloscopio</strong><span><i className="qs-channel-key" /> L {signal.channels > 1 && <><i className="qs-channel-key qs-channel-r" /> R</>} · amplitud PCM</span></figcaption><canvas ref={scopeRef} className="qs-scope-canvas" role="img" aria-label="Muestras temporales de los canales del archivo" /><p className="qs-chart-note">Ventana de {windowMs} ms · misma ganancia en ambos canales · muestra a muestra.</p></figure>
          <figure className="qs-signal-card"><figcaption><strong>Espectro del instante</strong><label>Rango<select aria-label="Rango de frecuencias" value={maxFrequency} onChange={e => setMaxFrequency(Number(e.target.value))}><option value={1600}>0–1.6 kHz</option><option value={8000}>0–8 kHz</option><option value={-1}>Nyquist</option></select></label></figcaption><canvas ref={spectrumRef} className="qs-fft-canvas" role="img" aria-label="Espectro en Hz y dBFS del audio decodificado" /><p className="qs-chart-note">Hann · {FFT_SIZE} muestras · Δf {(signal.sampleRate / FFT_SIZE).toFixed(2)} Hz · dBFS de amplitud equivalente por potencia media L/R. {lastSpectrum ? `Ventana termina en ${lastSpectrum.endSeconds.toFixed(3)} s.` : "Calculando…"}</p></figure>
        </div>
        <figure className="qs-signal-card qs-phase-card"><figcaption><strong>Lissajous y trayectorias</strong></figcaption>
          <label className="qs-phase-select">Coordenadas<select aria-label="Coordenadas de trayectoria" value={view} onChange={e => setView(e.target.value as PhaseView)}><option value="lr" disabled={signal.channels < 2}>L ↔ R · estéreo</option><option value="ms" disabled={signal.channels < 2}>Mid ↔ Side</option><option value="delay">M(t) ↔ M(t−τ)</option><option value="delay3d">Retardos · 3D</option></select></label>
          <canvas ref={phaseRef} className="qs-phase-canvas" style={{ touchAction: view === "delay3d" ? "none" : "auto" }} role="img" aria-label={view === "delay3d" ? "Proyección 3D de tres muestras de la señal con retardos" : "Diagrama de coordenadas acústicas de las muestras"}
            onPointerDown={event => { if (view !== "delay3d") return; event.currentTarget.setPointerCapture(event.pointerId); dragRef.current = { x: event.clientX, y: event.clientY, yaw, pitch }; }}
            onPointerMove={event => { const d = dragRef.current; if (!d) return; setYaw(d.yaw + (event.clientX - d.x) * 0.008); setPitch(clamp(d.pitch + (event.clientY - d.y) * 0.008, -1.3, 1.3)); }}
            onPointerUp={() => { dragRef.current = null; }} onPointerCancel={() => { dragRef.current = null; }} />
          {(view === "delay" || view === "delay3d") && <label className="qs-delay-control">Retardo τ <input aria-label="Retardo de la señal" type="range" min={0.1} max={12} step={0.1} value={delayMs} onChange={e => setDelayMs(Number(e.target.value))} /><span>{phase?.actualDelayMs.toFixed(3)} ms · {phase?.delaySamples} muestras</span></label>}
          {view === "delay3d" && <label className="qs-delay-control">Rotación <input aria-label="Rotación 3D" type="range" min={-Math.PI} max={Math.PI} step={0.02} value={yaw} onChange={e => setYaw(Number(e.target.value))} /><span>Arrastra para girar. La cámara no altera la señal.</span></label>}
          <p className="qs-chart-note">{view === "lr" ? "Una recta indica canales proporcionales; una curva más abierta puede reflejar fase, mezcla de voces o modulación." : view === "ms" ? "M=(L+R)/2 recoge lo común; S=(L−R)/2 recoge la diferencia entre canales." : "Los retardos revelan la geometría temporal de la señal. Cambiar τ puede cambiar la forma."} El color sigue la edad de las muestras.</p>
          <details className="qs-quiet-details"><summary>Cómo interpretar la forma</summary><p>Una voz ideal con paneo fijo tiene canales proporcionales: su Lissajous es una recta. Varias voces pueden abrir la figura. En retardos, τ compara la señal con copias desplazadas. Estas curvas no certifican entrelazamiento ni reconstruyen el espacio de Hilbert.</p></details>
        </figure>
      </div>
      <figure className="qs-signal-card qs-waterfall"><figcaption><strong>Espectrograma en movimiento</strong><span>Últimos 6 s disponibles · escala fija −100…0 dBFS</span></figcaption><canvas ref={waterfallRef} className="qs-waterfall-canvas" role="img" aria-label="Espectrograma de los últimos seis segundos de audio hasta el cursor" /><p className="qs-chart-note">Eje vertical: frecuencia. Eje horizontal: tiempo del archivo. Brillo: amplitud espectral. La FFT avanza cada {1000 * FFT_HOP / signal.sampleRate | 0} ms; no se interpola evolución cuántica.</p>{workerError && <p role="alert">{workerError}</p>}</figure>
      <div className="qs-acoustic-stats"><div><span>RMS estéreo</span><strong>{scalar(stats?.rms ?? null, 5)}</strong><small>amplitud PCM</small></div><div><span>Correlación L/R</span><strong>{scalar(stats?.correlation ?? null)}</strong><small>{signal.channels > 1 ? "Pearson · ventana visible" : "no definida en mono"}</small></div><div><span>Energía lateral</span><strong>{stats?.sideFraction === null || !stats ? "—" : `${(100 * stats.sideFraction).toFixed(1)} %`}</strong><small>ΣS² / (ΣM² + ΣS²)</small></div><div><span>Muestreo decodificado</span><strong>{(signal.sampleRate / 1000).toFixed(2)} kHz</strong><small>{signal.channels} canal{signal.channels === 1 ? "" : "es"} · {stats?.count ?? 0} muestras visibles</small></div></div>
      <div className="qs-mapped-frequency">{referenceVoice && <span>Marcador q{referenceVoice.qubit}: {referenceVoice.frequency.toFixed(1)} Hz asignados por el modelo; no es una voz aislada.</span>}</div><div className="qs-instrument-footer"><span>Medidas del archivo antes del control de volumen. En MP3 u Opus, se analiza el PCM decodificado; puede incluir efectos de compresión.</span><button className="qs-small-button" onClick={exportCoordinates}><Download size={14} /> Exportar ventana CSV + JSON</button></div>
    </>}
  </section>;
}
