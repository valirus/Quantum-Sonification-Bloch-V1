import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { compactCircuit, edgeKey, gatePresentation, gateTargets, mappedVoice, matrixFromEdges, maximumForestTrace, wireWindow } from "../src/features/quantum-sonification/visualModels";
import { colorFraction, luminance, matrixColor } from "../src/features/quantum-sonification/colorScale";
import type { AudioSegment, BlochDescriptor, GateOperation, GraphBackboneDataset } from "../src/features/quantum-sonification/types";
import type { DecodedSignal } from "../src/features/quantum-sonification/signalMath";
const root = "public/sonification/seeds/seed_001060/";
const gates: GateOperation[] = readFileSync(root + "gate_manifest.csv", "utf8").trim().split(/\r?\n/).slice(1).map(line => {
  const [layer, operation, , gate_label, qubits] = line.split(",");
  return { layer_added: +layer, operation_index: +operation, gate_label, qubits };
});
const graph: GraphBackboneDataset = JSON.parse(readFileSync(root + "graph_backbones.json", "utf8"));
const descriptor = (r: number, theta: number, phi: number): BlochDescriptor => ({ layer: 1, qubit: 0, r, theta, phi, x: 0, y: 0, z: 0, linear_entropy: 1-r*r, von_neumann_entropy: 0 });
const segment: AudioSegment = { layer: 3, start_sec: 10, end_sec: 15 };

describe("recorded circuit and bounded presentation", () => {
  it("compresses this real circuit to two dependency columns per layer, preserving all 220 operations", () => {
    const result = compactCircuit(gates, 15);
    expect(result.placed.map(p => p.gate.operation_index)).toEqual(Array.from({ length: 220 }, (_, i) => i));
    expect(result.bands.map(b => b.columns)).toEqual(Array(10).fill(2));
    expect(result.columns).toBe(20);
  });
  it("never shares a column between operations that depend on the same qubit", () => {
    for (const band of compactCircuit(gates, 15).bands) {
      const last = new Map<number, number>();
      for (const item of compactCircuit(gates, 15).placed.filter(p => p.gate.layer_added === band.layer)) {
        for (const q of gateTargets(item.gate)) { expect(item.localColumn).toBeGreaterThan(last.get(q) ?? -1); last.set(q, item.localColumn); }
      }
    }
  });
  it("recomputes the recorded prefix when seeking forwards and backwards, without new states", () => {
    expect(gatePresentation(gates, 3, segment, 10).count).toBe(44);
    expect(gatePresentation(gates, 3, segment, 10.625).count).toBe(55);
    expect(gatePresentation(gates, 3, segment, 11.25).count).toBe(66);
    expect(gatePresentation(gates, 3, segment, 10.625).latest).toBe(gates[54]);
    expect(gatePresentation(gates, 3, segment, 10).count).toBe(44);
  });
  it("keeps the initial state empty and a layer gap complete", () => {
    expect(gatePresentation(gates, 0, null, 0).count).toBe(0);
    expect(gatePresentation(gates, 3, null, 15.1).count).toBe(66);
  });
  it("bounds the visual introduction by the available layer duration", () => {
    const tiny = { ...segment, end_sec: 10.5 };
    expect(gatePresentation(gates, 3, tiny, 10).introductionSeconds).toBeCloseTo(.175);
    expect(gatePresentation(gates, 3, tiny, 10.5).count).toBe(66);
  });
});

