// Orthographic browser renderer. Molecular coordinates/graphs are never modified.
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
    this.scale = 20;
    this.range = 10;
    this.points = [];
    this.pending = false;
    this.gl = canvas.getContext("webgl", {
      alpha: true,
      antialias: true,
      preserveDrawingBuffer: true,
    });
    if (this.gl) this.initGL();
    else this.ctx = canvas.getContext("2d");
    document.getElementById("rendererBadge").textContent = this.gl
      ? "WEBGL · ORTHOGRAPHIC"
      : "CANVAS · ORTHOGRAPHIC";
    new ResizeObserver(() => this.draw()).observe(canvas.parentElement);
    canvas.addEventListener("contextmenu", (e) => e.preventDefault());
    canvas.addEventListener("pointerdown", (e) => this.down(e));
    canvas.addEventListener("pointermove", (e) => this.move(e));
    canvas.addEventListener("pointerup", (e) => this.up(e));
    canvas.addEventListener("pointercancel", () => {
      this.drag = null;
      document.getElementById("boxSelect").style.display = "none";
    });
    canvas.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        this.zoom = Math.max(
          0.08,
          Math.min(20, this.zoom * Math.exp(-e.deltaY * 0.001)),
        );
        this.draw();
      },
      { passive: false },
    );
  }
  initGL() {
    const gl = this.gl;
    const compile = (type, src) => {
      const sh = gl.createShader(type);
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS))
        throw Error(gl.getShaderInfoLog(sh));
      return sh;
    };
    const vs =
      "attribute vec3 position;attribute vec3 color;attribute float size;varying vec3 col;void main(){gl_Position=vec4(position,1.0);gl_PointSize=size;col=color;}";
    const fs =
      "precision mediump float;varying vec3 col;uniform bool sphere;void main(){float light=1.0;if(sphere){vec2 q=gl_PointCoord*2.0-1.0;float d=dot(q,q);if(d>1.0)discard;vec3 n=vec3(q.x,-q.y,sqrt(1.0-d));light=.3+.7*max(0.0,dot(n,normalize(vec3(-.4,.6,1.0))));light+=.16*pow(max(0.0,dot(n,normalize(vec3(-.4,.6,1.0)))),24.0);}gl_FragColor=vec4(col*light,1.0);}";
    this.program = gl.createProgram();
    gl.attachShader(this.program, compile(gl.VERTEX_SHADER, vs));
    gl.attachShader(this.program, compile(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(this.program);
    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS))
      throw Error("WebGL program link failed");
    this.buffer = gl.createBuffer();
    this.loc = {};
    for (const n of ["position", "color", "size"])
      this.loc[n] = gl.getAttribLocation(this.program, n);
    this.sphere = gl.getUniformLocation(this.program, "sphere");
  }
  fit() {
    const { project } = this.getData();
    if (!project?.atoms.length) return;
    const aa = project.atoms;
    this.center = [0, 1, 2].map(
      (k) => aa.reduce((s, a) => s + [a.x, a.y, a.z][k], 0) / aa.length,
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
    const b = this.canvas.getBoundingClientRect();
    this.scale = (Math.min(b.width, b.height) * 0.32) / (this.range + 1);
    this.zoom = 1;
    this.pan = [0, 0];
    this.draw();
  }
  rotate(dx, dy) {
    const turn = (axis, t) => {
      let [x, y, z] = axis,
        c = Math.cos(t),
        s = Math.sin(t),
        v = 1 - c;
      return [
        c + x * x * v,
        x * y * v - z * s,
        x * z * v + y * s,
        y * x * v + z * s,
        c + y * y * v,
        y * z * v - x * s,
        z * x * v - y * s,
        z * y * v + x * s,
        c + z * z * v,
      ];
    };
    const mul = (a, b) =>
      Array.from({ length: 9 }, (_, i) => {
        let r = Math.floor(i / 3),
          c = i % 3;
        return (
          a[r * 3] * b[c] + a[r * 3 + 1] * b[c + 3] + a[r * 3 + 2] * b[c + 6]
        );
      });
    this.rotation = mul(
      turn([1, 0, 0], dy * 0.008),
      mul(turn([0, 1, 0], dx * 0.008), this.rotation),
    );
  }
  down(e) {
    this.canvas.setPointerCapture(e.pointerId);
    const b = this.canvas.getBoundingClientRect();
    this.drag = {
      x: e.clientX - b.left,
      y: e.clientY - b.top,
      lastX: e.clientX,
      lastY: e.clientY,
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
    const b = this.canvas.getBoundingClientRect(),
      x = e.clientX - b.left,
      y = e.clientY - b.top;
    if (Math.hypot(x - d.x, y - d.y) > 4) d.moved = true;
    if (d.box) {
      const box = document.getElementById("boxSelect");
      Object.assign(box.style, {
        display: "block",
        left: Math.min(x, d.x) + "px",
        top: Math.min(y, d.y) + "px",
        width: Math.abs(x - d.x) + "px",
        height: Math.abs(y - d.y) + "px",
      });
    } else if (d.pan) {
      this.pan[0] += dx;
      this.pan[1] += dy;
      this.draw();
    } else if (d.moved) {
      this.rotate(dx, dy);
      this.draw();
    }
  }
  up(e) {
    if (!this.drag) return;
    const d = this.drag;
    this.drag = null;
    const b = this.canvas.getBoundingClientRect(),
      x = e.clientX - b.left,
      y = e.clientY - b.top;
    document.getElementById("boxSelect").style.display = "none";
    if (d.box && d.moved) {
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
    } else if (!d.moved && !d.pan) {
      const hit = this.points
        .filter((p) => Math.hypot(p.x - x, p.y - y) <= Math.max(p.r, 8))
        .sort((a, b) => b.z - a.z)[0];
      this.onSelect(hit ? [hit.a.id] : [], d.shift, false);
    }
  }
  draw() {
    if (this.pending) return;
    this.pending = true;
    requestAnimationFrame(() => {
      this.pending = false;
      this.render();
    });
  }
  bondSegments(bonds, map) {
    const segments = [],
      width = Math.max(1, Math.min(4, this.scale * this.zoom * 0.09));
    for (const bond of bonds) {
      const p = map.get(bond.a),
        q = map.get(bond.b);
      const dx = q.x - p.x,
        dy = q.y - p.y,
        length = Math.hypot(dx, dy) || 1;
      const nx = -dy / length,
        ny = dx / length;
      const lines =
        bond.order === 3
          ? [-3 * width, 0, 3 * width].map((offset) => ({ offset }))
          : bond.order === 2
            ? [-1.8 * width, 1.8 * width].map((offset) => ({ offset }))
            : bond.order === 1.5
              ? [
                  { offset: -1.6 * width },
                  { offset: 1.6 * width, dashed: true },
                ]
              : [{ offset: 0, dashed: bond.kind === "coordinate" }];
      for (const line of lines) {
        const point = (t) => ({
          x: p.x + dx * t + nx * line.offset,
          y: p.y + dy * t + ny * line.offset,
          z: p.z + (q.z - p.z) * t,
        });
        const n = line.dashed
          ? Math.max(2, Math.min(64, Math.ceil(length / 5)))
          : 1;
        for (let i = 0; i < n; i++) {
          if (line.dashed && i % 2) continue;
          const start = i / n,
            end = (i + 1) / n;
          for (const [a, b] of start < 0.5 && end > 0.5
            ? [
                [start, 0.5],
                [0.5, end],
              ]
            : [[start, end]])
            segments.push({
              p: point(a),
              q: point(b),
              color: (a + b) / 2 < 0.5 ? p.color : q.color,
              width,
            });
        }
      }
    }
    return segments;
  }
  render() {
    const {
      project,
      selection,
      settings,
      showH,
      labels,
      coreOnly,
      colors,
      radii,
    } = this.getData();
    if (!project) return;
    const b = this.canvas.getBoundingClientRect(),
      w = b.width,
      h = b.height,
      dpr = window.devicePixelRatio || 1;
    if (!w || !h) return;
    for (const cv of [this.canvas, this.overlay])
      if (
        cv.width !== Math.round(w * dpr) ||
        cv.height !== Math.round(h * dpr)
      ) {
        cv.width = Math.round(w * dpr);
        cv.height = Math.round(h * dpr);
      }
    const r = this.rotation,
      s = this.scale * this.zoom,
      chosen = new Set(selection),
      rgb = (hex) => {
        const m = /^#([a-f\d]{6})$/i.exec(hex || "");
        const n = parseInt(m ? m[1] : "999999", 16);
        return [(n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
      };
    this.points = project.atoms
      .filter((a) => (showH || a.element !== "H") && (!coreOnly || a.core))
      .map((a) => {
        const x = a.x - this.center[0],
          y = a.y - this.center[1],
          z = a.z - this.center[2];
        return {
          a,
          x: w / 2 + this.pan[0] + s * (r[0] * x + r[1] * y + r[2] * z),
          y: h / 2 + this.pan[1] - s * (r[3] * x + r[4] * y + r[5] * z),
          z: r[6] * x + r[7] * y + r[8] * z,
          r: Math.max(2, (radii[a.element] || 1) * s * 0.38),
          color:
            a.color ||
            settings.element_colors?.[a.element] ||
            colors[a.element] ||
            "#999999",
        };
      });
    const map = new Map(this.points.map((p) => [p.a.id, p])),
      bonds = project.bonds.filter((b) => map.has(b.a) && map.has(b.b));
    const segments = this.bondSegments(bonds, map);
    this.last = { w, h, map, bonds, segments };
    if (this.gl) {
      const gl = this.gl;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST);
      gl.depthFunc(gl.LEQUAL);
      gl.useProgram(this.program);
      const pack = (x, y, z, color, size) => [
        (x / w) * 2 - 1,
        1 - (y / h) * 2,
        -z / (this.range * 4 + 10),
        ...rgb(color),
        size * dpr,
      ];
      let lines = [];
      const quad = (p, q, color, width, offset = 0) => {
        const dx = q.x - p.x,
          dy = q.y - p.y,
          len = Math.hypot(dx, dy) || 1,
          nx = -dy / len,
          ny = dx / len;
        const pp = { x: p.x + nx * offset, y: p.y + ny * offset, z: p.z },
          qq = { x: q.x + nx * offset, y: q.y + ny * offset, z: q.z };
        const v = (a, sign) =>
          pack(a.x + nx * width * sign, a.y + ny * width * sign, a.z, color, 1);
        lines.push(
          ...v(pp, 1),
          ...v(pp, -1),
          ...v(qq, 1),
          ...v(qq, 1),
          ...v(pp, -1),
          ...v(qq, -1),
        );
      };
      for (const segment of segments)
        quad(segment.p, segment.q, segment.color, segment.width);
      const paint = (arr, mode, sphere) => {
        if (!arr.length) return;
        gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.DYNAMIC_DRAW);
        for (const [n, count, offset] of [
          ["position", 3, 0],
          ["color", 3, 12],
          ["size", 1, 24],
        ]) {
          gl.enableVertexAttribArray(this.loc[n]);
          gl.vertexAttribPointer(
            this.loc[n],
            count,
            gl.FLOAT,
            false,
            28,
            offset,
          );
        }
        gl.uniform1i(this.sphere, sphere);
        gl.drawArrays(mode, 0, arr.length / 7);
      };
      paint(lines, gl.TRIANGLES, false);
      let atoms = [];
      for (const p of this.points)
        atoms.push(...pack(p.x, p.y, p.z, p.color, p.r * 2));
      paint(atoms, gl.POINTS, true);
    } else {
      const ctx = this.ctx;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const layers = [];
      for (const seg of segments)
        layers.push({
          z: (seg.p.z + seg.q.z) / 2,
          fn: () => {
            ctx.lineWidth = seg.width * 2;
            ctx.strokeStyle = seg.color;
            ctx.beginPath();
            ctx.moveTo(seg.p.x, seg.p.y);
            ctx.lineTo(seg.q.x, seg.q.y);
            ctx.stroke();
          },
        });
      for (const p of this.points)
        layers.push({
          z: p.z,
          fn: () => {
            const g = ctx.createRadialGradient(
              p.x - p.r * 0.3,
              p.y - p.r * 0.35,
              p.r * 0.05,
              p.x,
              p.y,
              p.r,
            );
            g.addColorStop(0, "#ffffff");
            g.addColorStop(0.3, p.color);
            g.addColorStop(1, p.color);
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fill();
          },
        });
      layers.sort((a, b) => a.z - b.z).forEach((o) => o.fn());
    }
    const ctx = this.overlay.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.textAlign = "center";
    ctx.font = `${Math.max(11, settings.font_size || 11)}px Arial`;
    for (const p of this.points) {
      if (chosen.has(p.a.id)) {
        ctx.strokeStyle = settings.selection || "#58d6c5";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r + 4, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillStyle = settings.selection || "#58d6c5";
        ctx.fillText(String(selection.indexOf(p.a.id) + 1), p.x, p.y - p.r - 8);
      }
      if (labels) {
        ctx.fillStyle =
          settings.text_colors?.label ||
          (settings.theme === "light" ? "#243647" : "#dce5ef");
        ctx.fillText(p.a.element + p.a.id, p.x, p.y + p.r + 15);
      }
    }
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
  png() {
    const out = document.createElement("canvas");
    out.width = this.canvas.width;
    out.height = this.canvas.height;
    const ctx = out.getContext("2d");
    ctx.fillStyle =
      this.getData().settings.theme === "light" ? "#eef3f7" : "#0d151f";
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.drawImage(this.canvas, 0, 0);
    ctx.drawImage(this.overlay, 0, 0);
    return new Promise((resolve) => out.toBlob(resolve, "image/png"));
  }
  svg() {
    this.render();
    const { w, h, segments } = this.last,
      { settings, selection, labels } = this.getData();
    const escape = (s) =>
      String(s)
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;");
    const bg = settings.theme === "light" ? "#eef3f7" : "#0d151f";
    const shapes = [`<rect width="100%" height="100%" fill="${bg}"/>`];
    for (const seg of segments)
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
