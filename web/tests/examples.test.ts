import { afterEach, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { loadSonificationData, loadSonificationManifest } from "../src/features/quantum-sonification/dataLoaders";
import type { SonificationManifest } from "../src/features/quantum-sonification/types";
const base = "public";
function localFetch() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    try { return new Response(readFileSync(base + url), { status: 200 }); }
    catch { return new Response("not found", { status: 404 }); }
  }));
}
afterEach(() => vi.unstubAllGlobals());
it("keeps the original sample first and adds deterministic examples with no invented seeds", async () => {
  localFetch(); const manifest = await loadSonificationManifest();
  expect(manifest.seeds.map(s => s.id)).toEqual(["seed_001060","bell_2","ghz_3","grover_3"]);
  expect(manifest.seeds.slice(1).every(s => s.seed === null && s.kind === "illustrative" && s.dataset === "didactic_examples_v1")).toBe(true);
  expect(manifest.seeds.slice(1).every(s => s.dataset_version === "1.0.0")).toBe(true);
});
it.each(["bell_2","ghz_3","grover_3"])("loads all actual source assets for %s and preserves multi-qubit gate targets", async id => {
  localFetch(); const manifest = await loadSonificationManifest(); const data = await loadSonificationData(id, manifest);
  expect(data.gates.length).toBe(id === "grover_3" ? 35 : id === "ghz_3" ? 3 : 2);
  expect(data.metadata?.renderer_sha256).toBe("23e747dfe61ff50cc149f7395588fca86488e77f3a18e11fdfa8f87590630ad5");
  expect(data.gates.some(g => g.gate_label === "CX" && g.qubits.split(";").length === 2 || g.gate_label === "CCZ" && g.qubits.split(";").length === 3)).toBe(true);
  expect(data.segments.bfs?.length).toBe(data.metadata!.layers! + 1);
});
it("retains the original 220-operation RQC alongside the examples", async () => {
  localFetch(); const data = await loadSonificationData("seed_001060", await loadSonificationManifest());
  expect(data.gates.length).toBe(220);expect(data.metadata?.num_qubits).toBe(15);expect(data.seed.kind).toBeUndefined();
});
it("rejects unknown multi-qubit example labels instead of silently drawing them", async () => {
  localFetch(); const manifest = await loadSonificationManifest();
  const original = globalThis.fetch;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const response = await original(url); if (!url.endsWith("bell_2/gate_manifest.csv")) return response;
    return new Response((await response.text()).replace(/CX/g,"BAD"));
  }));
  await expect(loadSonificationData("bell_2", manifest)).rejects.toThrow("Destinos de compuerta inválidos");
});
