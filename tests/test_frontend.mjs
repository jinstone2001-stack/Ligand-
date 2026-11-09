/* DOM integration tests against the real local Python API. No browser/GPU claim.
 * npm install --no-save --package-lock=false jsdom@26
 * TINOXO_TEST_URL=http://127.0.0.1:PORT TINOXO_TEST_TOKEN=... node tests/test_frontend.mjs
 */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
const require = createRequire(import.meta.url);
const { JSDOM } = require(
  require.resolve("jsdom", {
    paths: [process.env.TINOXO_JSDOM_PATH || process.cwd(), process.cwd()],
  }),
);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const base = process.env.TINOXO_TEST_URL,
  token = process.env.TINOXO_TEST_TOKEN;
if (!base || !token)
  throw Error(
    "Set TINOXO_TEST_URL and TINOXO_TEST_TOKEN for an isolated test workspace.",
  );
const dom = new JSDOM(
  await readFile(path.join(root, "web/index.html"), "utf8"),
  { url: base + "/#token=" + token, pretendToBeVisual: true },
);
const win = dom.window,
  $ = (id) => win.document.getElementById(id);
const errors = [];
let copied = "",
  viewer = null;
Object.assign(globalThis, {
  window: win,
  document: win.document,
  location: win.location,
  history: win.history,
  sessionStorage: win.sessionStorage,
  FormData: win.FormData,
  FileReader: win.FileReader,
});
Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: win.navigator,
});
Object.defineProperty(win.navigator, "clipboard", {
  value: {
    writeText: async (s) => {
      copied = s;
    },
  },
});
win.HTMLDialogElement.prototype.showModal = function () {
  this.setAttribute("open", "");
};
win.HTMLDialogElement.prototype.close = function () {
  this.removeAttribute("open");
  this.dispatchEvent(new win.Event("close"));
};
win.HTMLElement.prototype.getBoundingClientRect = function () {
  return { left: 0, top: 0, right: 800, bottom: 500, width: 800, height: 500 };
};
win.HTMLCanvasElement.prototype.setPointerCapture = function () {};
const context = {
  setTransform() {},
  clearRect() {},
  beginPath() {},
  moveTo() {},
  lineTo() {},
  stroke() {},
  arc() {},
  fill() {},
  fillText() {},
  fillRect() {},
  drawImage() {},
  createRadialGradient() {
    return { addColorStop() {} };
  },
};
win.HTMLCanvasElement.prototype.getContext = function (type) {
  return type === "2d" ? { ...context } : null;
};
win.HTMLCanvasElement.prototype.toBlob = function (callback) {
  callback(new Blob(["simulated PNG"], { type: "image/png" }));
};
const downloads = [];
win.HTMLAnchorElement.prototype.click = function () {
  downloads.push({ name: this.download, url: this.href });
};
globalThis.ResizeObserver = class {
  observe() {}
};
globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 0);
const realFetch = globalThis.fetch;
globalThis.fetch = (url, options) => realFetch(new URL(url, base), options);
win.addEventListener("error", (e) => errors.push(e.error));
const viewerModule = await import(
  pathToFileURL(path.join(root, "web/viewer.js"))
);
const originalRender = viewerModule.MoleculeViewer.prototype.render;
viewerModule.MoleculeViewer.prototype.render = function () {
  viewer = this;
  return originalRender.call(this);
};
await import(pathToFileURL(path.join(root, "web/app.js")));
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, message, timeout = 12000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await check()) return;
    await wait(30);
  }
  throw Error(message + "; toast=" + $("toast").textContent + "; connection=" + $("connection").textContent);
}
const click = (el) => {
  assert.ok(el, "missing element");
  if (el.click) el.click();
  else el.dispatchEvent(new win.MouseEvent("click", { bubbles: true }));
};
const set = (el, value) => {
  assert.ok(el);
  el.value = value;
  el.dispatchEvent(new win.Event("change", { bubbles: true }));
};
const close = () => click(document.querySelector('[data-close="modal"]'));
async function action(name) {
  click(document.querySelector(`[data-action="${name}"]`));
  await wait(60);
}
async function current() {
  return (
    await realFetch(base + "/api/state", {
      headers: { "X-Tinoxo-Token": token },
    })
  ).json();
}
let count = 0;
function passed(name) {
  count++;
  console.log("PASS", name);
}
await until(
  () => $("connection").classList.contains("hidden"),
  "initial connection",
);
assert.equal($("atomCount").textContent, "38");
assert.equal($("formula").textContent, "H6O20Sn12");
await until(() => viewer, "first molecular frame");
passed("initial authenticated workspace and molecular renderer");
assert.equal(location.hash, "");
assert.equal(sessionStorage.getItem("tinoxo-token"), token);
passed("token is retained per tab and removed from address bar");
click(document.querySelector('[data-core="3"]'));
await action("reset");
await until(() => $("atomCount").textContent === "6", "Sn3 reset");
click(document.querySelector('[data-core="12"]'));
await action("reset");
await until(() => $("atomCount").textContent === "38", "Sn12 reset");
passed("core choice and resets");
await action("selectSn");
assert.equal($("selectedCount").textContent, "12");
await action("deselect");
assert.equal($("selectedCount").textContent, "0");
passed("all Sn selection and clearing");
await until(() => viewer.points.length === 38, "viewer points");
const scale = viewer.scale;
const original = JSON.stringify((await current()).project.atoms);
viewer.rotate(50, 20);
viewer.render();
assert.equal(viewer.scale, scale);
$("molecule").dispatchEvent(
  new win.WheelEvent("wheel", { deltaY: -100, cancelable: true }),
);
assert.ok(viewer.zoom > 1);
assert.equal(JSON.stringify((await current()).project.atoms), original);
passed("rotation and wheel preserve molecular graph and fit scale");
click(document.querySelector('[data-mode="single"]'));
const point = viewer.points
  .filter((p) => p.a.element === "Sn")
  .sort((a, b) => b.z - a.z)[0];
