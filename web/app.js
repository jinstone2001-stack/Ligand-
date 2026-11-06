import { MoleculeViewer } from "./viewer.js";
const $ = (id) => document.getElementById(id),
  h = (s) =>
    String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let token =
  new URLSearchParams(location.hash.slice(1)).get("token") ||
  sessionStorage.getItem("tinoxo-token") ||
  "";
if (token) {
  sessionStorage.setItem("tinoxo-token", token);
  history.replaceState(null, "", location.pathname + location.search);
}
let state = null,
  config = null,
  selection = [],
  core = 12,
  mode = "multi",
  viewer,
  jobPolling = false,
  selectedSlot = null;
const modal = $("modal"),
  picker = $("picker");
let modalEpoch = 0;
modal.addEventListener("close", () => {
  modalEpoch++;
});
function toast(message, error = false) {
  $("toast").textContent = message;
  $("toast").classList.toggle("error", error);
  $("toast").style.display = "block";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").style.display = "none"), 6500);
  $("status").textContent = message;
}
const guard =
  (fn) =>
  (...args) => {
    try {
      return Promise.resolve(fn(...args)).catch((error) => {
        console.error(error);
        toast(error.message, true);
      });
    } catch (error) {
      toast(error.message, true);
    }
  };
async function api(path, data) {
  const response = await fetch("/api/" + path, {
    method: data === undefined ? "GET" : "POST",
    headers: {
      "X-Tinoxo-Token": token,
      ...(data === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  let result = await response.json();
  if (!response.ok) {
    if (response.status === 409) await refresh();
    throw Error(result.error || "서버 요청 실패");
  }
  return result;
}
// Merge versioned sections so unchanged models keep their GPU/DOM caches.
let editQueue = Promise.resolve(),
  saveTimer = null;
const rendered = {};
function mergeState(incoming) {
  state = { ...state, ...incoming };
  const ids = new Set(state.project.atoms.map((a) => a.id));
  selection = selection.filter((i) => ids.has(i));
}
async function refresh(fit = false) {
  const known = encodeURIComponent(JSON.stringify(state?.versions || {}));
  mergeState(await api("state?known=" + known));
  render();
  if (fit) viewer.fit();
  if (state.job?.status === "running") guard(() => pollJob())();
}
function edit(action, data = {}, fit = false) {
  const ids = [...selection];
  const work = editQueue.then(async () => {
    const result = await api("edit/" + action, {
      revision: state.revision,
      known: state.versions,
      ids,
      ...data,
    });
    mergeState(result.state || result);
    if (result.result?.selection) selection = result.result.selection;
    render();
    if (fit) viewer.fit();
    return result.result;
  });
  // Later clicks use the revision returned by the previous edit.
  editQueue = work.catch(() => {});
  return work;
}
async function task(action, data = {}) {
  await editQueue;
  if (state.job?.status === "running")
    throw Error("진행 중인 계산을 완료하거나 취소하세요.");
  const job = await api("task/" + action, {
    revision: state.revision,
    ids: selection,
    ff: $("ff").value,
    ...data,
  });
  state.job = job;
  renderJob();
  modal.close();
  await pollJob(true);
}
async function pollJob(wait = false) {
  if (jobPolling) {
    if (wait) await jobPolling;
    return;
  }
  jobPolling = (async () => {
    while (true) {
      const data = await api("job");
      state.job = data.job;
      state.save = data.save;
      renderJob();
      renderSave();
      if (!data.job || data.job.status !== "running") {
        await refresh(true);
        if (data.job?.status === "error") throw Error(data.job.error);
        if (data.job?.status === "cancelled") toast("계산을 취소했습니다.");
        else if (data.job) toast("계산 결과를 적용했습니다.");
        break;
      }
      await delay(350);
    }
  })();
  try {
    await jobPolling;
  } finally {
    jobPolling = false;
  }
}
function renderJob() {
  const running = state.job?.status === "running";
  $("jobStatus").textContent = running ? state.job.progress : "";
  $("cancelJob").classList.toggle("hidden", !running);
}
function renderSave() {
  const save = state.save || { state: "saved" };
  $("saveStatus").textContent =
    save.state === "pending"
      ? "저장 중…"
      : save.state === "error"
        ? "자동 저장 실패 · JSON을 다운로드하세요"
        : "자동 저장됨";
  $("saveStatus").title = save.error || "";
  $("saveStatus").classList.toggle("save-error", save.state === "error");
  clearTimeout(saveTimer);
  if (save.state === "pending")
    saveTimer = setTimeout(
      guard(async () => {
        const info = await api("job");
        state.save = info.save;
        renderSave();
      }),
      650,
    );
}
function xyz() {
  return (
    `${state.project.atoms.length}\n${state.project.title}\n` +
    state.project.atoms
      .map(
        (a) =>
          `${a.element.padEnd(3)} ${[a.x, a.y, a.z].map((v) => v.toFixed(9)).join("  ")}`,
      )
      .join("\n") +
    "\n"
  );
}
function applyAppearance() {
  const s = state.settings;
  document.body.classList.toggle("light", s.theme === "light");
  document.documentElement.style.fontSize =
    (14 * (Number(s.font_size) || 11)) / 11 + "px";
  document.body.style.fontFamily = `${s.english_font === "Calibri" ? "Calibri" : "Arial"}, '${s.korean_font === "굴림" ? "Gulim" : "Malgun Gothic"}', NanumGothic, sans-serif`;
  const names = {
    body: "fg",
    heading: "heading",
    muted: "muted",
    button: "button-text",
    input: "input-text",
    status: "accent",
    warning: "danger",
  };
  for (const [key, v] of Object.entries(names)) {
    document.body.style.removeProperty("--" + v);
    if (/^#[0-9a-f]{6}$/i.test(s.text_colors?.[key] || ""))
      document.body.style.setProperty("--" + v, s.text_colors[key]);
  }
}
function table(headers, rows, attrs = () => "", empty = "항목이 없습니다.") {
  return rows.length
    ? `<table><thead><tr>${headers.map((v) => `<th>${h(v)}</th>`).join("")}</tr></thead><tbody>${rows.map((row, i) => `<tr ${attrs(row, i)}>${row.map((v) => `<td>${h(v)}</td>`).join("")}</tr>`).join("")}</tbody></table>`
    : `<div class="empty">${h(empty)}</div>`;
}
// Keep long inspection lists responsive without dropping any rows.
function pagedTable(
  id,
  headers,
  rows,
  attrs = () => "",
  bind = () => {},
  empty = "항목이 없습니다.",
) {
  const host = $(id),
    size = 150;
  if (!host) return;
  let page = 0;
  const fill = () => {
    const start = page * size,
      pages = Math.max(1, Math.ceil(rows.length / size));
    host.innerHTML =
      table(
        headers,
        rows.slice(start, start + size),
        (r, i) => attrs(r, start + i),
        empty,
      ) +
      (pages > 1
        ? `<div class="inline table-pager"><button data-page="prev" ${page === 0 ? "disabled" : ""}>이전</button><span>${page + 1} / ${pages} · 총 ${rows.length}개</span><button data-page="next" ${page + 1 === pages ? "disabled" : ""}>다음</button></div>`
        : "");
    host.querySelectorAll("[data-page]").forEach(
      (b) =>
        (b.onclick = () => {
          page += b.dataset.page === "next" ? 1 : -1;
          fill();
          host.scrollTop = 0;
        }),
    );
    bind(host);
  };
  fill();
}
function atomMap() {
  if (rendered.atomSource !== state.project) {
    rendered.atomSource = state.project;
    rendered.atoms = new Map(state.project.atoms.map((a) => [a.id, a]));
  }
  return rendered.atoms;
}
function renderLazyPanels() {
  const p = state.project;
  if (
    !$("coordinates").classList.contains("hidden") &&
    rendered.coordinates !== p
  ) {
    $("coordinates").textContent = xyz();
    rendered.coordinates = p;
  }
  if (!$("slotList").classList.contains("hidden") && rendered.slots !== p) {
    $("slotsTable").innerHTML = table(
      ["자리", "종류", "SMILES"],
      p.slots.map((s) => [s.id, s.kind, s.smiles || "—"]),
      (r) => `data-slot="${h(r[0])}"`,
    );
    rendered.slots = p;
  }
}
function render() {
  const p = state.project;
  if (rendered.settings !== state.settings) {
    applyAppearance();
    $("ff").value = state.settings.ff || "MMFF94";
    rendered.settings = state.settings;
  }
  if (rendered.project !== p) {
    $("structureTitle").textContent = p.title;
    $("viewMetrics").textContent =
      `${p.atoms.length} atoms · ${p.bonds.length} bonds · 고정 배율`;
    $("formula").textContent = state.formula;
    $("atomCount").textContent = p.atoms.length;
    $("bondCount").textContent = p.bonds.length;
    $("totalCharge").textContent = p.metadata.totalCharge ?? "미지정";
    rendered.project = p;
  }
  const log = state.logs.join("\n");
  if (rendered.log !== log) {
    $("log").textContent = log;
    rendered.log = log;
  }
  $("undo").disabled = !state.undo;
  $("redo").disabled = !state.redo;
  renderLazyPanels();
  renderSelection();
  renderJob();
  renderSave();
  viewer.draw();
}
function renderSelection() {
  const key = selection.join(",");
  if (
    rendered.selectionProject === state.project &&
    rendered.selectionKey === key
  )
    return;
  rendered.selectionProject = state.project;
  rendered.selectionKey = key;
  const aa = atomMap();
  $("selectedCount").textContent = selection.length;
  $("selectionBadge").textContent = selection.length;
  $("atomList").innerHTML =
    table(
      ["ID", "원소", "고정"],
      selection
        .slice(0, 100)
        .map((i) => [i, aa.get(i).element, aa.get(i).fixed ? "●" : "—"]),
      (r) => `data-id="${r[0]}"`,
      "구조에서 원자를 선택하세요.",
    ) +
    (selection.length > 100
      ? `<p class="hint">처음 100개 표시 · 선택한 ${selection.length}개 모두에 작업을 적용합니다.</p>`
      : "");
  const a = selection.length === 1 ? aa.get(selection[0]) : null;
  for (const input of $("atomForm").querySelectorAll("input"))
    input.value = a ? (a[input.name] ?? 0) : "";
  viewer.draw();
}
function select(ids, append = false, box = false) {
  if (append) selection = [...new Set([...selection, ...ids])];
  else if (mode === "multi" && !box && ids.length === 1) {
    const i = ids[0];
    selection = selection.includes(i)
      ? selection.filter((v) => v !== i)
      : [...selection, i];
  } else selection = [...new Set(ids)];
  renderSelection();
}
function selectExact(ids) {
  selection = [...new Set(ids)];
  renderSelection();
}
function show(title, html) {
  modalEpoch++;
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  if (!modal.open) modal.showModal();
  return modalEpoch;
}
function btn(text, id, primary = false) {
  return `<button id="${id}" class="${primary ? "primary" : ""}">${h(text)}</button>`;
}
function options(values, value) {
  return values
    .map(
      (v) =>
        `<option value="${h(Array.isArray(v) ? v[0] : v)}" ${String(Array.isArray(v) ? v[0] : v) === String(value) ? "selected" : ""}>${h(Array.isArray(v) ? v[1] : v)}</option>`,
    )
    .join("");
}
function inputField(label, id, value = "", type = "text", extra = "") {
  return `<label>${h(label)}<input id="${id}" value="${h(value)}" type="${type}" ${extra}></label>`;
}
function selectField(label, id, values, value) {
  return `<label>${h(label)}<select id="${id}">${options(values, value)}</select></label>`;
}
function on(id, fn, event = "click") {
  $(id).addEventListener(event, guard(fn));
}
function download(content, name, mime = "text/plain;charset=utf-8") {
  const blob =
      content instanceof Blob ? content : new Blob([content], { type: mime }),
    url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
async function exportKind(kind, opts = {}) {
  const out = await api("query/export", { kind, ...opts });
  download(out.text, out.filename, out.mime);
  toast("파일을 다운로드했습니다.");
}
function exportDialog() {
  show(
    "구조 / 이미지 / 프로젝트 내보내기",
    `<p class="content-note">현재 구조와 화면의 배향을 내보냅니다. 브라우저 다운로드는 접속한 PC에 저장됩니다.</p><div class="form-grid">${[
      ["project", "전체 프로젝트 JSON"],
      ["xyz", "XYZ 좌표"],
      ["sdf", "SDF V3000 / 결합 정보"],
      ["pdb", "PDB 좌표 / CONECT"],
      ["report", "검사 보고서 JSON"],
      ["csv", "전체 거리 / 각도 CSV"],
      ["png", "PNG / 현재 배향"],
      ["svg", "SVG / 현재 배향"],
      ["html", "호환 HTML / 기존 v2.2 웹 편집기"],
    ]
      .map(([k, v]) => `<button data-export="${k}">${v}</button>`)
      .join(
        "",
      )}</div><p class="hint">호환 HTML은 기존 편집기를 포함합니다. 4.1의 RDKit·Gaussian 기능은 현재 로컬 서버에서 사용하세요.</p>`,
  );
  $("modalBody")
    .querySelectorAll("[data-export]")
    .forEach((b) =>
      b.addEventListener(
        "click",
        guard(async () => {
          const k = b.dataset.export;
          if (k === "png") download(await viewer.png(), "tinoxo.png");
          else if (k === "svg")
            download(viewer.svg(), "tinoxo.svg", "image/svg+xml");
          else await exportKind(k);
        }),
      ),
    );
}
function records() {
  return [
    ...config.ligands.map(([category, name, smiles, mode]) => ({
      category,
      name,
      smiles,
      mode,
      builtin: true,
    })),
    ...(state.settings.favorites || []).map((v) => ({
      ...v,
      category: "내 SMILES",
      builtin: false,
    })),
  ];
}
function libraryHTML() {
  return `<input id="ligandSearch" class="library-search" placeholder="리간드 이름 / 종류 / SMILES 검색"><div id="libraryTable" class="table-scroll library-table"></div><div class="form-grid">${inputField("이름", "favoriteName")}${selectField("결합 방식", "favoriteMode", ["covalent", "coordinate", "bridge"], "covalent")}<label class="full">리간드 SMILES<input id="favoriteSmiles" placeholder="CCN 또는 [*:1]C"></label></div><div class="inline">${btn("내 SMILES 추가 / 갱신", "favoriteSave")}${btn("내 SMILES 삭제", "favoriteDelete")}${btn("선택 사용", "libraryUse", true)}</div>`;
}
function bindLibrary(receiver) {
  let active = null;
  const fill = () => {
    const q = $("ligandSearch").value.toLowerCase();
    const rr = records().filter((r) =>
      [r.name, r.category, r.smiles].join(" ").toLowerCase().includes(q),
    );
    pagedTable(
      "libraryTable",
      ["종류", "이름", "SMILES", "방식"],
      rr.map((r) => [r.category, r.name, r.smiles, r.mode]),
      (_, i) => `data-record="${i}"`,
      () => {
        $("libraryTable")
          .querySelectorAll("[data-record]")
          .forEach((tr) => {
            const choose = () => {
              active = rr[Number(tr.dataset.record)];
              $("favoriteName").value = active.name;
              $("favoriteSmiles").value = active.smiles;
              $("favoriteMode").value = active.mode;
              $("libraryTable")
                .querySelectorAll("tr.selected")
                .forEach((v) => v.classList.remove("selected"));
              tr.classList.add("selected");
            };
            tr.addEventListener("click", choose);
            tr.addEventListener(
              "dblclick",
              guard(async () => {
                choose();
                await receiver(active.smiles, active.mode);
              }),
            );
          });
      },
    );
  };
  let searchTimer;
  on(
    "ligandSearch",
    () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        if ($("ligandSearch")) fill();
      }, 80);
    },
    "input",
  );
  on("libraryUse", () => {
    if (!$("favoriteSmiles").value.trim())
      throw Error("리간드를 선택하거나 SMILES를 입력하세요.");
    return receiver($("favoriteSmiles").value.trim(), $("favoriteMode").value);
  });
  on("favoriteSave", async () => {
    await edit("favorite", {
      name: $("favoriteName").value,
      smiles: $("favoriteSmiles").value,
      mode: $("favoriteMode").value,
    });
    fill();
    toast("내 SMILES를 저장했습니다.");
  });
  on("favoriteDelete", async () => {
    if (!active || active.builtin)
      throw Error("삭제할 내 SMILES를 선택하세요.");
    await edit("favorite", { ...active, remove: true });
    fill();
  });
  fill();
}
function libraryDialog() {
  show("범용 리간드 / 내 SMILES", libraryHTML());
  bindLibrary(async (s, m) => {
    if (!selection.length) throw Error("먼저 리간드를 붙일 원자를 선택하세요.");
    await attachDialog(null, {
      smiles: s,
      mode: m === "bridge" ? "coordinate" : m,
    });
  });
}
async function chooseAtom(smiles, kind, mode, initial = null) {
  let diagram = await api("query/ligand", {
      smiles,
      kind,
      mode,
      selected: initial,
    }),
    chosen = diagram.selected;
  return new Promise((resolve, reject) => {
    let confirmed = false;
    const paint = () => {
      $("pickerBody").innerHTML =
        `<p class="content-note">원자를 클릭하거나 목록에서 선택한 뒤 확정하세요. 번호는 입력 SMILES 순서(1부터)입니다.</p><p class="content-note">${h(smiles)}</p><div class="picker-layout"><div class="atom-diagram" id="ligandDiagram">${diagram.svg}</div><div class="table-scroll">${table(
          ["원자", "전하"],
          diagram.candidates.map((a) => [a.element + (a.index + 1), a.charge]),
          (_, i) =>
            `data-atom="${diagram.candidates[i].index}" class="${diagram.candidates[i].index === chosen ? "selected" : ""}"`,
        )}</div></div><p id="chosenAtom" class="badge"></p><p class="hint">${kind === "L" || kind === "P" ? "선택한 O → 첫 Sn, 같은 연결부의 다른 O → 두 번째 Sn." : mode === "coordinate" ? "선택 원자의 H를 유지해 배위결합합니다." : "선택 원자의 H 하나를 공유결합으로 치환합니다. 이전 * 자리는 필요한 경우 H로 막습니다."}</p><div class="dialog-actions">${btn("취소", "cancelAtom")}${btn("결합 원자 확정", "confirmAtom", true)}</div>`;
      mark();
      $("pickerBody")
        .querySelectorAll("[data-atom]")
        .forEach((el) =>
          el.addEventListener("click", () => {
            chosen = Number(el.dataset.atom);
            mark();
          }),
        );
      on("cancelAtom", () => picker.close());
      on("confirmAtom", () => {
        confirmed = true;
        picker.close();
        resolve(chosen);
      });
    };
    const mark = () => {
      const atom = diagram.candidates.find((a) => a.index === chosen);
      $("chosenAtom").textContent = `결합 원자: ${atom.element}${chosen + 1}`;
      $("pickerBody")
        .querySelectorAll("tr[data-atom]")
        .forEach((tr) =>
          tr.classList.toggle("selected", Number(tr.dataset.atom) === chosen),
        );
      $("ligandDiagram")
        .querySelectorAll("circle[data-atom]")
        .forEach((el) => {
          el.setAttribute(
            "fill",
            Number(el.dataset.atom) === chosen ? "#58d6c550" : "transparent",
          );
          el.setAttribute(
            "stroke",
            Number(el.dataset.atom) === chosen ? "#087e73" : "none",
          );
        });
    };
    picker.addEventListener(
      "close",
      () => {
        if (!confirmed) resolve(null);
      },
      { once: true },
    );
    paint();
    picker.showModal();
  });
}
async function attachDialog(slotId = null, preset = null) {
  const hosts = [...selection],
    slot = state.project.slots.find((s) => s.id === slotId);
  if (!slot && !hosts.length)
    throw Error("리간드를 붙일 원자를 먼저 선택하세요.");
  const aa = new Map(state.project.atoms.map((a) => [a.id, a])),
    plans = [];
  let picked = null,
    pickedKey = "",
    current = preset || {
      smiles: slot?.smiles || "",
      mode: slot?.mode || "covalent",
    };
  if (current.mode === "bridge") current.mode = "coordinate";
  show(
    "선택 원자 / 결합 자리에 리간드 추가",
    `<p class="content-note">${slot ? "자리 " + h(slot.id) : hosts.length + "개 선택 원자"} · 공통 입력과 원자별 입력을 계획에 추가한 뒤 한 번에 적용합니다.</p><div class="attachment-grid">${selectField("대상", "attachTarget", slot ? [slot.id] : [["all", "선택 원자 모두"], ...hosts.map((i) => [String(i), aa.get(i).element + i])], slot ? slot.id : "all")}${inputField("리간드 SMILES", "attachSmiles", current.smiles)}${selectField("결합 방식", "attachMode", ["covalent", "coordinate"], current.mode)}${inputField("길이 Å", "attachLength", "", "number", 'step="0.01" min="0.5" max="4"')}${selectField("방향", "attachDirection", ["자동", "+X", "-X", "+Y", "-Y", "+Z", "-Z"], "자동")}</div><div class="inline">${btn("결합 원자 선택…", "chooseAttachAtom")}<span id="attachAtomLabel" class="badge">선택 필요</span>${btn("라이브러리 열기", "attachLibraryToggle")}</div><section id="inlineLibrary" class="hidden">${libraryHTML()}</section><div id="plansTable" class="table-scroll"></div><div class="inline">${btn("입력을 계획에 추가", "addPlan")}${btn("선택 계획 삭제", "removePlan")}</div><label><input type="checkbox" id="replaceH" checked> 공유결합 시 비금속 부모의 H 하나 치환</label><label><input type="checkbox" id="cleanAttach" checked> 리간드 배향을 탐색해 겹침 줄이기</label><p class="hint">같은 리간드와 결합 원자를 여러 부모 원자에 함께 적용할 수 있습니다. SMILES나 방식을 바꾸면 결합 원자를 다시 선택합니다.</p><div class="dialog-actions">${btn("닫기", "closeAttach")}${btn("모두 적용", "applyAttach", true)}</div>`,
  );
  const key = () =>
    $("attachSmiles").value.trim() + "|" + $("attachMode").value;
  const pick = async () => {
    const index = await chooseAtom(
      $("attachSmiles").value.trim(),
      slot?.kind || "A",
      $("attachMode").value,
      pickedKey === key() ? picked : slot?.attachmentIndex,
    );
    if (index === null) return false;
    picked = index;
    pickedKey = key();
    $("attachAtomLabel").textContent = "결합 원자 #" + (index + 1);
    return true;
  };
  let selectedPlan = null;
  const fill = () => {
    $("plansTable").innerHTML = table(
      ["대상", "SMILES", "결합 원자", "방식", "길이", "방향"],
      plans.map((r) => [
        r.slot_id || r.parents.map((i) => aa.get(i).element + i).join(", "),
        r.smiles,
        r.attachment_index === null ? "제거" : r.attachment_index + 1,
        r.mode,
        r.length || "자동",
        r.directionName,
      ]),
      (_, i) => `data-plan="${i}"`,
    );
    $("plansTable")
      .querySelectorAll("[data-plan]")
      .forEach(
        (tr) =>
          (tr.onclick = () => {
            selectedPlan = Number(tr.dataset.plan);
            $("plansTable")
              .querySelectorAll("tr")
              .forEach((v) => v.classList.remove("selected"));
            tr.classList.add("selected");
          }),
      );
  };
  const add = async () => {
    let smiles = $("attachSmiles").value.trim();
    if (!smiles && !slot) throw Error("SMILES를 입력하세요.");
    if (smiles && pickedKey !== key() && !(await pick())) return false;
    const len = $("attachLength").value;
    if (len && (Number(len) < 0.5 || Number(len) > 4))
      throw Error("길이는 0.5–4 Å 범위입니다.");
    const ds = {
      "+X": [1, 0, 0],
      "-X": [-1, 0, 0],
      "+Y": [0, 1, 0],
      "-Y": [0, -1, 0],
      "+Z": [0, 0, 1],
      "-Z": [0, 0, -1],
    };
    if (slot) plans.length = 0;
    plans.push({
      parents:
        $("attachTarget").value === "all"
          ? hosts
          : slot
            ? slot.sn
            : [Number($("attachTarget").value)],
      slot_id: slot?.id,
      smiles,
      attachment_index: smiles ? picked : null,
      mode: $("attachMode").value,
      length: len,
      direction: ds[$("attachDirection").value] || null,
      directionName: $("attachDirection").value,
    });
    fill();
    return true;
  };
  for (const id of ["attachSmiles", "attachMode"])
    on(
      id,
      () => {
        $("attachAtomLabel").textContent =
          pickedKey === key() ? "결합 #" + (picked + 1) : "선택 필요";
      },
      "input",
    );
  on("chooseAttachAtom", pick);
  on("addPlan", add);
  on("removePlan", () => {
    if (selectedPlan !== null) {
      plans.splice(selectedPlan, 1);
      selectedPlan = null;
      fill();
    }
  });
  on("closeAttach", () => modal.close());
  on("attachLibraryToggle", () =>
    $("inlineLibrary").classList.toggle("hidden"),
  );
  bindLibrary(async (s, m) => {
    $("attachSmiles").value = s;
    $("attachMode").value = m === "bridge" ? "coordinate" : m;
    $("inlineLibrary").classList.add("hidden");
    await pick();
  });
  on("applyAttach", async () => {
    if (!plans.length && !(await add())) return;
    await task("attach", {
      plans,
      replace_h: $("replaceH").checked,
      cleanup: $("cleanAttach").checked,
    });
  });
  fill();
  if (preset && current.smiles) await pick();
}
function gaussianDialog() {
  const p = state.project,
    g = structuredClone(config.defaults),
    bmap = {},
    emap = {};
  g.charge = p.metadata.totalCharge ?? 0;
  const electrons =
    p.atoms.reduce(
      (sum, a) => sum + config.elements.indexOf(a.element) + 1,
      0,
    ) - g.charge;
  g.multiplicity = electrons % 2 ? 2 : 1;
  let text = "";
  const fields = {
    method: ["방법 / XC", config.methods],
    basis: ["기본 기저함수", config.bases],
    spin: ["파동함수", ["Auto", "R", "U", "ROHF"]],
    job: ["계산 종류", config.jobs],
    freeze: ["원자 고정", ["None", "Core", "Fixed"]],
    dispersion: ["분산 보정", ["None", "GD3", "GD3BJ"]],
    charge: ["총전하"],
    multiplicity: ["스핀 다중도"],
    cpus: ["CPU %NProcShared"],
    memory: ["메모리 %Mem"],
    title: ["제목 (ASCII)"],
    checkpoint: ["체크포인트 %Chk"],
    basis_mode: ["기저 방식", ["single", "mixed", "custom"]],
    scf: ["SCF 보조", ["XQC", "QC", "None"]],
    scf_max: ["SCF 최대 반복"],
    grid: ["수치 적분격자", ["UltraFine", "SuperFineGrid", "FineGrid", "None"]],
    opt_cycles: ["최적화 최대 반복"],
    population: [
      "전자밀도 / population",
      ["None", "Regular", "Full", "Hirshfeld", "NPA"],
    ],
    solvent: [
      "용매",
      [
        "None",
        "Water",
        "Methanol",
        "Ethanol",
        "Acetonitrile",
        "Toluene",
        "Benzene",
        "Chloroform",
        "Dichloromethane",
        "TetraHydroFuran",
        "DiMethylSulfoxide",
      ],
    ],
    solvation: ["용매 모델", ["SMD", "IEFPCM"]],
    states: ["TD NStates"],
    root: ["TD Root"],
    extra: ["추가 route 키워드"],
  };
  const field = (k) => {
    const [label, vals] = fields[k];
    return `<label>${h(label)}${vals ? `<select data-g="${k}">${options(vals, g[k])}</select>` : `<input data-g="${k}" value="${h(g[k])}" ${["charge", "multiplicity", "cpus", "scf_max", "opt_cycles", "states", "root"].includes(k) ? 'type="number"' : ""}>`}</label>`;
  };
  const elements = [...new Set(p.atoms.map((a) => a.element))].sort(
    (a, b) => config.elements.indexOf(a) - config.elements.indexOf(b),
  );
  show(
    "Gaussian 16 입력 생성",
    `<div class="dialog-tabs" id="gaussianTabs"><button data-gtab="quick" class="active">간편 설정</button><button data-gtab="custom">커스텀 설정</button><button data-gtab="preview">입력 미리보기</button></div><section id="g-quick"><div class="form-grid">${["method", "basis", "spin", "dispersion", "job", "freeze", "charge", "multiplicity", "cpus", "memory", "title", "checkpoint", "solvent", "solvation"].map(field).join("")}</div><p id="basisStatus" class="content-note"></p>${btn("이 기저함수를 모든 원소에 간편 적용", "uniformBasis")}<p class="hint">방법과 기저함수를 함께 고릅니다. Sn + def2는 Auto 설정에서 Def2 ECP를 함께 생성합니다.</p></section><section id="g-custom" class="hidden"><h3>방법 / 기저함수 / ECP</h3><div class="form-grid">${["method", "basis", "spin", "basis_mode"].map(field).join("")}</div><div class="inline">${selectField("Exchange", "xcExchange", config.exchange, "B")}${selectField("Correlation", "xcCorrelation", config.correlation, "LYP")}${btn("XC 반영", "composeXC")}</div><div class="table-scroll"><table><thead><tr><th>원소</th><th>기저함수</th><th>ECP</th></tr></thead><tbody>${elements.map((e) => `<tr><td>${e}</td><td><select data-basis="${e}">${options(config.bases, g.basis)}</select></td><td><select data-ecp="${e}">${options(["Auto", "None", "Def2", "SDD", "LANL2DZ"], "Auto")}</select></td></tr>`).join("")}</tbody></table></div><div class="inline">${selectField("외부 블록 키워드", "customKeyword", ["Gen", "GenECP"], "GenECP")}<p class="hint">외부 블록을 쓰려면 기저 방식을 custom으로 선택하세요.</p></div><textarea id="customBasis" placeholder="검증한 외부 기저함수 / ECP 블록"></textarea><h3>SCF / 최적화 / 물성</h3><div class="form-grid">${["scf", "scf_max", "grid", "opt_cycles", "dispersion", "population", "solvation", "solvent", "states", "root", "extra"].map(field).join("")}</div><div class="inline">${["scf_tight", "opt_tight", "nosymm"].map((k) => `<label><input type="checkbox" data-g="${k}" ${g[k] ? "checked" : ""}> ${k === "scf_tight" ? "SCF Tight" : k === "opt_tight" ? "Opt Tight" : "NoSymm"}</label>`).join("")}</div><label>좌표 / 기저 블록 뒤 추가 입력<textarea id="additionalBlocks"></textarea></label></section><section id="g-preview" class="hidden"><textarea id="gaussianText" class="gaussian-preview" readonly></textarea><p id="gaussianReport" class="content-note"></p></section><div class="dialog-actions">${btn("입력 생성 / 갱신", "generateGaussian")}${btn(".gjf 다운로드", "downloadGaussian", true)}${btn("서버 경로에 저장", "saveGaussianServer")}</div><div class="inline">${inputField("서버 저장 경로 (파일 이름 포함)", "gaussianServerPath", "", "text", 'placeholder="/home/user/calculation/input.gjf"')}</div><p class="hint">총전하·다중도를 확인하세요. Gaussian 실행이나 스케줄러 제출은 하지 않습니다.</p>`,
  );
  const sync = () => {
    $("modalBody")
      .querySelectorAll("[data-g]")
      .forEach((el) => {
        const v = g[el.dataset.g];
        if (el.type === "checkbox") el.checked = !!v;
        else el.value = v;
      });
    $("basisStatus").textContent =
      `기저 방식: ${g.basis_mode} · 원소별 지정 ${Object.keys(bmap).length}개`;
  };
  $("modalBody")
    .querySelectorAll("[data-g]")
    .forEach((el) =>
      el.addEventListener("change", () => {
        g[el.dataset.g] =
          el.type === "checkbox"
            ? el.checked
            : [
                  "charge",
                  "multiplicity",
                  "cpus",
                  "scf_max",
                  "opt_cycles",
                  "states",
                  "root",
                ].includes(el.dataset.g)
              ? Number(el.value)
              : el.value;
        if (el.dataset.g === "basis")
          $("modalBody")
            .querySelectorAll("[data-basis]")
            .forEach((b) => {
              if (!bmap[b.dataset.basis]) b.value = g.basis;
            });
        sync();
      }),
    );
  const tab = (name) => {
    $("gaussianTabs")
      .querySelectorAll("button")
      .forEach((b) => b.classList.toggle("active", b.dataset.gtab === name));
    for (const k of ["quick", "custom", "preview"])
      $("g-" + k).classList.toggle("hidden", k !== name);
  };
  $("gaussianTabs")
    .querySelectorAll("[data-gtab]")
    .forEach((b) => (b.onclick = () => tab(b.dataset.gtab)));
  $("modalBody")
    .querySelectorAll("[data-basis]")
    .forEach(
      (el) =>
        (el.onchange = () => {
          bmap[el.dataset.basis] = el.value;
          g.basis_mode = "mixed";
          sync();
        }),
    );
  $("modalBody")
    .querySelectorAll("[data-ecp]")
    .forEach(
      (el) =>
        (el.onchange = () => {
          emap[el.dataset.ecp] = el.value;
          g.basis_mode = "mixed";
          sync();
        }),
    );
  const gather = () => ({
    ...g,
    basis_by_element: { ...bmap },
    ecp_by_element: { ...emap },
    custom_keyword: $("customKeyword").value,
    custom_basis: $("customBasis").value,
    additional: $("additionalBlocks").value,
  });
  const generate = async () => {
    const result = await api("query/gaussian", { options: gather() });
    text = result.text;
    $("gaussianText").value = text;
    $("gaussianReport").textContent =
      `전자수: ${result.report.electrons} · ` +
      result.report.warnings.join(" / ");
    tab("preview");
    return text;
  };
  on("generateGaussian", generate);
  on("downloadGaussian", async () => {
    download(await generate(), "tinoxo.gjf");
    toast("Gaussian 입력을 다운로드했습니다.");
  });
  on("saveGaussianServer", async () => {
    if (!$("gaussianServerPath").value.trim())
      throw Error("파일 이름을 포함한 서버 경로를 입력하세요.");
    await generate();
    await api("save", {
      revision: state.revision,
      kind: "gaussian",
      options: gather(),
      path: $("gaussianServerPath").value.trim(),
    });
    toast("지정한 서버 경로에 저장했습니다.");
  });
  on("composeXC", () => {
    const m = $("xcExchange").value + $("xcCorrelation").value;
    if (!config.valid_xc.includes(m))
      throw Error("내장 검증 목록에 없는 XC 조합입니다.");
    g.method = m;
    sync();
  });
  on("uniformBasis", () => {
    for (const e of Object.keys(bmap)) delete bmap[e];
    for (const e of Object.keys(emap)) delete emap[e];
    g.basis_mode = "mixed";
    $("modalBody")
      .querySelectorAll("[data-basis]")
      .forEach((el) => (el.value = g.basis));
    $("modalBody")
      .querySelectorAll("[data-ecp]")
      .forEach((el) => (el.value = "Auto"));
    sync();
  });
  sync();
}
function slotsDialog() {
  const slots = structuredClone(state.project.slots),
    indices = new Map();
  show(
    "R / L / P / 추가 U 자리 편집",
    `<p class="content-note">비어 있는 SMILES는 기존 리간드를 제거합니다. 바뀐 SMILES의 결합 원자는 적용 전에 구조 팝업에서 확인합니다.</p><div class="table-scroll"><table><thead><tr><th>자리</th><th>종류</th><th>부모</th><th>SMILES</th><th>결합 원자</th></tr></thead><tbody>${slots.map((s) => `<tr><td>${h(s.id)}</td><td>${h(s.kind)}</td><td>${s.sn.join(", ")}</td><td><input data-slot-edit="${h(s.id)}" value="${h(s.smiles || "")}" style="width:350px"></td><td><button data-slot-pick="${h(s.id)}">원자 선택</button></td></tr>`).join("")}</tbody></table></div><div class="dialog-actions">${btn("전체 자리 적용", "applySlots", true)}</div>`,
  );
  const values = () =>
    new Map(
      [...$("modalBody").querySelectorAll("[data-slot-edit]")].map((el) => [
        el.dataset.slotEdit,
        el.value.trim(),
      ]),
    );
  const pick = async (s) => {
    const smiles = values().get(s.id);
    if (!smiles) throw Error("선택할 리간드 SMILES를 입력하세요.");
    const mode =
      s.kind === "L" || s.kind === "P" ? "coordinate" : s.mode || "covalent";
    const i = await chooseAtom(smiles, s.kind, mode, s.attachmentIndex);
    if (i !== null) indices.set(s.id, { smiles, index: i });
    return i;
  };
  $("modalBody")
    .querySelectorAll("[data-slot-pick]")
    .forEach(
      (b) =>
        (b.onclick = guard(() =>
          pick(slots.find((s) => s.id === b.dataset.slotPick)),
        )),
    );
  on("applySlots", async () => {
    const plans = [];
    for (const s of slots) {
      const smiles = values().get(s.id),
        chosen = indices.get(s.id);
      if (smiles === (s.smiles || "") && !chosen) continue;
      let index = chosen?.smiles === smiles ? chosen.index : null;
      if (smiles && index === null) {
        index = await pick(s);
        if (index === null) return;
      }
      plans.push({
        slot_id: s.id,
        smiles,
        attachment_index: index,
        mode:
          s.kind === "L" || s.kind === "P"
            ? "coordinate"
            : s.mode || "covalent",
      });
    }
    if (!plans.length) throw Error("바뀐 자리 입력이 없습니다.");
    await task("attach", { plans });
  });
}
async function refreshContacts() {
  const rows = await api("query/contacts", {});
  pagedTable(
    "contactsTable",
    ["원자쌍", "거리 Å", "기준 Å"],
    rows.map((r) => [
      r.a + "–" + r.b,
      r.distance.toFixed(3),
      r.threshold.toFixed(3),
    ]),
    (_, i) => `data-pair="${rows[i].a},${rows[i].b}"`,
    () => {
      $("contactsTable")
        .querySelectorAll("[data-pair]")
        .forEach(
          (tr) =>
            (tr.onclick = () =>
              selectExact(tr.dataset.pair.split(",").map(Number))),
        );
    },
    "현재 기준의 근접 접촉이 없습니다.",
  );
}
function contactSettings() {
  const v = state.project.metadata.contactCriteria || state.settings.contact;
  show(
    "비결합 접촉 검사 기준",
    `<p class="content-note">radii: max(vdW 반경합 × 계수, 공유반경합 × 계수). minimum: 모든 검사쌍에 공통 최소 거리 적용.</p><div class="form-grid">${selectField("방식", "contactMode", ["radii", "minimum"], v.mode)}${inputField("vdW 계수", "contactVdw", v.vdw, "number", 'step="0.01"')}${inputField("공유반경 계수", "contactCovalent", v.covalent, "number", 'step="0.01"')}${inputField("공통 최소거리 Å", "contactMinimum", v.minimum, "number", 'step="0.01"')}</div><div class="dialog-actions">${btn("적용", "applyContacts", true)}</div>`,
  );
  on("applyContacts", async () => {
    await edit("contacts", {
      criteria: {
        mode: $("contactMode").value,
        vdw: $("contactVdw").value,
        covalent: $("contactCovalent").value,
        minimum: $("contactMinimum").value,
      },
    });
    await refreshContacts();
    modal.close();
  });
}
async function geometryDialog() {
  const request = show(
    "결합길이 · 결합각 · 이면각",
    '<p class="content-note">기하 정보를 계산하고 있습니다…</p>',
  );
  const rows = await api("query/geometry", {});
  if (request !== modalEpoch || !modal.open) return;
  show(
    "결합길이 · 결합각 · 이면각",
    `<p class="content-note">원자 ID를 순서대로 2개(거리), 3개(각도), 4개(이면각) 입력하세요.</p><div class="inline"><input id="measureIds" value="${selection.slice(0, 4).join(" ")}" placeholder="1 2 3">${btn("측정", "measureNow")}${btn("CSV 다운로드", "geometryCsv")}</div><p id="measureResult" class="content-note"></p><div id="geometryTable" class="table-scroll"></div>`,
  );
  const measure = async () => {
    const ids = $("measureIds")
      .value.split(/[\s,;]+/)
      .filter(Boolean)
      .map(Number);
    const r = await api("query/measure", { ids });
    $("measureResult").textContent =
      `${r.name}: ${r.value.toFixed(6)} ${r.unit}`;
    selectExact(ids);
  };
  on("measureNow", measure);
  on("geometryCsv", () => exportKind("csv"));
  pagedTable(
    "geometryTable",
    ["종류", "원자 순서", "값", "단위", "근거"],
    rows.map((r) => [r[0], r[1], Number(r[2]).toFixed(5), r[3], r[4]]),
    (_, i) => `data-geometry="${i}"`,
    () => {
      $("geometryTable")
        .querySelectorAll("[data-geometry]")
        .forEach(
          (tr) =>
            (tr.onclick = guard(async () => {
              $("measureIds").value = (
                rows[Number(tr.dataset.geometry)][1].match(/[A-Z][a-z]?\d+/g) ||
                []
              )
                .map((s) => s.match(/\d+/)[0])
                .join(" ");
              await measure();
            })),
        );
    },
  );
}
async function bondsDialog() {
  show(
    "결합 정보 검사 / 편집",
    `<p class="content-note">기존 명시 결합을 유지합니다. ASE 거리 후보는 사용자가 선택해 추가해야 확정됩니다.</p><div class="inline">${inputField("ASE 반경 배율", "auditScale", 1.25, "number", 'step="0.05"')}${inputField("금속 donor 최대거리 Å", "auditMetal", 2.85, "number", 'step="0.05"')}${btn("다시 검사", "auditRefresh")}</div><div id="auditTable" class="table-scroll"></div><div class="form-grid">${inputField("원자 ID 2개", "bondIds", selection.slice(0, 2).join(" "))}${selectField("결합차수", "bondOrder", [1, 1.5, 2, 3], 1)}${selectField("결합 방식", "bondKind", ["covalent", "coordinate"], "covalent")}</div><div class="dialog-actions">${btn("원자가 / 배위수 점검", "validateOrganic")}${btn("선택 후보 추가", "acceptBonds")}${btn("선택 결합 삭제", "deleteBonds")}${btn("추가 / 수정", "manualBond", true)}</div><pre id="validationOutput"></pre>`,
  );
  let rows = [];
  const selectedAudit = new Set();
  const fill = async () => {
    const scale = Number($("auditScale").value),
      metal_max = Number($("auditMetal").value);
    if (scale < 1 || scale > 1.8 || metal_max < 2 || metal_max > 4)
      throw Error("반경 배율 1–1.8, 금속 거리 2–4 Å를 지정하세요.");
    const host = $("auditTable");
    const result = await api("query/bonds", { scale, metal_max });
    if (host !== $("auditTable")) return;
    rows = result;
    selectedAudit.clear();
    pagedTable(
      "auditTable",
      ["선택", "원자쌍", "차수", "방식", "거리 Å", "상태"],
      rows.map((r, i) => [
        "",
        r.a + "–" + r.b,
        r.order,
        r.kind,
        r.distance.toFixed(4),
        r.status,
      ]),
      (_, i) => `data-audit="${i}"`,
      () => {
        $("auditTable")
          .querySelectorAll("[data-audit]")
          .forEach((tr) => {
            const index = Number(tr.dataset.audit);
            tr.cells[0].innerHTML = `<input type="checkbox" data-audit-check="${index}" ${selectedAudit.has(index) ? "checked" : ""}>`;
            tr.cells[0].firstElementChild.onchange = (e) => {
              if (e.target.checked) selectedAudit.add(index);
              else selectedAudit.delete(index);
            };
            tr.addEventListener("click", (e) => {
              if (e.target.type !== "checkbox") {
                const r = rows[index];
                $("bondIds").value = r.a + " " + r.b;
                $("bondOrder").value = r.order;
                $("bondKind").value = r.kind;
                selectExact([r.a, r.b]);
              }
            });
          });
      },
    );
  };
  const checked = () => [...selectedAudit].map((i) => rows[i]);
  on("auditRefresh", fill);
  on("manualBond", async () => {
    await edit("bond", {
      ids: $("bondIds")
        .value.trim()
        .split(/[\s,;]+/)
        .map(Number),
      order: $("bondOrder").value,
      kind: $("bondKind").value,
    });
    await fill();
  });
  on("deleteBonds", async () => {
    const rr = checked();
    if (!rr.length) throw Error("삭제할 결합을 체크하세요.");
    for (const r of rr) await edit("bond", { ids: [r.a, r.b], remove: true });
    await fill();
  });
  on("acceptBonds", async () => {
    const rr = checked().filter((r) => r.status.startsWith("검토"));
    if (!rr.length) throw Error("추가할 후보를 체크하세요.");
    await edit("accept_bonds", {
      pairs: rr.map((r) => [r.a, r.b]),
      scale: Number($("auditScale").value),
      metal_max: Number($("auditMetal").value),
    });
    await fill();
  });
  on("validateOrganic", async () => {
    const result = await api("query/validate", {});
    const metals = state.project.atoms.filter((a) =>
      config.metals.includes(a.element),
    );
    $("validationOutput").textContent =
      result.join("\n") +
      "\n" +
      metals
        .map(
          (a) =>
            a.element +
            a.id +
            ": 명시 그래프 연결 " +
            state.project.bonds.filter((b) => b.a === a.id || b.b === a.id)
              .length +
            "개",
        )
        .join("\n");
  });
  await fill();
}
async function resonanceDialog() {
  const slot = state.project.slots.find((s) =>
    selection.some((i) => s.ligandIds?.includes(i)),
  );
  show(
    "공명식 / 방향족성 확인",
    `<div class="inline"><input id="resonanceSmiles" value="${h(slot?.smiles || "CC(=O)[O-]")}">${btn("공명식 분석", "analyzeResonance")}</div><p class="content-note">Lewis 표현의 열거 결과입니다. 형식차수의 산술 평균은 양자화학적 결합차수나 통계 가중치가 아닙니다.</p><p id="resonanceSummary" class="badge"></p><div id="resonanceTable" class="table-scroll"></div><div id="resonanceImage" class="atom-diagram"></div><div class="dialog-actions">${btn("이 SMILES로 리간드 생성 / 재부착", "attachResonance", true)}</div>`,
  );
  const analyze = async () => {
    const host = $("resonanceSummary");
    const r = await api("query/resonance", {
      smiles: $("resonanceSmiles").value,
    });
    if (host !== $("resonanceSummary")) return;
    $("resonanceSummary").textContent =
      `공명식 ${r.forms}개${r.truncated ? " (제한됨)" : ""} · 방향족 원자 ${r.aromatic}개`;
    $("resonanceTable").innerHTML = table(
      ["공명식", "SMILES"],
      r.smiles.map((s, i) => [i + 1, s]),
      (_, i) => `data-resonance="${i}"`,
    );
    const draw = async (i) => {
      const diagram = await api("query/ligand", {
        smiles: r.smiles[i],
        mode: "coordinate",
      });
      if (host === $("resonanceSummary"))
        $("resonanceImage").innerHTML = diagram.svg;
    };
    $("resonanceTable")
      .querySelectorAll("[data-resonance]")
      .forEach(
        (tr) => (tr.onclick = guard(() => draw(Number(tr.dataset.resonance)))),
      );
    if (r.smiles.length) await draw(0);
  };
  on("analyzeResonance", analyze);
  on("attachResonance", () =>
    attachDialog(slot?.id, {
      smiles: $("resonanceSmiles").value,
      mode:
        slot?.kind === "L" || slot?.kind === "P" ? "coordinate" : "covalent",
    }),
  );
  await analyze();
}
function bankDialog() {
  let active = state.bank.activeId;
  show(
    "이름별 구조 보관함",
    `${inputField("구조 이름", "bankName", state.project.title)}<div id="bankTable" class="table-scroll bank-table"></div><div class="dialog-actions">${[
      ["store", "현재 구조 보관"],
      ["copy", "복사 보관"],
      ["load", "불러오기"],
      ["rename", "이름 변경"],
      ["delete", "삭제"],
      ["restore", "삭제 복원"],
    ]
      .map(([op, t]) => `<button data-bank-op="${op}">${t}</button>`)
      .join(
        "",
      )}</div><p class="hint">현재 구조·보관함·즐겨찾기·설정은 서버에 자동 복구 저장됩니다. 다른 PC로 옮길 때는 전체 프로젝트 JSON을 다운로드하세요.</p>`,
  );
  const fill = () => {
    $("bankTable").innerHTML = table(
      ["이름", "원자수", "조성"],
      state.bank.entries.map((e) => [e.name, e.atoms, e.formula || "—"]),
      (_, i) =>
        `data-bank-id="${h(state.bank.entries[i].id)}" class="${state.bank.entries[i].id === active ? "selected" : ""}"`,
    );
    $("bankTable")
      .querySelectorAll("[data-bank-id]")
      .forEach(
        (tr) =>
          (tr.onclick = () => {
            active = tr.dataset.bankId;
            $("bankName").value = state.bank.entries.find(
              (e) => e.id === active,
            ).name;
            fill();
          }),
      );
  };
  $("modalBody")
    .querySelectorAll("[data-bank-op]")
    .forEach(
      (b) =>
        (b.onclick = guard(async () => {
          await edit(
            "bank",
            { op: b.dataset.bankOp, id: active, name: $("bankName").value },
            b.dataset.bankOp === "load",
          );
          active = state.bank.activeId;
          fill();
        })),
    );
  fill();
}
function appearanceDialog() {
  const old = structuredClone(state.settings),
    draft = structuredClone(old),
    changedColors = new Set();
  show(
    "화면 설정 · 글꼴 / 색상",
    `<p class="content-note">글씨는 현재 브라우저가 렌더링합니다. 맑은고딕·굴림·Arial·Calibri가 접속 PC에 없으면 동봉된 나눔고딕 등으로 대체됩니다.</p><div class="form-grid">${selectField("한글 글꼴", "koFont", ["맑은고딕", "굴림"], old.korean_font)}${selectField("영문 글꼴", "enFont", ["Arial", "Calibri"], old.english_font)}${inputField("글꼴 크기 pt", "fontSize", old.font_size, "number", 'min="8" max="24"')}${selectField("화면 모드", "theme", ["dark", "light"], old.theme)}${selectField(
      "3D 표시 품질",
      "viewerQuality",
      [
        ["auto", "자동 (권장)"],
        ["low", "속도 우선"],
        ["high", "고화질"],
      ],
      old.viewer_quality || "auto",
    )}${selectField("목표 프레임", "viewerFps", [20, 30, 60], old.viewer_fps || 30)}</div><h3>항목별 글자 색상</h3><div class="settings-grid">${Object.entries(
      {
        body: "본문",
        heading: "제목",
        muted: "설명",
        button: "버튼",
        input: "입력값",
        status: "상태",
        warning: "경고",
        label: "3D 라벨",
      },
    )
      .map(([k, t]) =>
        inputField(
          t,
          "textColor-" + k,
          old.text_colors?.[k] ||
            {
              body: "#dce5ef",
              muted: "#8598ad",
              status: "#58d6c5",
              warning: "#f18b97",
            }[k] ||
            "#dce5ef",
          "color",
        ),
      )
      .join(
        "",
      )}</div><div class="form-grid">${inputField("선택 강조 색상", "selectionColor", old.selection, "color")}${selectField("원소 색상 편집", "elementColorChoice", config.elements, "Sn")}${inputField("선택 원소 RGB", "elementColorValue", old.element_colors?.Sn || config.colors.Sn, "color")}</div><div class="inline">${btn("이 원소 색상 반영", "applyElementColor")}${btn("VESTA 기본 색상 복원", "resetElementColors")}<label>VESTA elements.ini 가져오기<input id="vestaImport" type="file" accept=".ini,.txt"></label></div><p class="content-note" id="fontSample">한글 예문: 주석 옥소 구조 · 결합길이 / English: Sn12 O20 · 1.234 Å</p><div class="dialog-actions">${btn("취소", "cancelAppearance")}${btn("미리보기", "previewAppearance")}${btn("적용 / 저장", "saveAppearance", true)}</div>`,
  );
  let saved = false;
  const gather = () => {
    draft.korean_font = $("koFont").value;
    draft.english_font = $("enFont").value;
    draft.font_size = Number($("fontSize").value);
    if (draft.font_size < 8 || draft.font_size > 24)
      throw Error("글꼴 크기는 8–24 pt입니다.");
    draft.theme = $("theme").value;
    draft.viewer_quality = $("viewerQuality").value;
    draft.viewer_fps = Number($("viewerFps").value);
    draft.selection = $("selectionColor").value;
    draft.text_colors = { ...old.text_colors };
    for (const key of changedColors)
      draft.text_colors[key] = $("textColor-" + key).value;
    return draft;
  };
  $("modalBody")
    .querySelectorAll("[id^=textColor-]")
    .forEach((el) =>
      el.addEventListener("change", () => changedColors.add(el.id.slice(10))),
    );
  on(
    "elementColorChoice",
    () => {
      $("elementColorValue").value =
        draft.element_colors?.[$("elementColorChoice").value] ||
        config.colors[$("elementColorChoice").value];
    },
    "change",
  );
  on("applyElementColor", () => {
    draft.element_colors = {
      ...draft.element_colors,
      [$("elementColorChoice").value]: $("elementColorValue").value,
    };
    toast("원소 색상을 설정했습니다. 적용 / 저장을 누르세요.");
  });
  on("resetElementColors", () => {
    draft.element_colors = { ...config.colors };
    $("elementColorValue").value = config.colors[$("elementColorChoice").value];
  });
  on(
    "vestaImport",
    async () => {
      const file = $("vestaImport").files[0];
      if (!file) return;
      const text = await file.text();
      let count = 0;
      for (const line of text.split("\n")) {
        const words = line.trim().split(/\s+/);
        let symbol = words.find((v) => config.elements.includes(v));
        if (!symbol) continue;
        const numbers = words
          .slice(words.indexOf(symbol) + 1)
          .map(Number)
          .filter(Number.isFinite);
        if (numbers.length >= 3) {
          let rgb = numbers.slice(-3);
          if (rgb.every((v) => v >= 0 && v <= 1)) {
            draft.element_colors[symbol] =
              "#" +
              rgb
                .map((v) =>
                  Math.round(v * 255)
                    .toString(16)
                    .padStart(2, "0"),
                )
                .join("");
            count++;
          }
        }
      }
      if (!count) throw Error("원소 RGB 행을 찾지 못했습니다.");
      toast("원소 색상 " + count + "개를 읽었습니다.");
    },
    "change",
  );
  on("previewAppearance", () => {
    state.settings = structuredClone(gather());
    applyAppearance();
    viewer.draw();
  });
  on("cancelAppearance", () => modal.close());
  on("saveAppearance", async () => {
    const settings = gather();
    state.settings = old;
    await edit("settings", { settings });
    saved = true;
    modal.close();
  });
  modal.addEventListener(
    "close",
    () => {
      if (!saved) {
        state.settings = old;
        applyAppearance();
        viewer.draw();
      }
    },
    { once: true },
  );
}
function helpDialog() {
  show(
    "사용 안내 / 출처",
    `<ol class="help-list"><li>코어를 선택하고 빈 코어 초기화 또는 예제 완성을 누릅니다.</li><li>구조에서 원자를 선택합니다. 다중 선택은 클릭할 때마다 추가/해제하며, 사각형 모드는 앞뒤 원자 중심을 함께 선택합니다.</li><li>리간드 붙이기 → SMILES 입력/라이브러리 선택 → 결합 원자 선택 → 계획 추가 → 모두 적용 순서로 진행합니다.</li><li>R은 Sn–C, L/P는 O 두 점 가교입니다. Sn12 OH 버튼은 원래 코어의 H 6개를 제거하고 O 6개를 선택합니다.</li><li>회전·이동은 배율을 바꾸지 않습니다. 휠로 확대하고 맞춤 버튼으로 전체 구조를 맞춥니다.</li><li>초기 최적화·겹침 정리·결합/접촉/공명/기하 검사는 기존 Python RDKit/ASE 코드를 사용합니다.</li><li>Gaussian 입력은 간편/커스텀 설정에서 조절하고 미리보기 후 다운로드 또는 서버 경로로 저장합니다.</li><li>변경은 서버의 web-workspace.json으로 복구 저장됩니다. 전체 프로젝트 JSON 다운로드는 보관함·설정·즐겨찾기도 포함합니다.</li><li>서버 종료: 실행 터미널에서 Ctrl+C. 웹 모드에는 Tk / X11 / Node.js / 인터넷 연결이 필요하지 않습니다.</li></ol><p class="content-note">단축키: Ctrl+S 프로젝트 다운로드 · Ctrl+Z 실행 취소 · Ctrl+Shift+Z 복원 · Delete 선택 원자 삭제 · Esc 선택 해제.</p><h3>과학적 범위</h3><p class="content-note">힘장 에너지는 DFT 에너지가 아닙니다. 금속의 파라미터 존재는 정확성 보장이 아닙니다. 거리 후보는 결합 확정이 아니며 공명식 평균은 전자구조 결합차수가 아닙니다. 미완성 코어의 전하와 다중도는 직접 확인하세요.</p><h3>참고 / 좌표 출처</h3>${Object.entries(
      config.sources,
    )
      .map(
        ([k, v]) =>
          `<p class="content-note">${h(k)}<br><a href="${h(v)}" target="_blank" rel="noopener">${h(v)}</a></p>`,
      )
      .join(
        "",
      )}<pre>${h(JSON.stringify(state.project.metadata, null, 2))}</pre>`,
  );
}
async function saveDialog() {
  show(
    "프로젝트 저장",
    `<p class="content-note">프로젝트에는 현재 구조, 결합, 리간드 결합 원자, 보관함, 즐겨찾기, 화면 설정을 함께 기록합니다.</p><div class="dialog-actions">${btn("전체 프로젝트 JSON 다운로드", "downloadProject", true)}</div>${inputField("서버 저장 경로 (파일 이름 포함)", "projectServerPath", "", "text", 'placeholder="/home/user/tinoxo/project.tinoxo.json"')}<div class="dialog-actions">${btn("서버 경로에 저장", "saveProjectServer")}</div><p class="hint">브라우저 다운로드는 접속한 PC에 저장됩니다. 서버 경로는 Python이 실행되는 컴퓨터의 경로입니다.</p>`,
  );
  on("downloadProject", () => exportKind("project"));
  on("saveProjectServer", async () => {
    if (!$("projectServerPath").value.trim())
      throw Error("서버 파일 경로를 입력하세요.");
    await api("save", {
      revision: state.revision,
      kind: "project",
      path: $("projectServerPath").value.trim(),
    });
    toast("서버 경로에 저장했습니다.");
  });
}
const actions = {
  open: () => $("fileInput").click(),
  save: saveDialog,
  export: exportDialog,
  gaussian: gaussianDialog,
  appearance: appearanceDialog,
  help: helpDialog,
  reset: async () => {
    selectExact([]);
    await edit("reset", { n: core }, true);
  },
  example: () => task("example", { n: core }),
  hydroxo: async () => {
    await edit("hydroxo");
    await attachDialog();
  },
  attach: () => attachDialog(),
  library: libraryDialog,
  slots: slotsDialog,
  bank: bankDialog,
  copy: async () => {
    try {
      await navigator.clipboard.writeText(xyz());
      toast("XYZ 좌표를 복사했습니다.");
    } catch {
      download(xyz(), "tinoxo.xyz");
      toast("클립보드 권한이 없어 XYZ 파일을 다운로드했습니다.");
    }
  },
  optimize: () => task("optimize", { scope: $("scope").value }),
  cleanup: () => task("cleanup"),
  bonds: bondsDialog,
  geometry: geometryDialog,
  resonance: resonanceDialog,
  contactSettings,
  refreshContacts,
  snc: () => edit("snc", { length: Number($("snc").value) }),
  selectSn: () =>
    selectExact(
      state.project.atoms.filter((a) => a.element === "Sn").map((a) => a.id),
    ),
  selectAll: () => selectExact(state.project.atoms.map((a) => a.id)),
  deselect: () => selectExact([]),
  fit: () => viewer.fit(),
  undo: () => edit("undo", {}, true),
  redo: () => edit("redo", {}, true),
  fixed: () => edit("fixed"),
  atomColor: () => edit("color", { color: $("selectedColor").value }),
  delete: async () => {
    if (!selection.length) throw Error("삭제할 원자를 선택하세요.");
    await edit("delete");
  },
  selectH: () => {
    const aa = new Map(state.project.atoms.map((a) => [a.id, a]));
    const ids = [...selection];
    for (const b of state.project.bonds) {
      if (selection.includes(b.a) && aa.get(b.b).element === "H") ids.push(b.b);
      if (selection.includes(b.b) && aa.get(b.a).element === "H") ids.push(b.a);
    }
    selectExact(ids);
  },
  selectLigand: () => {
    const groups = new Set(
      state.project.atoms
        .filter((a) => selection.includes(a.id))
        .map((a) => a.slot)
        .filter(Boolean),
    );
    if (!groups.size) throw Error("리간드 내부 원자를 선택하세요.");
    selectExact(
      state.project.atoms.filter((a) => groups.has(a.slot)).map((a) => a.id),
    );
  },
  cancel: () => api("cancel", {}),
};
function bindShell() {
  document.querySelectorAll("[data-action]").forEach((b) =>
    b.addEventListener(
      "click",
      guard(() => actions[b.dataset.action]()),
    ),
  );
  document
    .querySelectorAll("[data-close]")
    .forEach((b) => (b.onclick = () => $(b.dataset.close).close()));
  document.querySelectorAll("[data-core]").forEach(
    (b) =>
      (b.onclick = () => {
        core = Number(b.dataset.core);
        document
          .querySelectorAll("[data-core]")
          .forEach((v) => v.classList.toggle("active", v === b));
      }),
  );
  document.querySelectorAll("[data-mode]").forEach(
    (b) =>
      (b.onclick = () => {
        mode = b.dataset.mode;
        document
          .querySelectorAll("[data-mode]")
          .forEach((v) => v.classList.toggle("active", v === b));
      }),
  );
  for (const [attr, ids] of [
    ["left", ["build", "calculate"]],
    ["right", ["selection", "slotList", "contacts"]],
    ["output", ["coordinates", "log"]],
  ])
    document.querySelectorAll(`[data-${attr}]`).forEach(
      (b) =>
        (b.onclick = guard(async () => {
          for (const id of ids)
            $(id).classList.toggle("hidden", id !== b.dataset[attr]);
          document
            .querySelectorAll(`[data-${attr}]`)
            .forEach((v) => v.classList.toggle("active", v === b));
          renderLazyPanels();
          if (b.dataset[attr] === "contacts") await refreshContacts();
        })),
    );
  on(
    "ff",
    () => edit("settings", { settings: { ff: $("ff").value } }),
    "change",
  );
  for (const id of ["showH", "showLabels", "coreOnly"])
    $(id).onchange = () => viewer.draw();
  $("slotsTable").addEventListener("click", (e) => {
    const tr = e.target.closest("[data-slot]");
    if (!tr) return;
    selectedSlot = tr.dataset.slot;
    const s = state.project.slots.find((s) => s.id === selectedSlot);
    selectExact([...s.sn, ...(s.ligandIds || [])]);
  });
  $("slotsTable").addEventListener(
    "dblclick",
    guard((e) => {
      const tr = e.target.closest("[data-slot]");
      if (tr) return attachDialog(tr.dataset.slot);
    }),
  );
  $("atomForm").addEventListener(
    "submit",
    guard(async (e) => {
      e.preventDefault();
      const values = Object.fromEntries(new FormData($("atomForm")));
      await edit("atom", { values });
    }),
  );
  $("fileInput").addEventListener(
    "change",
    guard(async () => {
      const file = $("fileInput").files[0];
      if (!file) return;
      if (file.size > 24 * 1024 * 1024)
        throw Error("구조 파일은 24 MB 이하로 선택하세요.");
      const content = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      selectExact([]);
      await edit("import", { name: file.name, content }, true);
      $("fileInput").value = "";
      toast(file.name + " 불러오기 완료");
    }),
  );
  document.addEventListener(
    "keydown",
    guard(async (e) => {
      if (
        ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) ||
        modal.open ||
        picker.open
      )
        return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        await exportKind("project");
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        await actions[e.shiftKey ? "redo" : "undo"]();
      } else if (e.key === "Delete") {
        e.preventDefault();
        await actions.delete();
      } else if (e.key === "Escape") selectExact([]);
    }),
  );
}
async function start() {
  try {
    [config, state] = await Promise.all([api("config"), api("state")]);
    viewer = new MoleculeViewer(
      $("molecule"),
      $("overlay"),
      () => ({
        project: state?.project,
        selection,
        settings: state?.settings || {},
        showH: $("showH").checked,
        labels: $("showLabels").checked,
        coreOnly: $("coreOnly").checked,
        mode,
        colors: config.colors,
        radii: config.radii,
      }),
      select,
    );
    $("elements").innerHTML = config.elements
      .map((v) => `<option value="${v}">`)
      .join("");
    bindShell();
    render();
    viewer.fit();
    $("connection").classList.add("hidden");
    if (state.job?.status === "running") guard(() => pollJob())();
  } catch (error) {
    $("connection").innerHTML =
      `<div class="token-prompt"><h2>로컬 작업 공간 연결</h2><p class="content-note">${h(error.message)}</p><p class="content-note">터미널에 출력된 #token=…이 포함된 전체 주소로 접속하거나 접속 토큰을 입력하세요.</p><input id="accessToken" type="password" placeholder="접속 토큰"><button id="connectToken">연결</button></div>`;
    $("connectToken").onclick = () => {
      token = $("accessToken").value.trim();
      sessionStorage.setItem("tinoxo-token", token);
      start();
    };
  }
}
start();
