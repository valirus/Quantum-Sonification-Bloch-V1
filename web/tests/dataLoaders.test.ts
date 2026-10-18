import { afterEach, describe, expect, it, vi } from "vitest";
import { loadSonificationData } from "../src/features/quantum-sonification/dataLoaders";
import type { SonificationManifest } from "../src/features/quantum-sonification/types";
const manifest: SonificationManifest={version:"explicit-test",dataset:"unit-test-only",seeds:[{id:"one",seed:1,label:"fixture",metadata:"meta",layerMetrics:"layers",blochDescriptors:"bloch",gateManifest:"gates",miMatrices:"mi",segments:{bfs:"segments"},audio:{bfs:"tone.wav"}}]};
function install(overrides:Record<string,unknown>={}) {
 const files:Record<string,unknown>={meta:{num_qubits:1,layers:0,seed:1,preferred_root:0},layers:"layer,mean_bloch_radius,mean_von_neumann_entropy,central_cut_entanglement_entropy_normalized,total_mutual_information,positive_edge_density,backbone_edges,backbone_components\n0,1,0,0,0,0,0,1",bloch:"layer,qubit,x,y,z,theta,phi,r,linear_entropy,von_neumann_entropy\n0,0,0,0,1,0,0,1,0,0",gates:"layer_added,operation_index,gate_label,qubits",segments:"layer,start_sec,end_sec\n0,0,1",mi:{layers:[{layer:0,matrix:[[0]]}]},...overrides};
 vi.stubGlobal("fetch",vi.fn(async(path:string)=>new Response(typeof files[path]==="string"?files[path] as string:JSON.stringify(files[path]),{status:files[path]===undefined?404:200})));
}
afterEach(()=>vi.unstubAllGlobals());
describe("data fail closed instead of inventing scientific zeros",()=>{
 it("loads an explicit complete zero-depth fixture",async()=>{install();const data=await loadSonificationData("one",manifest);expect(data.bloch[0].r).toBe(1);expect(data.metadata?.layers).toBe(0);});
 it("rejects a missing radius column",async()=>{install({bloch:"layer,qubit,x,y,z,theta,phi,linear_entropy,von_neumann_entropy\n0,0,0,0,1,0,0,0,0"});await expect(loadSonificationData("one",manifest)).rejects.toThrow("Falta el valor r");});
 it("rejects inconsistent Cartesian and radius descriptors",async()=>{install({bloch:"layer,qubit,x,y,z,theta,phi,r,linear_entropy,von_neumann_entropy\n0,0,0,0,1,0,0,0.2,0,0"});await expect(loadSonificationData("one",manifest)).rejects.toThrow("radio de Bloch");});
 it("rejects a non-zero MI diagonal",async()=>{install({mi:{layers:[{layer:0,matrix:[[0.1]]}]}});await expect(loadSonificationData("one",manifest)).rejects.toThrow("diagonal cero");});
 it("keeps an unavailable MI file as null with a warning",async()=>{install({mi:undefined});const data=await loadSonificationData("one",manifest);expect(data.miMatrices).toBeNull();expect(data.warnings.some(s=>s.includes("Matrices MI"))).toBe(true);});
 it("rejects a nonconsecutive gate order",async()=>{install({gates:"layer_added,operation_index,gate_label,qubits\n0,4,√X,0"});await expect(loadSonificationData("one",manifest)).rejects.toThrow("Orden de compuertas");});
 it("rejects negative or reversed audio intervals",async()=>{install({segments:"layer,start_sec,end_sec\n0,1,0"});await expect(loadSonificationData("one",manifest)).rejects.toThrow("Segmentos BFS");});
});
