import { useEffect, useState } from "react";
import type { DecodedSignal } from "./signalMath";

export interface SignalLoadState {
  status: "empty" | "loading" | "ready" | "error";
  signal: DecodedSignal | null;
  message: string | null;
  sourceUrl: string;
}

function wavSampleRate(bytes: ArrayBuffer) {
  if (bytes.byteLength < 32) return 48000;
  const view = new DataView(bytes);
  if (view.getUint32(0, false) !== 0x52494646 || view.getUint32(8, false) !== 0x57415645) return 48000;
  for (let position = 12; position + 8 < bytes.byteLength;) {
    const length = view.getUint32(position + 4, true);
    if (view.getUint32(position, false) === 0x666d7420 && length >= 16 && position + 24 <= bytes.byteLength) {
      const rate = view.getUint32(position + 12, true);
      return rate >= 8000 && rate <= 96000 ? rate : 48000;
    }
    position += 8 + length + (length % 2);
  }
  return 48000;
}

export function useDecodedSignal(sourceUrl: string): SignalLoadState {
  const [state, setState] = useState<SignalLoadState>({ status: "empty", signal: null, message: null, sourceUrl: "" });
  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    if (!sourceUrl) {
      setState({ status: "empty", signal: null, message: "Selecciona un audio disponible.", sourceUrl });
      return;
    }
    setState({ status: "loading", signal: null, message: null, sourceUrl });
    const load = async () => {
      const response = await fetch(sourceUrl, { signal: controller.signal, mode: "cors" });
      if (!response.ok) throw new Error(`Audio: HTTP ${response.status}`);
      const bytes = await response.arrayBuffer();
      if (disposed) return;
      const digest = globalThis.crypto?.subtle
        ? await crypto.subtle.digest("SHA-256", bytes) : null;
      const sha256 = digest ? Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("") : null;
      const decoder = new OfflineAudioContext(2, 1, wavSampleRate(bytes));
      const buffer = await decoder.decodeAudioData(bytes);
      if (disposed) return;
      if (buffer.numberOfChannels < 1 || buffer.numberOfChannels > 2) throw new Error("Se admite audio mono o estéreo; este archivo tiene otro número de canales.");
      const left = buffer.getChannelData(0);
      const signal: DecodedSignal = {
        left, right: buffer.numberOfChannels > 1 ? buffer.getChannelData(1) : left,
        sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels, duration: buffer.duration, sourceUrl, sha256,
      };
      setState({ status: "ready", signal, message: null, sourceUrl });
    };
    void load().catch(error => {
      if (disposed) return;
      setState({ status: "error", signal: null, sourceUrl, message: `No se pudo leer el PCM: ${error instanceof Error ? error.message : String(error)}. Revisa el archivo y el permiso CORS del servidor de audio.` });
    });
    return () => { disposed = true; controller.abort(); };
  }, [sourceUrl]);
  // Never show an old mode's samples while the new source is being fetched.
  return state.sourceUrl === sourceUrl ? state : { status: sourceUrl ? "loading" : "empty", signal: null, message: null, sourceUrl };
}
