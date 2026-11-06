/* CPU submission benchmark only; mock GPU, no browser/FPS claims.
 * python benchmarks/benchmark_web.py BASELINE --output benchmarks/web_20261106.json
 * emits the baseline/current Python data and the shared input JSON.
 * node benchmarks/benchmark_viewer.mjs BASELINE INPUT > results.json
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { performance } from "node:perf_hooks";
import { setupViewer, copies } from "../tests/viewer_fixture.mjs";
const [baseline, inputPath] = process.argv.slice(2);
const input = JSON.parse(await readFile(inputPath, "utf8"));
const versions = {
  before: path.resolve(baseline, "web/viewer.js"),
  after: new URL("../web/viewer.js", import.meta.url).pathname,
};
const results = {
  note: "JavaScript CPU work with GL/canvas calls mocked; not browser/GPU frame timings or FPS.",
  warmup: 10,
  samples: 60,
  cases: [],
};
for (const [version, file] of Object.entries(versions)) {
  const { MoleculeViewer } = await import(pathToFileURL(file));
  for (const n of [1, 8, 32, 64]) {
    const data = copies(input, n),
      { view, counts } = setupViewer(data, MoleculeViewer);
    view.render();
    view.interacting = true;
    for (let i = 0; i < 10; i++) {
      view.rotate(3, 2);
      view.render();
    }
    const begin = counts(),
      times = [];
    for (let i = 0; i < 60; i++) {
      const start = performance.now();
      view.rotate(3, 2);
      view.render();
      times.push(performance.now() - start);
    }
    const end = counts();
    times.sort((a, b) => a - b);
    results.cases.push({
      version,
      atoms: data.project.atoms.length,
      bonds: data.project.bonds.length,
      median_ms: +times[30].toFixed(4),
      p95_ms: +times[56].toFixed(4),
      buffer_uploads: end.uploads - begin.uploads,
      uploaded_bytes: end.bytes - begin.bytes,
    });
  }
}
console.log(JSON.stringify(results, null, 2));
