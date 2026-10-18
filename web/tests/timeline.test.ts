import { describe, expect, it } from "vitest";
import { sampleAlignedEvents, segmentAt, traversalMoment } from "../src/features/quantum-sonification/timeline";
import type { GraphAudioEvent, GraphBackboneLayer } from "../src/features/quantum-sonification/types";
const event = (nodes: number[], end: number): GraphAudioEvent => ({ kind: "sound", nodes, edges: [], depth: 0, incomingMi: null, start: 0, end });
const graph = { layer: 3, edges: [], bfs: [], dfs: [], events: { bfs: [event([0, 1], .3)], dfs: [event([1], .6)] } } as GraphBackboneLayer;
const segment = { layer: 3, start_sec: 20, end_sec: 20.6 };
describe("real layer/traversal clocks", () => {
  it("assigns a shared boundary to the new layer", () => expect(segmentAt([{ layer: 0, start_sec: 0, end_sec: 1 },{ layer: 1, start_sec: 1, end_sec: 2 }],1)?.layer).toBe(1));
  it("keeps gaps as gaps", () => expect(segmentAt([{ layer: 0, start_sec: 0, end_sec: 1 },{ layer: 1, start_sec: 1.2, end_sec: 2 }],1.1)).toBeNull());
  it("quantizes each event duration before accumulating samples", () => expect(sampleAlignedEvents([event([0], .333),event([1], .333)],10).map(e=>[e.start,e.end])).toEqual([[0,.3],[.3,.6]]));
  it("uses the same layer-local origin for the two mix branches", () => expect(traversalMoment(graph,segment,"mix",20.1,22050).active.map(a=>a.branch)).toEqual(["bfs","dfs"]));
  it("does not invent a BFS event when that branch has finished", () => expect(traversalMoment(graph,segment,"mix",20.4,22050).active.map(a=>a.branch)).toEqual(["dfs"]));
  it("stops highlighting during inter-layer gaps", () => expect(traversalMoment(graph,null,"mix",20.4,22050).active).toEqual([]));
  it("disables a mismatched schedule", () => expect(traversalMoment(graph,{...segment,end_sec:21},"mix",20.1,22050).compatible).toBe(false));
  it("does not use a different quantum layer's schedule", () => expect(traversalMoment(graph,{...segment,layer:4},"mix",20.1,22050).active).toEqual([]));
});
