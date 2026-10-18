import { describe, expect, it } from "vitest";
import { FFT_SIZE, phaseCoordinates, spectrumAt, windowBounds, windowStatistics } from "../src/features/quantum-sonification/signalMath";
import type { DecodedSignal } from "../src/features/quantum-sonification/signalMath";
import { segmentAt } from "../src/features/quantum-sonification/timeline";

const fs = 22050;
const make = (phase = 0, amplitude = 0.125): DecodedSignal => ({ left: Float32Array.from({ length: fs }, (_, i) => amplitude * Math.sin(2 * Math.PI * 400 * i / fs)), right: Float32Array.from({ length: fs }, (_, i) => amplitude * Math.sin(2 * Math.PI * 400 * i / fs + phase)), sampleRate: fs, duration: 1, channels: 2, sourceUrl: "explicit-test-tone", sha256: null });

describe("physical interpretation of acoustic coordinates", () => {
  it("identical channels give a diagonal, correlation 1 and zero side energy", () => {
    const signal = make();
    const stats = windowStatistics(signal, 0.8, 100);
    expect(stats.correlation).toBeCloseTo(1, 10);
    expect(stats.sideFraction).toBe(0);
    for (const [x, y] of phaseCoordinates(signal, 0.8, 16, "lr", 1).points) expect(x).toBe(y);
  });
  it("opposite channels give an anti-diagonal and side-energy fraction 1", () => {
    const signal = make(Math.PI);
    const stats = windowStatistics(signal, 0.8, 100);
    expect(stats.correlation).toBeCloseTo(-1, 8);
    expect(stats.sideFraction).toBeCloseTo(1, 8);
    const spectrum = spectrumAt(signal, fs);
    expect(Math.max(...spectrum.values)).toBeGreaterThan(-20);
  });
  it("quadrature gives a circle with equal gain, not an entanglement measure", () => {
    const signal = make(Math.PI / 2);
    const points = phaseCoordinates(signal, 0.8, 100, "lr", 1).points;
    for (const [x, y] of points) expect(Math.hypot(x, y)).toBeCloseTo(0.125, 6);
    expect(windowStatistics(signal, 0.8, 100).correlation).toBeCloseTo(0, 5);
  });
  it("the delay embedding uses the declared samples and no future samples", () => {
    const signal = make();
    const result = phaseCoordinates(signal, 0.019, 32, "delay3d", 1.2);
    expect(result.delaySamples).toBe(Math.round(1.2 * fs / 1000));
    expect(result.firstSample).toBe(2 * result.delaySamples);
    expect(result.firstSample + result.points.length).toBe(Math.floor(0.019 * fs));
    result.points.forEach(([x, y, z], i) => {
      const at = result.firstSample + i;
      expect(x).toBe(signal.left[at]); expect(y).toBe(signal.left[at - result.delaySamples]); expect(z).toBe(signal.left[at - 2 * result.delaySamples]);
    });
  });
  it("silence and missing stereo variance do not invent a correlation", () => {
    const signal = make(0, 0);
    const stats = windowStatistics(signal, 0.8, 32);
    expect(stats.rms).toBe(0); expect(stats.correlation).toBeNull(); expect(stats.sideFraction).toBeNull();
    expect(spectrumAt(signal, fs).values.every(value => value === -100)).toBe(true);
  });
  it("mono has no stereo correlation or stereo side-energy statistic", () => {
    const signal = make(); signal.channels = 1;
    expect(windowStatistics(signal, 0.8, 32).correlation).toBeNull();
    expect(windowStatistics(signal, 0.8, 32).sideFraction).toBeNull();
  });
  it("Hann amplitude normalization recovers a known coherent FFT tone in dBFS", () => {
    const bin = 96, amplitude = 0.125;
    const channel = Float32Array.from({ length: FFT_SIZE }, (_, i) => amplitude * Math.sin(2 * Math.PI * bin * i / FFT_SIZE));
    const spectrum = spectrumAt({ left: channel, right: channel, sampleRate: fs }, FFT_SIZE);
    expect(spectrum.values[bin]).toBeCloseTo(20 * Math.log10(amplitude), 4);
    expect(spectrum.values.indexOf(Math.max(...spectrum.values))).toBe(bin);
  });
  it("bounds at the start, end and outside the file remain within available PCM", () => {
    const signal = make();
    expect(windowBounds(signal, 0, 32).end).toBe(0);
    expect(windowBounds(signal, 4, 32).end).toBe(fs);
    expect(windowBounds(signal, -1, 32).end).toBe(0);
  });
});

describe("layer timeline", () => {
  const segments = [{ layer: 0, start_sec: 0, end_sec: 1 }, { layer: 1, start_sec: 1, end_sec: 2 }, { layer: 2, start_sec: 2.2, end_sec: 3 }];
  it("a shared boundary belongs to the new layer", () => { expect(segmentAt(segments, 1)?.layer).toBe(1); });
  it("gaps have no invented layer or active voice", () => { expect(segmentAt(segments, 2.1)).toBeNull(); });
  it("a browser-rounded sample boundary still selects its layer", () => { const exact=18.23845804988662; expect(segmentAt([{layer:3,start_sec:exact,end_sec:20}],18.238458)?.layer).toBe(3); });
  it("the final endpoint remains selectable", () => { expect(segmentAt(segments, 3)?.layer).toBe(2); });
});
