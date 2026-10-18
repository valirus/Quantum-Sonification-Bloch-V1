import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import { resolve, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const readJson = async path => JSON.parse(await readFile(path, "utf8"));
const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const assert = (ok, message) => { if (!ok) throw new Error(message); };
const provenance = await readJson(resolve(root, "docs/UPSTREAM_INTEGRITY.json"));
for (const item of provenance.files) {
  let bytes = await readFile(resolve(root, item.path));
  if (item.path.startsWith("public/")) assert(digest(bytes) === item.source_byte_sha256, `Cambiaron los bytes del recurso suministrado: ${item.path}`);
  if (item.mode === "normalized") bytes = Buffer.from(bytes.toString("utf8").replaceAll("\r\n", "\n"));
  assert(digest(bytes) === item.sha256, `Cambió el archivo de referencia: ${item.path}`);
}

const publicRoot = resolve(root, "public");
function publicPath(url) {
  assert(url.startsWith("/sonification/"), `Recurso ajeno a la colección: ${url}`);
  const path = resolve(publicRoot, `.${url}`);
  const rel = relative(publicRoot, path);
  assert(!rel.startsWith(`..${sep}`) && rel !== "..", `Ruta inválida: ${url}`);
  return path;
}
const study = await readJson(publicPath("/sonification/manifest.json"));
const examples = await readJson(publicPath("/sonification/examples_manifest.json"));
const seeds = [...study.seeds, ...examples.seeds];
assert(seeds.length === 4 && new Set(seeds.map(s => s.id)).size === 4, "Se esperaban la muestra 1060 y tres ejemplos distintos.");
let audioCount = 0;
let largest = { bytes: 0, url: "" };
for (const seed of seeds) {
  const paths = [seed.metadata, seed.layerMetrics, seed.blochDescriptors, seed.gateManifest, seed.graphBackbones, seed.miMatrices, seed.audioAnalysis].filter(Boolean);
  const hashes = [];
  for (const mode of ["bfs", "dfs", "mix"]) {
    assert(seed.audio[mode] && seed.segments[mode], `Falta ${mode} en ${seed.id}.`);
    paths.push(seed.audio[mode], seed.segments[mode]);
    hashes.push(digest(await readFile(publicPath(seed.audio[mode]))));
    audioCount += 1;
  }
  assert(new Set(hashes).size === 3, `Los archivos de audio de ${seed.id} no son distintos.`);
  for (const url of paths) {
    const info = await stat(publicPath(url));
    assert(info.isFile() && info.size > 0, `Recurso ausente o vacío: ${url}`);
    assert(info.size <= 25 * 1024 ** 2, `Recurso mayor que el límite de 25 MiB: ${url}`);
    if (info.size > largest.bytes) largest = { bytes: info.size, url };
  }
}
console.log(`PASS: ${provenance.files.length} archivos de referencia; ${seeds.length} muestras; ${audioCount} audios; todas las rutas disponibles.`);
console.log(`Mayor recurso: ${largest.url}, ${(largest.bytes / 1024 ** 2).toFixed(2)} MiB; límite individual de Pages: 25 MiB.`);