for (const type of ["pointerdown", "pointerup"])
  $("molecule").dispatchEvent(
    new win.MouseEvent(type, {
      clientX: point.x,
      clientY: point.y,
      button: 0,
      bubbles: true,
    }),
  );
assert.equal($("selectedCount").textContent, "1");
passed("canvas picking selects one atom");
await action("attach");
await until(() => $("attachSmiles"), "attachment dialog");
set($("attachSmiles"), "CCN");
set($("attachMode"), "coordinate");
click($("chooseAttachAtom"));
await until(
  () =>
    $("picker").open && document.querySelector('#picker circle[data-atom="2"]'),
  "atom picker SVG",
);
click(document.querySelector('#picker circle[data-atom="2"]'));
assert.ok($("chosenAtom").textContent.includes("N3"));
click($("confirmAtom"));
await until(
  () => $("attachAtomLabel").textContent.includes("#3"),
  "confirmed attachment atom",
);
click($("applyAttach"));
await until(
  () => $("atomCount").textContent === "48",
  "asynchronous N attachment",
  20000,
);
let saved = await current();
const slot = saved.project.slots.find((s) => s.custom);
assert.equal(
  saved.project.atoms.find((a) => a.id === slot.anchor).element,
  "N",
);
assert.equal(slot.attachmentIndex, 2);
passed("SVG atom choice flows through real RDKit attachment");
await action("undo");
await until(() => $("atomCount").textContent === "38", "attachment undo");
await action("redo");
await until(() => $("atomCount").textContent === "48", "attachment redo");
passed("asynchronous edit undo and redo");
await action("gaussian");
await until(() => $("generateGaussian"), "Gaussian dialog");
const method = document.querySelector('[data-g="method"]');
set(method, "wB97XD");
assert.ok(
  [...document.querySelectorAll('[data-g="method"]')].every(
    (el) => el.value === "wB97XD",
  ),
);
click($("generateGaussian"));
await until(
  () => $("gaussianText").value.includes("wB97XD/GenECP"),
  "Gaussian route",
);
click(document.querySelector('[data-gtab="custom"]'));
set(document.querySelector('[data-basis="Sn"]'), "SDD");
set(document.querySelector('[data-ecp="Sn"]'), "SDD");
click($("generateGaussian"));
await until(() => $("gaussianText").value.includes("Sn 0\nSDD"), "mixed SDD");
click($("uniformBasis"));
click($("downloadGaussian"));
await until(
  () => downloads.some((d) => d.name === "tinoxo.gjf"),
  "Gaussian download",
);
close();
passed("shared Gaussian settings, element bases, uniform reset and download");
await action("appearance");
const initialSize = document.documentElement.style.fontSize;
set($("fontSize"), "16");
click($("previewAppearance"));
assert.ok(
  parseFloat(document.documentElement.style.fontSize) > parseFloat(initialSize),
);
click($("cancelAppearance"));
assert.equal(document.documentElement.style.fontSize, initialSize);
await action("appearance");
set($("theme"), "light");
click($("saveAppearance"));
await until(() => !$("modal").open, "save appearance");
assert.ok(document.body.classList.contains("light"));
assert.equal(document.body.style.getPropertyValue("--fg"), "");
passed("font preview cancellation and persistent theme change");
await action("library");
set($("ligandSearch"), "n1ccccc1");
$("ligandSearch").dispatchEvent(new win.Event("input"));
await wait(30);
assert.ok($("libraryTable").textContent.includes("n1ccccc1"));
set($("favoriteName"), "테스트 아민");
set($("favoriteSmiles"), "CCN");
set($("favoriteMode"), "coordinate");
click($("favoriteSave"));
await until(
  () => $("toast").textContent.includes("내 SMILES를 저장"),
  "favorite save",
);
close();
assert.ok(
  (await current()).settings.favorites.some((v) => v.name === "테스트 아민"),
);
passed("library search and saved custom SMILES");
await action("bank");
set($("bankName"), "테스트 구조");
click(document.querySelector('[data-bank-op="store"]'));
await until(
  () => $("bankTable").textContent.includes("테스트 구조"),
  "bank store",
);
click(document.querySelector('[data-bank-op="copy"]'));
await until(
  () => $("bankTable").querySelectorAll("[data-bank-id]").length === 2,
  "bank copy",
);
close();
passed("named structure storage and copying");
await action("geometry");
set($("measureIds"), "1 2");
click($("measureNow"));
await until(
  () => $("measureResult").textContent.includes("거리"),
  "distance measurement",
);
click($("geometryCsv"));
await until(
  () => downloads.some((d) => d.name === "tinoxo.csv"),
  "geometry CSV",
);
close();
passed("geometry analysis and CSV export");
await action("bonds");
await until(() => $("auditTable").querySelector("tbody tr"), "bond audit");
assert.ok($("auditTable").textContent.includes("기존 명시 결합"));
const oldBonds = Number($("bondCount").textContent);
set($("bondIds"), "1 2");
set($("bondKind"), "coordinate");
click($("manualBond"));
await until(
  () => Number($("bondCount").textContent) === oldBonds + 1,
  "manual bond update",
);
close();
passed("bond audit and explicit bond editing");
await action("resonance");
await until(() => $("resonanceImage").querySelector("svg"), "resonance SVG");
assert.ok($("resonanceSummary").textContent.includes("공명식"));
close();
passed("resonance enumeration and vector diagram");
await action("contactSettings");
set($("contactMode"), "minimum");
set($("contactMinimum"), "2.1");
click($("applyContacts"));
await until(() => !$("modal").open, "contact settings");
assert.equal((await current()).project.metadata.contactCriteria.minimum, 2.1);
passed("contact criteria editing and refresh");
await action("copy");
assert.ok(copied.startsWith("48\n"));
await action("save");
click($("downloadProject"));
await until(
  () => downloads.some((d) => d.name === "tinoxo.tinoxo.json"),
  "project download",
);
close();
passed("XYZ clipboard and complete workspace download");
const project = (await current()).project;
project.title = "<img src=x onerror=alert(1)>";
const file = new win.File([JSON.stringify(project)], "project.json", {
  type: "application/json",
});
Object.defineProperty($("fileInput"), "files", {
  configurable: true,
  value: [file],
});
$("fileInput").dispatchEvent(new win.Event("change"));
await until(
  () => $("structureTitle").textContent === project.title,
  "file import",
);
assert.equal($("structureTitle").children.length, 0);
passed("file import and literal rendering of untrusted titles");
// The form event must be prevented synchronously; a queued guard used to navigate.
await action("selectSn");
click(document.querySelector('[data-mode="single"]'));
viewer.render();
const atomPoint = viewer.points
  .filter((p) => p.a.element === "Sn")
  .sort((a, b) => b.z - a.z)[0];