describe("actual mixed PCM and frozen reference mapping", () => {
  const signal = { left: Float32Array.from({ length: 100 }, (_, i) => i/100), right: Float32Array.from({ length: 100 }, (_, i) => i/100), sampleRate: 1000 } as DecodedSignal;
  it("copies a normalized mixed PCM window and remains identical at the same paused clock", () => {
    const before = wireWindow(signal, .080, 5);
    expect(before).toEqual([.6, .7, .8, .9, 1].map((_, i) => (signal.left[48 + 8*i] + signal.right[48 + 8*i]) / 2 / signal.left[80]));
    expect(wireWindow(signal, .080, 5)).toEqual(before);
    expect(wireWindow(signal, .070, 5)).not.toEqual(before);
    expect(wireWindow(null, .1)).toEqual([]);
  });
  it("does not animate silent PCM with a synthetic oscillation", () => {
    expect(wireWindow({ ...signal, left: new Float32Array(100), right: new Float32Array(100) }, .08)).toEqual(Array(160).fill(0));
  });
  it("respects tone endpoints, power pan and local purity", () => {
    expect(mappedVoice(descriptor(1, 0, 0), null)).toMatchObject({ frequency: 110, leftPower: 1, rightPower: 0, amplitude: .22, purity: 1 });
    const end = mappedVoice(descriptor(1, Math.PI, Math.PI), null)!;
    expect(end.frequency).toBe(880); expect(end.leftPower).toBeCloseTo(.5); expect(end.rightPower).toBeCloseTo(.5);
  });
  it("uses the actual neutral carrier and nonzero amplitude floor when radius is zero", () => {
    const voice = mappedVoice(descriptor(0, 0, 0), null)!;
    expect(voice.neutral).toBe(true); expect(voice.frequency).toBeCloseTo(Math.sqrt(110*880));
    expect(voice.leftPower).toBeCloseTo(.5); expect(voice.amplitude).toBeCloseTo(.22*.12); expect(voice.purity).toBe(.5);
  });
});

describe("maximum-weight forest construction", () => {
  it("rejects cycles, then connects the remaining node with its strongest available edge", () => {
    const m = [[0,9,8,0],[9,0,7,1],[8,7,0,2],[0,1,2,0]];
    const t = maximumForestTrace(m, 0);
    expect(t.steps.map(s => s.accepted)).toEqual([true,true,false,true]);
    expect(t.forestWeight).toBe(19); expect(t.components).toBe(1);
  });
  it("retains isolated qubits and disconnected components as a forest", () => {
    const t = maximumForestTrace([[0,1,0,0],[1,0,0,0],[0,0,0,0],[0,0,0,0]], 1e-10);
    expect(t.forest).toHaveLength(1); expect(t.components).toBe(3);
  });
  it("matches every recorded forest in all 11 real sample layers, using full-precision graph weights", () => {
    for (const layer of graph.layers) {
      const t = maximumForestTrace(matrixFromEdges(layer.allEdges!, 15), graph.edgeTolerance!);
      const expected = layer.forest!;
      expect(t.forest.map(e => edgeKey(e.source,e.target)).sort()).toEqual(expected.map(e => edgeKey(e.source,e.target)).sort());
      expect(t.forestWeight).toBeCloseTo(expected.reduce((s,e)=>s+e.weight,0), 12);
      expect(t.components).toBe(layer.components!.length);
    }
  });
  it("never mutates source edges while building the forest", () => {
    const source = graph.layers[3].allEdges!;
    const before = JSON.stringify(source); const m = matrixFromEdges(source,15);
    const originalMatrix = JSON.stringify(m);
    maximumForestTrace(m,1e-10);
    expect(JSON.stringify(m)).toBe(originalMatrix);
    expect(JSON.stringify(source)).toBe(before);
  });
});

describe("MI color semantics", () => {
  it("uses the same neutral zero for both maps and distinct signed endpoints", () => {
    expect(matrixColor(0,2,true,false)).toBe(matrixColor(0,2,false,false));
    expect(matrixColor(-1,2,true,false)).not.toBe(matrixColor(1,2,true,false));
  });
  it("increases sequential luminance monotonically in both contrast modes", () => {
    for (const log of [false,true]) {
      const values = Array.from({length:101},(_,i)=>luminance(matrixColor(i/50,2,false,log)));
      values.slice(1).forEach((v,i)=>expect(v).toBeGreaterThanOrEqual(values[i]));
    }
  });
  it("keeps global normalization fixed and changes only the color contrast", () => {
    expect(colorFraction(.1,2,false)).toBe(.05);
    expect(colorFraction(.1,2,true)).toBeGreaterThan(.05);
    expect(colorFraction(2,2,true)).toBe(1);
    expect(colorFraction(0,0,true)).toBe(0);
    expect(matrixColor(3,2,false,false)).toBe(matrixColor(2,2,false,false));
  });
});
