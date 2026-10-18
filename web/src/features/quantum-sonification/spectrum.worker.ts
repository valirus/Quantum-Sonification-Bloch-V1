import { FFT_HOP, FFT_SIZE, spectrumAt } from "./signalMath";
import type { DecodedSignal } from "./signalMath";

let signal: Pick<DecodedSignal, "left" | "right" | "sampleRate"> | null = null;
const cache = new Map<number, ReturnType<typeof spectrumAt>>();
self.onmessage = (event: MessageEvent) => {
  if (event.data.type === "init") {
    signal = { left: event.data.left, right: event.data.right || event.data.left, sampleRate: event.data.sampleRate };
    cache.clear();
    self.postMessage({ type: "ready" });
    return;
  }
  if (!signal) return;
  const index = Math.max(0, event.data.index);
  const columns = Math.min(180, Math.ceil(6 * signal.sampleRate / FFT_HOP));
  const frames: ReturnType<typeof spectrumAt>[] = [];
  for (let frame = Math.max(0, index - columns + 1); frame <= index; frame += 1) {
    let spectrum = cache.get(frame);
    if (!spectrum) { spectrum = spectrumAt(signal, frame * FFT_HOP, FFT_SIZE); cache.set(frame, spectrum); }
    frames.push(spectrum);
  }
  for (const key of cache.keys()) if (key < index - columns - 20 || key > index + 20) cache.delete(key);
  self.postMessage({ type: "frames", index, frames });
};