for (const type of ["pointerdown", "pointerup"])
  $("molecule").dispatchEvent(
    new win.MouseEvent(type, {
      clientX: atomPoint.x,
      clientY: atomPoint.y,
      button: 0,
      bubbles: true,
    }),
  );
$("atomForm").elements.x.value = "1.234";
const submit = new win.Event("submit", { bubbles: true, cancelable: true });
$("atomForm").dispatchEvent(submit);
assert.equal(submit.defaultPrevented, true);
await until(
  () => $("atomForm").elements.x.value === "1.234",
  "atom form result",
);
await wait(150);
assert.ok((await current()).project.atoms.some((a) => a.x === 1.234));
passed("atom form commits and prevents navigation synchronously");
// Settings should keep the immutable model, coordinate text node and selection rows.
await until(() => viewer.cachedProject, "model cache");
const modelBefore = viewer.cachedProject,
  xyzNode = $("coordinates").firstChild,
  rowBefore = $("atomList").querySelector("tr[data-id]");
const revBeforeSettings = (await current()).revision;
set($("ff"), $("ff").value === "UFF" ? "MMFF94" : "UFF");
await until(
  async () => (await current()).revision === revBeforeSettings + 1,
  "settings commit",
);
await wait(100);
assert.equal(viewer.cachedProject, modelBefore);
assert.equal($("coordinates").firstChild, xyzNode);
assert.equal($("atomList").querySelector("tr[data-id]"), rowBefore);
passed("settings updates retain model and unchanged DOM nodes");
const revBeforeBurst = (await current()).revision;
const fixedButton = document.querySelector('[data-action="fixed"]');
for (let i = 0; i < 3; i++) click(fixedButton);
await until(
  async () => (await current()).revision === revBeforeBurst + 3,
  "queued rapid edits",
);
assert.ok(!$("toast").textContent.includes("다른 탭"));
await until(
  () => $("saveStatus").textContent === "자동 저장됨",
  "background save status",
);
passed("rapid edits serialize revisions and report completed autosave");
await action("geometry");
await until(
  () => $("geometryTable").querySelector('[data-page="next"]'),
  "geometry pagination",
);
assert.ok($("geometryTable").querySelectorAll("tbody tr").length <= 150);
click($("geometryTable").querySelector('[data-page="next"]'));
assert.equal(
  $("geometryTable").querySelector("[data-geometry]").dataset.geometry,
  "150",
);
click($("geometryTable").querySelector("[data-geometry]"));
await until(
  () => $("measureResult").textContent.length > 0,
  "paged geometry selection",
);
close();
passed("large geometry lists page without losing row selection");
// v5 shared scope controls are grounded in the actual backend plan.
const scopeProject = (await current()).project;
const coreCount = scopeProject.atoms.filter(a => a.core).length;
assert.equal($("scope").options.length, 4);
assert.equal($("respectFixed").checked, false);
set($("scope"), "core_only");
await until(() => $("scopeCounts").textContent.includes(`이동 ${coreCount}`), "core-only preview");
await action("selectMoving");
assert.equal(Number($("selectedCount").textContent), coreCount);
set($("scope"), "all");
await until(() => $("scopeCounts").textContent.includes(`이동 ${scopeProject.atoms.length}`), "all-free preview");
$("respectFixed").checked = true;
$("respectFixed").dispatchEvent(new win.Event("change"));
const manualCount = scopeProject.atoms.filter(a => a.fixed).length;
await until(() => $("scopeCounts").textContent.includes(`고정 ${manualCount}`), "manual fixed override");
set($("scope"), "rigid");
assert.ok($("scopeDescription").textContent.includes("강체") || $("scopeDescription").textContent.includes("회전·이동"));
passed("four scope previews, atom selection and manual-fixed override");
await action("contactSettings");
set($("contactMode"), "minimum");
assert.equal($("contactVdw").closest("label").hidden, true);
assert.equal($("contactMinimum").closest("label").hidden, false);
set($("contactMode"), "radii");
assert.equal($("contactMinimum").disabled, true);
assert.equal($("contactVdw").closest("label").hidden, false);
$("contactMinimum").value = ""; // Hidden invalid field must never be submitted.
click($("applyContacts"));
await until(() => !$("modal").open, "inactive contact input ignored");
assert.equal((await current()).settings.contact.minimum, 2.1);
passed("contact methods show/validate active fields and retain inactive settings");
await action("copy");
const oldCopy = copied;
let latest = await current();
const editedId = latest.project.atoms[0].id;
const external = await realFetch(base + "/api/edit/atom", {
  method: "POST", headers: { "X-Tinoxo-Token": token, "Content-Type": "application/json" },
  body: JSON.stringify({ revision: latest.revision, ids: [editedId], values: { ...latest.project.atoms[0], x: 7.123456789 } }),
});
assert.equal(external.status, 200);
await action("copy");
await until(() => copied.includes("7.123456789"), "copy fetches latest cross-tab revision");
assert.notEqual(copied, oldCopy);
passed("XYZ clipboard refreshes after an external revision");
const normalWrite = navigator.clipboard.writeText;
navigator.clipboard.writeText = async () => { throw Error("clipboard denied"); };
document.execCommand = command => {
  assert.equal(command, "copy"); copied = document.activeElement.value; return true;
};
copied = "stale";
await action("copy");
await until(() => copied.includes("7.123456789"), "clipboard legacy fallback");
document.execCommand = () => false;
const downloadCount = downloads.length;
await action("copy");
await until(() => $("copyText"), "manual clipboard fallback");
assert.ok($("copyText").value.includes("7.123456789"));
assert.equal(downloads.length, downloadCount);
close(); navigator.clipboard.writeText = normalWrite;
passed("denied clipboard uses fresh copy fallback or selectable manual text");
$("respectFixed").checked = false;
set($("scope"), "core_only");
set($("optSteps"), "10");
const beforeCleanup = (await current()).project;
await action("cleanup");
await until(async () => (await current()).job?.status === "done", "scope-aware cleanup", 20000);
await until(() => $("jobPercent").textContent === "100%", "completed percentage");
latest = await current();
assert.equal(latest.project.metadata.lastCleanup.scope, "core_only");
assert.equal(latest.project.metadata.lastCleanup.respectFixed, false);
for (const a of beforeCleanup.atoms.filter(a => !a.core)) {
  const b = latest.project.atoms.find(b => b.id === a.id);
  assert.deepEqual([b.x,b.y,b.z], [a.x,a.y,a.z]);
}
assert.equal($("calculationResult").classList.contains("hidden"), false);
assert.ok($("calculationResult").textContent.includes("임의 단위"));
passed("cleanup receives scope and displays percentage, units and completion result");
assert.deepEqual(errors, []);
console.log(
  `DOM integration: ${count} scenarios passed (Canvas mocked; browser/GPU not tested).`,
);
dom.window.close();
process.exit(0);
