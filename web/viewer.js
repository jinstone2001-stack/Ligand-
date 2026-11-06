// Geometry is uploaded once. Camera changes update only GPU uniforms.
export const POINT_VERTEX = `
attribute vec3 position; attribute vec3 color; attribute float radius; attribute float selected;
uniform mat3 rotation; uniform vec3 center; uniform vec2 viewport; uniform vec2 pan;
uniform float scale; uniform float depth; uniform float dpr;
varying vec3 col; varying float sel; varying float bodyRatio; varying float gapRatio;
void main(){vec3 p=rotation*(position-center);float r=max(2.0,radius*scale);float outer=r+selected*4.0;
gl_Position=vec4((p.xy*scale+vec2(pan.x,-pan.y))*2.0/viewport,-p.z/depth,1.0);
gl_PointSize=outer*2.0*dpr;col=color;sel=selected;bodyRatio=r/outer;gapRatio=(r+2.0)/outer;}`;
export const POINT_FRAGMENT = `
precision mediump float; varying vec3 col;varying float sel;varying float bodyRatio;varying float gapRatio;
uniform vec3 selectionColor;uniform bool detail;
void main(){vec2 q=gl_PointCoord*2.0-1.0;float d=length(q);if(d>1.0)discard;
if(sel>.5&&d>bodyRatio){if(d<gapRatio)discard;gl_FragColor=vec4(selectionColor,1.0);return;}
q/=bodyRatio;float light=.85;if(detail){vec3 n=vec3(q.x,-q.y,sqrt(max(0.0,1.0-dot(q,q))));float diffuse=max(0.0,dot(n,normalize(vec3(-.4,.6,1.0))));light=.3+.7*diffuse+.16*pow(diffuse,24.0);}
gl_FragColor=vec4(col*light,1.0);}`;
export const BOND_VERTEX = `
attribute vec3 position;attribute vec3 endpoint;attribute vec3 color;attribute float fraction;attribute float side;attribute float offset;
uniform mat3 rotation;uniform vec3 center;uniform vec2 viewport;uniform vec2 pan;uniform float scale;uniform float depth;
varying vec3 col;void main(){vec3 p=rotation*(position-center);vec3 q=rotation*(endpoint-center);vec3 v=mix(p,q,fraction);
vec2 delta=(q.xy-p.xy)*vec2(1.0,-1.0);vec2 normal=vec2(-delta.y,delta.x)/max(length(delta),.0001);
vec2 shift=normal*(side+offset)*clamp(scale*.09,1.0,4.0);
gl_Position=vec4((v.xy*scale+vec2(pan.x,-pan.y)+shift*vec2(1.0,-1.0))*2.0/viewport,-v.z/depth,1.0);col=color;}`;
export const BOND_FRAGMENT = `precision mediump float;varying vec3 col;void main(){gl_FragColor=vec4(col,1.0);}`;
const rgb = (hex) => {
  const m = /^#([a-f\d]{6})$/i.exec(hex || "");
  const n = parseInt(m ? m[1] : "999999", 16);
  return [(n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};
const mul = (a, b) => [
  a[0] * b[0] + a[1] * b[3] + a[2] * b[6],
  a[0] * b[1] + a[1] * b[4] + a[2] * b[7],
  a[0] * b[2] + a[1] * b[5] + a[2] * b[8],
  a[3] * b[0] + a[4] * b[3] + a[5] * b[6],
  a[3] * b[1] + a[4] * b[4] + a[5] * b[7],
  a[3] * b[2] + a[4] * b[5] + a[5] * b[8],
  a[6] * b[0] + a[7] * b[3] + a[8] * b[6],
  a[6] * b[1] + a[7] * b[4] + a[8] * b[7],
  a[6] * b[2] + a[7] * b[5] + a[8] * b[8],
];
export class MoleculeViewer {
  constructor(canvas, overlay, getData, onSelect) {
    this.canvas = canvas;
    this.overlay = overlay;
    this.getData = getData;
    this.onSelect = onSelect;
    this.rotation = [
      0.939, 0.058, 0.339, 0.058, 0.944, -0.324, -0.339, 0.324, 0.883,
    ];
    this.zoom = 1;
    this.pan = [0, 0];
    this.center = [0, 0, 0];
    this.range = 10;
    this.scale = 20;
    this.points = [];
    this.pending = false;
    this.pointsDirty = true;
    this.interacting = false;
    this.lastFrame = 0;
    this.sprites = new Map();
    this.stats = { geometryBuilds: 0, bufferUploads: 0, frames: 0 };
    this.gl = canvas.getContext("webgl", {
      alpha: false,
      antialias: false,
      preserveDrawingBuffer: false,
    });
    if (this.gl) this.initGL();
    else this.ctx = canvas.getContext("2d");
    document.getElementById("rendererBadge").textContent = this.gl
      ? "WEBGL · CACHED"
      : "CANVAS · CACHED";
    this.size = canvas.getBoundingClientRect();
    new ResizeObserver(() => {
      this.size = canvas.getBoundingClientRect();
      this.pointsDirty = true;
      this.draw();
    }).observe(canvas.parentElement);
    canvas.addEventListener("contextmenu", (e) => e.preventDefault());
    canvas.addEventListener("pointerdown", (e) => this.down(e));
    canvas.addEventListener("pointermove", (e) => this.move(e));
    canvas.addEventListener("pointerup", (e) => this.up(e));
    canvas.addEventListener("pointercancel", () => {
      this.drag = null;
      this.interacting = false;
      document.getElementById("boxSelect").style.display = "none";
      this.draw();
    });
    canvas.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        this.zoom = Math.max(
          0.08,
          Math.min(20, this.zoom * Math.exp(-e.deltaY * 0.001)),
        );
        this.pointsDirty = true;
        this.interacting = true;
        clearTimeout(this.settleTimer);
        this.settleTimer = setTimeout(() => {
          if (!this.drag) {
            this.interacting = false;
            this.draw();
          }
        }, 130);
        this.draw();
      },
      { passive: false },
    );
    canvas.addEventListener("webglcontextlost", (e) => {
      e.preventDefault();
      this.lost = true;
    });
    canvas.addEventListener("webglcontextrestored", () => {
      this.lost = false;
      this.initGL();
      this.cachedProject = null;
      this.draw();
    });
  }
  initGL() {
    const gl = this.gl;
    const make = (vertex, fragment, spec, stride) => {
      const program = gl.createProgram();
      for (const [type, src] of [
        [gl.VERTEX_SHADER, vertex],
        [gl.FRAGMENT_SHADER, fragment],
      ]) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, src);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
          throw Error(gl.getShaderInfoLog(shader));
        gl.attachShader(program, shader);
        gl.deleteShader(shader);
      }
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS))
        throw Error(gl.getProgramInfoLog(program));
      const uniforms = {};
      for (const n of [
        "rotation",
        "center",
        "viewport",
        "pan",
        "scale",
        "depth",
        "dpr",
        "selectionColor",
        "detail",
      ])
        uniforms[n] = gl.getUniformLocation(program, n);
      const attributes = spec
        .map(([name, n, off]) => [gl.getAttribLocation(program, name), n, off])
        .filter(([loc]) => loc >= 0);
      return { program, uniforms, attributes, stride };
    };
    this.pointGL = make(
      POINT_VERTEX,
      POINT_FRAGMENT,
      [
        ["position", 3, 0],
        ["color", 3, 12],
        ["radius", 1, 24],
        ["selected", 1, 28],
      ],
      32,
    );
    this.bondGL = make(
      BOND_VERTEX,
      BOND_FRAGMENT,
      [
        ["position", 3, 0],
        ["endpoint", 3, 12],
        ["color", 3, 24],
        ["fraction", 1, 36],
        ["side", 1, 40],
        ["offset", 1, 44],
      ],
      48,
    );
    this.enabledAttributes = new Set();
    this.atomBuffer = gl.createBuffer();
    this.bondBuffer = gl.createBuffer();
    try {
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      this.software =
        !!ext &&
        /swiftshader|llvmpipe|software/i.test(
          gl.getParameter(ext.UNMASKED_RENDERER_WEBGL),
        );
    } catch {
      this.software = false;
    }
  }
  fit() {
    const { project } = this.getData();
    if (!project?.atoms.length) return;
    const aa = project.atoms;
    this.center = [0, 1, 2].map(
      (k) => aa.reduce((sum, a) => sum + [a.x, a.y, a.z][k], 0) / aa.length,
    );
    this.range = Math.max(
      2,
      ...aa.map((a) =>
        Math.hypot(
          a.x - this.center[0],
          a.y - this.center[1],
          a.z - this.center[2],
        ),
      ),
    );
    this.scale =
      (Math.min(this.size.width, this.size.height) * 0.32) / (this.range + 1);
    this.zoom = 1;
    this.pan = [0, 0];
    this.pointsDirty = true;
    this.draw();
  }
  rotate(dx, dy) {
    const a = dx * 0.008,
      b = dy * 0.008,
      ca = Math.cos(a),
      sa = Math.sin(a),
      cb = Math.cos(b),
      sb = Math.sin(b);
    this.rotation = mul(
      [1, 0, 0, 0, cb, -sb, 0, sb, cb],
      mul([ca, 0, sa, 0, 1, 0, -sa, 0, ca], this.rotation),
    );
    this.pointsDirty = true;
  }
  down(e) {
    this.canvas.setPointerCapture(e.pointerId);
    const rect = this.canvas.getBoundingClientRect();
    clearTimeout(this.settleTimer);
    this.drag = {
      rect,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      lastX: e.clientX,
      lastY: e.clientY,
      startX: e.clientX,
      startY: e.clientY,
      moved: false,
      pan: e.button === 2 || e.button === 1,
      box: this.getData().mode === "box" && !e.altKey && e.button === 0,
      shift: e.shiftKey,
    };
  }
  move(e) {
    if (!this.drag) return;
    const d = this.drag,
      dx = e.clientX - d.lastX,
      dy = e.clientY - d.lastY;
    d.lastX = e.clientX;
    d.lastY = e.clientY;
    if (Math.hypot(e.clientX - d.startX, e.clientY - d.startY) > 4)
      d.moved = true;
    if (d.box) {
      const x = e.clientX - d.rect.left,
        y = e.clientY - d.rect.top;
      Object.assign(document.getElementById("boxSelect").style, {
        display: "block",
        left: Math.min(x, d.x) + "px",
        top: Math.min(y, d.y) + "px",
        width: Math.abs(x - d.x) + "px",
        height: Math.abs(y - d.y) + "px",
      });
    } else if (d.moved) {
      this.interacting = true;
      if (d.pan) {
        this.pan[0] += dx;
        this.pan[1] += dy;
        this.pointsDirty = true;
      } else this.rotate(dx, dy);
      this.draw();
    }
  }
  up(e) {
    if (!this.drag) return;
    const d = this.drag;
    this.drag = null;
    this.interacting = false;
    const x = e.clientX - d.rect.left,
      y = e.clientY - d.rect.top;
    document.getElementById("boxSelect").style.display = "none";
    this.projectPoints();
    if (d.box && d.moved)
      this.onSelect(
        this.points
          .filter(
            (p) =>
              p.x >= Math.min(x, d.x) &&
              p.x <= Math.max(x, d.x) &&
              p.y >= Math.min(y, d.y) &&
              p.y <= Math.max(y, d.y),
          )
          .map((p) => p.a.id),
        d.shift,
        true,
      );
    else if (!d.moved && !d.pan) {
      let hit = null;
      for (const p of this.points)
        if (
          Math.hypot(p.x - x, p.y - y) <= Math.max(p.r, 8) &&
          (!hit || p.z > hit.z)
        )
          hit = p;
      this.onSelect(hit ? [hit.a.id] : [], d.shift, false);
    }
    this.draw();
  }
  draw() {
    if (this.pending) return;
    this.pending = true;
    const frame = (t) => {
      const now = Number.isFinite(t) ? t : performance.now(),
        fps = Math.min(
          60,
          Math.max(15, this.getData().settings.viewer_fps || 30),
        );
      if (now - this.lastFrame < 1000 / fps) {
        requestAnimationFrame(frame);
        return;
      }
      this.pending = false;
      this.lastFrame = now;
      this.render();
    };
    requestAnimationFrame(frame);
  }
  syncScene(data) {
    const { project, settings, showH, coreOnly, colors, radii } = data;
    if (this.cachedSettings !== settings) {
      this.cachedSettings = settings;
      this.colorSignature = JSON.stringify(settings.element_colors || colors);
    }
    const key = `${showH}|${coreOnly}|${this.colorSignature}`;
    if (this.cachedProject === project && this.sceneKey === key) return false;
    this.cachedProject = project;
    this.sceneKey = key;
    this.stats.geometryBuilds++;
    this.sprites.clear();
    this.visibleAtoms = project.atoms.filter(
      (a) => (showH || a.element !== "H") && (!coreOnly || a.core),
    );
    this.atomIndex = new Map(this.visibleAtoms.map((a, i) => [a.id, i]));
    this.points = this.visibleAtoms.map((a) => ({
      a,
      x: 0,
      y: 0,
      z: 0,
      r: 0,
      baseRadius: (radii[a.element] || 1) * 0.38,
      color:
        a.color ||
        settings.element_colors?.[a.element] ||
        colors[a.element] ||
        "#999999",
    }));
    this.atomData = new Float32Array(this.points.length * 8);
    for (let i = 0; i < this.points.length; i++) {
      const p = this.points[i],
        a = p.a;
      this.atomData.set(
        [a.x, a.y, a.z, ...rgb(p.color), p.baseRadius, 0],
        i * 8,
      );
    }
    this.bonds = project.bonds.filter(
      (b) => this.atomIndex.has(b.a) && this.atomIndex.has(b.b),
    );
    this.bondParts = [];
    const packed = [];
    for (const b of this.bonds) {
      const i = this.atomIndex.get(b.a),
        j = this.atomIndex.get(b.b),
        p = this.points[i],
        q = this.points[j];
      const lines =
        b.order === 3
          ? [{ offset: -3 }, { offset: 0 }, { offset: 3 }]
          : b.order === 2
            ? [{ offset: -1.8 }, { offset: 1.8 }]
            : b.order === 1.5
              ? [{ offset: -1.6 }, { offset: 1.6, dashed: true }]
              : [{ offset: 0, dashed: b.kind === "coordinate" }];
      for (const line of lines) {
        const n = line.dashed
          ? Math.max(
              4,
              Math.min(
                24,
                Math.ceil(
                  Math.hypot(p.a.x - q.a.x, p.a.y - q.a.y, p.a.z - q.a.z) * 3,
                ),
              ),
            )
          : 1;
        for (let k = 0; k < n; k++) {
          if (line.dashed && k % 2) continue;
          const lo = k / n,
            hi = (k + 1) / n;
          const parts =
            lo < 0.5 && hi > 0.5
              ? [
                  [lo, 0.5],
                  [0.5, hi],
                ]
              : [[lo, hi]];
          for (const [start, end] of parts) {
            const color = (start + end) / 2 < 0.5 ? p.color : q.color;
            this.bondParts.push({
              i,
              j,
              start,
              end,
              offset: line.offset,
              color,
            });
            for (const [t, side] of [
              [start, 1],
              [start, -1],
              [end, 1],
              [end, 1],
              [start, -1],
              [end, -1],
            ])
              packed.push(
                p.a.x,
                p.a.y,
                p.a.z,
                q.a.x,
                q.a.y,
                q.a.z,
                ...rgb(color),
                t,
                side,
                line.offset,
              );
          }
        }
      }
    }
    this.bondData = new Float32Array(packed);
    this.selectionKey = null;
    this.pointsDirty = true;
    if (this.gl) {
      const gl = this.gl;
      gl.bindBuffer(gl.ARRAY_BUFFER, this.bondBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, this.bondData, gl.STATIC_DRAW);
      this.stats.bufferUploads++;
    }
    return true;
  }
  syncSelection(selection) {
    const key = selection.join(",");
    if (key === this.selectionKey) return;
    this.selectionKey = key;
    const selected = new Set(selection);
    for (let i = 0; i < this.points.length; i++)
      this.atomData[i * 8 + 7] = selected.has(this.points[i].a.id) ? 1 : 0;
    if (this.gl) {
      const gl = this.gl;
      gl.bindBuffer(gl.ARRAY_BUFFER, this.atomBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, this.atomData, gl.STATIC_DRAW);
      this.stats.bufferUploads++;
    }
  }
  projectPoints() {
    if (!this.pointsDirty) return;
    const r = this.rotation,
      s = this.scale * this.zoom,
      w = this.size.width,
      h = this.size.height;
    for (const p of this.points) {
      const a = p.a,
        x = a.x - this.center[0],
        y = a.y - this.center[1],
        z = a.z - this.center[2];
      p.x = w / 2 + this.pan[0] + s * (r[0] * x + r[1] * y + r[2] * z);
      p.y = h / 2 + this.pan[1] - s * (r[3] * x + r[4] * y + r[5] * z);
      p.z = r[6] * x + r[7] * y + r[8] * z;
      p.r = Math.max(2, p.baseRadius * s);
    }
    this.pointsDirty = false;
  }
  uniforms(bundle, dpr, data) {
    const gl = this.gl,
      u = bundle.uniforms,
      r = this.rotation;
    gl.useProgram(bundle.program);
    gl.uniformMatrix3fv(
      u.rotation,
      false,
      new Float32Array([r[0], r[3], r[6], r[1], r[4], r[7], r[2], r[5], r[8]]),
    );
    gl.uniform3fv(u.center, this.center);
    gl.uniform2f(u.viewport, this.size.width, this.size.height);
    gl.uniform2fv(u.pan, this.pan);
    gl.uniform1f(u.scale, this.scale * this.zoom);
    gl.uniform1f(u.depth, this.range * 4 + 10);
    gl.uniform1f(u.dpr, dpr);
    gl.uniform3fv(u.selectionColor, rgb(data.settings.selection || "#58d6c5"));
    gl.uniform1i(u.detail, !this.interacting);
  }
  paintGL(dpr, data) {
    const gl = this.gl;
    const bg =
      data.settings.theme === "light" ? [0.93, 0.95, 0.97] : [0.05, 0.08, 0.12];
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(...bg, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    const draw = (bundle, buffer, count, mode) => {
      this.uniforms(bundle, dpr, data);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      const active = new Set(bundle.attributes.map(([loc]) => loc));
      for (const loc of this.enabledAttributes)
        if (!active.has(loc)) gl.disableVertexAttribArray(loc);
      for (const [loc, n, off] of bundle.attributes) {
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, n, gl.FLOAT, false, bundle.stride, off);
      }
      this.enabledAttributes = active;
      gl.drawArrays(mode, 0, count);
    };
    draw(this.bondGL, this.bondBuffer, this.bondData.length / 12, gl.TRIANGLES);
    draw(this.pointGL, this.atomBuffer, this.points.length, gl.POINTS);
  }
  bondSegments() {
    const width = Math.max(1, Math.min(4, this.scale * this.zoom * 0.09));
    return this.bondParts.map((part) => {
      const p = this.points[part.i],
        q = this.points[part.j],
        dx = q.x - p.x,
        dy = q.y - p.y,
        len = Math.hypot(dx, dy) || 1,
        nx = -dy / len,
        ny = dx / len,
        point = (t) => ({
          x: p.x + dx * t + nx * part.offset * width,
          y: p.y + dy * t + ny * part.offset * width,
          z: p.z + (q.z - p.z) * t,
        });
      return {
        p: point(part.start),
        q: point(part.end),
        color: part.color,
        width,
      };
    });
  }
  paintCanvas(dpr, data) {
    this.projectPoints();
    const ctx = this.ctx,
      w = this.size.width,
      h = this.size.height;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const order = [];
    for (const seg of this.bondSegments())
      order.push({ z: (seg.p.z + seg.q.z) / 2, seg });
    for (const p of this.points) order.push({ z: p.z, p });
    order.sort((a, b) => a.z - b.z);
    for (const item of order) {
      if (item.seg) {
        const s = item.seg;
        ctx.lineWidth = s.width * 2;
        ctx.strokeStyle = s.color;
        ctx.beginPath();
        ctx.moveTo(s.p.x, s.p.y);
        ctx.lineTo(s.q.x, s.q.y);
        ctx.stroke();
      } else {
        const p = item.p;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }
  render(force = false) {
    const data = this.getData();
    if (!data.project || this.lost) return;
    this.syncScene(data);
    this.syncSelection(data.selection);
    const { width: w, height: h } = this.size;
    if (!w || !h) return;
    this.stats.frames++;
    const actual = window.devicePixelRatio || 1,
      quality = data.settings.viewer_quality || "auto";
    const dpr =
      quality === "high"
        ? Math.min(actual, 2)
        : quality === "low" || this.interacting || this.software
          ? 1
          : Math.min(actual, 1.5);
    if (
      this.canvas.width !== Math.round(w * dpr) ||
      this.canvas.height !== Math.round(h * dpr)
    ) {
      this.canvas.width = Math.round(w * dpr);
      this.canvas.height = Math.round(h * dpr);
    }
    const overlayDpr = Math.min(actual, 2);
    if (
      this.overlay.width !== Math.round(w * overlayDpr) ||
      this.overlay.height !== Math.round(h * overlayDpr)
    ) {
      this.overlay.width = Math.round(w * overlayDpr);
      this.overlay.height = Math.round(h * overlayDpr);
    }
    if (this.gl) this.paintGL(dpr, data);
    else this.paintCanvas(dpr, data);
    const needsLabels =
      force ||
      (!this.interacting && (data.labels || data.selection.length > 0));
    if (needsLabels) this.projectPoints();
    const ctx = this.overlay.getContext("2d");
    ctx.setTransform(overlayDpr, 0, 0, overlayDpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (needsLabels) {
      const selected = new Map(data.selection.map((id, i) => [id, i + 1]));
      ctx.textAlign = "center";
      ctx.font = `${Math.max(11, data.settings.font_size || 11)}px Arial`;
      for (const p of this.points) {
        if (selected.has(p.a.id)) {
          if (!this.gl) {
            ctx.strokeStyle = data.settings.selection || "#58d6c5";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r + 4, 0, Math.PI * 2);
            ctx.stroke();
          }
          ctx.fillStyle = data.settings.selection || "#58d6c5";
          ctx.fillText(String(selected.get(p.a.id)), p.x, p.y - p.r - 8);
        }
        if (data.labels) {
          ctx.fillStyle =
            data.settings.text_colors?.label ||
            (data.settings.theme === "light" ? "#243647" : "#dce5ef");
          ctx.fillText(p.a.element + p.a.id, p.x, p.y + p.r + 15);
        }
      }
    }
    const r = this.rotation;
    ctx.textAlign = "left";
    ctx.font = "10px Arial";
    const ox = w - 48,
      oy = h - 52;
    for (const [k, color, label] of [
      [0, "#ef9191", "X"],
      [1, "#91d5ab", "Y"],
      [2, "#8faeea", "Z"],
    ]) {
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(ox + 24 * r[k], oy - 24 * r[3 + k]);
      ctx.stroke();
      ctx.fillText(label, ox + 29 * r[k], oy - 29 * r[3 + k]);
    }
  }
  async png() {
    this.render(true);
    const out = document.createElement("canvas");
    out.width = this.canvas.width;
    out.height = this.canvas.height;
    const ctx = out.getContext("2d");
    ctx.fillStyle =
      this.getData().settings.theme === "light" ? "#eef3f7" : "#0d151f";
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.drawImage(this.canvas, 0, 0);
    ctx.drawImage(this.overlay, 0, 0, out.width, out.height);
    return new Promise((resolve) => out.toBlob(resolve, "image/png"));
  }
  svg() {
    this.render(true);
    this.projectPoints();
    const { settings, selection, labels } = this.getData(),
      w = this.size.width,
      h = this.size.height,
      escape = (s) =>
        String(s)
          .replaceAll("&", "&amp;")
          .replaceAll('"', "&quot;")
          .replaceAll("<", "&lt;");
    const shapes = [
      `<rect width="100%" height="100%" fill="${settings.theme === "light" ? "#eef3f7" : "#0d151f"}"/>`,
    ];
    for (const seg of this.bondSegments())
      shapes.push(
        `<line x1="${seg.p.x}" y1="${seg.p.y}" x2="${seg.q.x}" y2="${seg.q.y}" stroke="${escape(seg.color)}" stroke-width="${seg.width * 2}"/>`,
      );
    for (const p of [...this.points].sort((a, b) => a.z - b.z)) {
      shapes.push(
        `<circle cx="${p.x}" cy="${p.y}" r="${p.r}" fill="${escape(p.color)}"/>`,
      );
      if (selection.includes(p.a.id))
        shapes.push(
          `<circle cx="${p.x}" cy="${p.y}" r="${p.r + 4}" fill="none" stroke="${escape(settings.selection || "#58d6c5")}" stroke-width="2"/>`,
        );
      if (labels)
        shapes.push(
          `<text x="${p.x}" y="${p.y + p.r + 15}" fill="${settings.theme === "light" ? "#243647" : "#dce5ef"}" font-family="Arial,sans-serif" font-size="${Math.max(11, settings.font_size || 11)}" text-anchor="middle">${p.a.element}${p.a.id}</text>`,
        );
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">${shapes.join("")}</svg>`;
  }
}
