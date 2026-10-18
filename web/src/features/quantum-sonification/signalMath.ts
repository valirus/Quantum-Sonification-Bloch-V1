/** Signal coordinates, not quantum-state coordinates. All windows end at the media clock. */
export interface DecodedSignal {
  left: Float32Array;
  right: Float32Array;
  sampleRate: number;
  duration: number;
  channels: number;
  sourceUrl: string;
  sha256: string | null;
}

export type PhaseView = "lr" | "ms" | "delay" | "delay3d";
export const FFT_SIZE = 4096;
export const FFT_HOP = 2048;
export const DB_FLOOR = -100;

export const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value));

export function windowBounds(signal: DecodedSignal, time: number, milliseconds: number) {
  const end = clamp(Math.floor(time * signal.sampleRate), 0, signal.left.length);
  const count = Math.max(2, Math.round(milliseconds * signal.sampleRate / 1000));
  return { start: Math.max(0, end - count), end, count };
}

export function windowStatistics(signal: DecodedSignal, time: number, milliseconds: number) {
  const { start, end } = windowBounds(signal, time, milliseconds);
  const count = end - start;
  let l = 0, r = 0, ll = 0, rr = 0, lr = 0, side = 0, mid = 0, peak = 0;
  for (let i = start; i < end; i += 1) {
    const a = signal.left[i], b = signal.right[i];
    l += a; r += b; ll += a * a; rr += b * b; lr += a * b;
    mid += ((a + b) / 2) ** 2; side += ((a - b) / 2) ** 2;
    peak = Math.max(peak, Math.abs(a), Math.abs(b));
  }
  const vl = count ? ll - l * l / count : 0;
  const vr = count ? rr - r * r / count : 0;
  const denominator = Math.sqrt(Math.max(0, vl) * Math.max(0, vr));
  const correlation = signal.channels >= 2 && denominator > 1e-16
    ? clamp((lr - l * r / count) / denominator, -1, 1) : null;
  return {
    count,
    rms: count ? Math.sqrt((ll + rr) / (2 * count)) : null,
    correlation,
    sideFraction: signal.channels >= 2 && mid + side > 1e-16 ? side / (mid + side) : null,
    peak,
    startSeconds: start / signal.sampleRate,
    endSeconds: end / signal.sampleRate,
  };
}

export function phaseCoordinates(signal: DecodedSignal, time: number, milliseconds: number, view: PhaseView, delayMs: number) {
  const { start, end } = windowBounds(signal, time, milliseconds);
  const delaySamples = Math.max(1, Math.round(delayMs * signal.sampleRate / 1000));
  const first = Math.max(start, view === "delay3d" ? 2 * delaySamples : view === "delay" ? delaySamples : 0);
  // Keep contiguous samples: coarse subsampling creates spurious polygons and aliases.
  const points: Array<[number, number, number]> = [];
  const mono = (i: number) => (signal.left[i] + signal.right[i]) / 2;
  for (let i = first; i < end; i += 1) {
    const l = signal.left[i], r = signal.right[i];
    if (view === "lr") points.push([l, r, 0]);
    else if (view === "ms") points.push([(l + r) / 2, (l - r) / 2, 0]);
    else points.push([mono(i), mono(i - delaySamples), view === "delay3d" ? mono(i - 2 * delaySamples) : 0]);
  }
  return { points, firstSample: first, delaySamples, actualDelayMs: 1000 * delaySamples / signal.sampleRate };
}

export function projectSignalPoint(point: [number, number, number], yaw: number, pitch: number): [number, number, number] {
  const [x, y, z] = point;
  const a = x * Math.cos(yaw) + z * Math.sin(yaw);
  const c = -x * Math.sin(yaw) + z * Math.cos(yaw);
  return [a, y * Math.cos(pitch) - c * Math.sin(pitch), y * Math.sin(pitch) + c * Math.cos(pitch)];
}

/** In-place radix-2 FFT. No smoothing, compression or independent channel normalization. */
export function fft(real: Float64Array, imaginary: Float64Array) {
  const n = real.length;
  if (n < 2 || (n & (n - 1)) !== 0 || imaginary.length !== n) throw new Error("FFT: tamaño inválido");
  for (let i = 1, j = 0; i < n; i += 1) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [real[i], real[j]] = [real[j], real[i]];
      [imaginary[i], imaginary[j]] = [imaginary[j], imaginary[i]];
    }
  }
  for (let size = 2; size <= n; size <<= 1) {
    const angle = -2 * Math.PI / size;
    const ur = Math.cos(angle), ui = Math.sin(angle);
    for (let start = 0; start < n; start += size) {
      let wr = 1, wi = 0;
      for (let j = 0; j < size / 2; j += 1) {
        const even = start + j, odd = even + size / 2;
        const tr = wr * real[odd] - wi * imaginary[odd];
        const ti = wr * imaginary[odd] + wi * real[odd];
        real[odd] = real[even] - tr; imaginary[odd] = imaginary[even] - ti;
        real[even] += tr; imaginary[even] += ti;
        const next = wr * ur - wi * ui;
        wi = wr * ui + wi * ur; wr = next;
      }
    }
  }
}

export function spectrumAt(signal: Pick<DecodedSignal, "left" | "right" | "sampleRate">, endSample: number, size = FFT_SIZE) {
  const hann = Float64Array.from({ length: size }, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / (size - 1)));
  const windowSum = hann.reduce((a, b) => a + b, 0);
  const transform = (channel: Float32Array) => {
    const real = new Float64Array(size), imaginary = new Float64Array(size);
    for (let i = 0; i < size; i += 1) {
      const index = endSample - size + i;
      real[i] = index >= 0 && index < channel.length ? channel[index] * hann[i] : 0;
    }
    fft(real, imaginary);
    return Float64Array.from({ length: size / 2 + 1 }, (_, i) => {
      const multiplier = i === 0 || i === size / 2 ? 1 : 2;
      return multiplier * Math.hypot(real[i], imaginary[i]) / windowSum;
    });
  };
  const l = transform(signal.left), r = signal.right === signal.left ? l : transform(signal.right);
  // Mean CHANNEL POWER, not spectrum of the summed channels (which may cancel).
  const values = Float32Array.from(l, (a, i) => Math.max(DB_FLOOR, 20 * Math.log10(Math.max(1e-10, Math.sqrt((a * a + r[i] * r[i]) / 2)))));
  return { values, sampleRate: signal.sampleRate, fftSize: size, endSeconds: endSample / signal.sampleRate };
}

export function peakEnvelope(signal: DecodedSignal, columns = 1000) {
  const values = new Float32Array(columns);
  for (let column = 0; column < columns; column += 1) {
    const start = Math.floor(column * signal.left.length / columns);
    const end = Math.floor((column + 1) * signal.left.length / columns);
    let peak = 0;
    for (let i = start; i < end; i += 1) peak = Math.max(peak, Math.abs(signal.left[i]), Math.abs(signal.right[i]));
    values[column] = peak;
  }
  return values;
}
