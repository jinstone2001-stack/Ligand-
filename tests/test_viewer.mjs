import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { MoleculeViewer } from "../web/viewer.js";
import { setupViewer, copies } from "./viewer_fixture.mjs";
const saved = JSON.parse(
  await readFile(
    new URL("../examples/Sn12_Methyl.tinoxo.json", import.meta.url),
    "utf8",
  ),
);
const input = {
  project: saved.project,
  settings: { element_colors: {}, font_size: 11 },
  colors: { Sn: "#aaaaaa", C: "#222222", O: "#ff0000" },
  radii: { Sn: 1.39, C: 0.76, O: 0.66, H: 0.31 },
};
const data = copies(input, 32);
const { view, counts } = setupViewer(data, MoleculeViewer);
view.render();
const initial = counts(),
  points = view.points,
  atomData = view.atomData,
  bonds = view.bondData;
assert.equal(initial.uploads, 2);
for (let i = 0; i < 100; i++) {
  view.interacting = true;
  view.rotate(3, 2);
  view.render();
}
assert.deepEqual(
  counts(),
  initial,
  "camera change uploaded buffers or queried GL attributes",
);
assert.equal(view.stats.geometryBuilds, 1);
assert.equal(view.points, points);
assert.equal(view.atomData, atomData);
assert.equal(view.bondData, bonds);
const scale = view.scale;
view.interacting = false;
view.projectPoints();
const atom = points[0].a,
  r = view.rotation;
const q = [
  atom.x - view.center[0],
  atom.y - view.center[1],
  atom.z - view.center[2],
];
assert.ok(
  Math.abs(
    points[0].x - (400 + scale * (r[0] * q[0] + r[1] * q[1] + r[2] * q[2])),
  ) < 1e-8,
);
data.selection = [atom.id];
view.render();
assert.equal(counts().uploads, 3);
assert.equal(view.stats.geometryBuilds, 1);
assert.equal(view.atomData[7], 1);
data.settings = { ...data.settings, theme: "light", font_size: 16 };
view.render();
assert.equal(
  counts().uploads,
  3,
  "font/theme change rebuilt molecular geometry",
);
data.settings = { ...data.settings, element_colors: { Sn: "#123456" } };
view.render();
assert.equal(view.stats.geometryBuilds, 2);
data.showH = false;
view.render();
assert.ok(view.points.every((p) => p.a.element !== "H"));
const oldCount = view.points.length;
data.project = {
  ...data.project,
  atoms: data.project.atoms.map((a, i) => (i === 0 ? { ...a, x: a.x + 1 } : a)),
};
view.render();
assert.equal(view.points.length, oldCount);
assert.equal(view.stats.geometryBuilds, 4);
console.log(
  "PASS GPU-buffer cache: 100 rotations, selection, fonts, theme, palette, visibility, model update and projection (GL calls mocked).",
);
