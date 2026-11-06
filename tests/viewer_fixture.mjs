// Test-only canvas/GL calls: verifies cache behavior, not GPU/browser throughput.
export function setupViewer(data, Viewer) {
  let uploads = 0,
    bytes = 0,
    attributeQueries = 0;
  const ctx = new Proxy({}, { get: (o, k) => o[k] ?? (() => {}) });
  const gl = new Proxy(
    {
      VERTEX_SHADER: 35633,
      FRAGMENT_SHADER: 35632,
      ARRAY_BUFFER: 34962,
      FLOAT: 5126,
      TRIANGLES: 4,
      POINTS: 0,
      COMPILE_STATUS: 35713,
      LINK_STATUS: 35714,
      STATIC_DRAW: 35044,
      createProgram: () => ({ shaders: [] }),
      createShader: (type) => ({ type }),
      shaderSource: (sh, src) => (sh.src = src),
      attachShader: (p, sh) => p.shaders.push(sh),
      getShaderParameter: () => true,
      getProgramParameter: () => true,
      createBuffer: () => ({}),
      getUniformLocation: () => ({}),
      getExtension: () => null,
      getAttribLocation: (p, name) => {
        attributeQueries++;
        const vertex = p.shaders.find((s) => s.type === 35633)?.src || "";
        const names = [...vertex.matchAll(/attribute\s+\w+\s+(\w+)/g)].map(
          (m) => m[1],
        );
        return names.indexOf(name);
      },
      bufferData: (_, array) => {
        uploads++;
        bytes += array.byteLength;
      },
    },
    { get: (o, k) => o[k] ?? (() => {}) },
  );
  const nodes = new Map();
  globalThis.document = {
    getElementById: (id) => {
      if (!nodes.has(id)) nodes.set(id, { style: {}, textContent: "" });
      return nodes.get(id);
    },
  };
  globalThis.window = { devicePixelRatio: 2 };
  globalThis.ResizeObserver = class {
    observe() {}
  };
  globalThis.requestAnimationFrame = () => {};
  const rect = { left: 0, top: 0, width: 800, height: 500 };
  const canvas = {
    width: 1600,
    height: 1000,
    parentElement: {},
    getBoundingClientRect: () => rect,
    getContext: (type) => (type === "webgl" ? gl : ctx),
    addEventListener() {},
    setPointerCapture() {},
  };
  const overlay = { ...canvas, getContext: () => ctx };
  const view = new Viewer(
    canvas,
    overlay,
    () => data,
    () => {},
  );
  view.draw = () => {};
  view.fit();
  return { view, counts: () => ({ uploads, bytes, attributeQueries }) };
}
export function copies(input, count) {
  const project = { atoms: [], bonds: [] };
  for (let k = 0; k < count; k++) {
    const offset = k * 10000;
    for (const a of input.project.atoms)
      project.atoms.push({
        ...a,
        id: a.id + offset,
        x: a.x + (k % 4) * 15,
        y: a.y + Math.floor(k / 4) * 15,
      });
    for (const b of input.project.bonds)
      project.bonds.push({ ...b, a: b.a + offset, b: b.b + offset });
  }
  return {
    ...input,
    project,
    selection: [],
    showH: true,
    labels: false,
    coreOnly: false,
    mode: "multi",
  };
}
