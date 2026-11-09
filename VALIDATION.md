# Validation — version 4.3.0, 2026-11-09

- The clarified report is that Python prints the address without an error but no browser appears. The 4.2 launcher has a specific SSH guard that skips `webbrowser.open`. A pre-fix harness with `SSH_CONNECTION` set printed the URL and made **zero opener calls**; the harness stops the server loop with a simulated KeyboardInterrupt.
- Restore automatic opening unless `--no-browser` is explicit. `--open-browser` remains accepted for 4.2 command compatibility. Cover both `SSH_CONNECTION` and `SSH_CLIENT`, with default/explicit-open/explicit-opt-out combinations, and preserve the selected bound port and token in the URL.
- **122 Python tests pass** on Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0, including all 16 optional Tk GUI tests on a local X11 display and the native EGL/GLES pixel checks. This is the 119-test suite plus three launcher regressions.
- A real command-line subprocess for each SSH variable uses the actual Timer and HTTP server. An opener recorder captures the URL/new-tab request; an authenticated GET to that recorded URL returns the running 4.3 workspace. This verifies dispatch and server availability, **not an actual desktop browser window**.
- Opener false returns and OSError are checked for the complete manual URL and a successful launcher return. Existing port selection, occupied-port rejection, `--no-browser`, save/history, chemistry and transport regressions still pass.
- **22 DOM scenarios**, the 100-rotation viewer-cache regression, JavaScript syntax checks, `--check` and the versioned `--help` output pass. The renderer and chemistry optimizations are unchanged; the timing samples below remain the original 4.2 measurements.
- Publish one tested source tree/commit to both `ver-4.3` and `main`. The user requires this for future releases; `AGENTS.md` records the policy. The latest ZIP points to `main`, and the version-specific ZIP stays available.
- The user's actual environment variables and desktop browser were unavailable. The SSH guard is a reproduced regression matching the reported behavior; it does not establish that every browser-launch failure has the same cause. Real browser appearance/WebGL/FPS, the user's HPC/SSH/Windows session and Gaussian execution remain unverified.

# Earlier 4.2.0 validation record — 2026-11-07

- Full Python suite: **119 passing tests** on Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0, including the optional legacy GUI on a local X11 display. This adds 17 performance/correctness regressions and 2 native GLES pixel checks to the 100 existing checks. The browser server still starts without DISPLAY or Tk initialization.
- **22 DOM integration scenarios** pass against the real Python HTTP API with jsdom 26. New checks preserve the model and unchanged coordinate/selection nodes after settings updates, serialize rapid edits without stale revisions, report completed background saves, and page geometry results while keeping row selection. Canvas is mocked in this suite.
- A separate Node regression rotates a 2,752-atom model **100 times without any geometry rebuild, buffer upload or GL attribute lookup** after the first frame. It also checks selection-only buffer updates, model/palette/visibility invalidation, unchanged font/theme geometry, and CPU picking projection. GL calls are mocked; this does not measure GPU throughput.
- Native surfaceless Mesa EGL/GLES tests compile/link the shipped point and bond shaders and check actual rendered pixels for a sphere, selection ring and bond. These tests are optional where native EGL is absent. They establish native shader execution on this environment, not WebGL/browser integration or hardware GPU performance.
- Exact pose-score regressions compare dense and sparse implementations with the original algorithm under both contact criteria, including exclusions and rigid internal distances. A complete 252-pose search returns the same final coordinates (tolerance 1e-7 Å). Repeated ligand construction uses one cached fragment; invalid float/bool/string atom indices remain rejected. Geometry tables reuse one atom lookup and retain original measurements.
- History checks cover immutable snapshots across bank store/rename/delete/restore, reset, undo/redo, settings, favorites, contact changes and atom edits. A blocked disk writer does not hold the edit lock. Rapid saves coalesce, shutdown flushes the latest revision, closing rejects new edits, and actual disk errors remain visible without discarding current work. Existing synchronous persistence rollback tests remain available for the direct workspace API.
- Transport checks cover versioned partial responses, graph-free bank summaries, gzip, HTTP/1.1 connection reuse, conditional static caching, token/origin enforcement, stale revisions and SSH browser-opening overrides. Expensive read-only geometry/export operations and socket writes release the workspace lock.
- JavaScript syntax checks and `python TinOxoStudio.py --check` pass. Runtime dependencies are unchanged; Node/jsdom are development-only.
- **Real-browser appearance, browser WebGL integration and end-to-end FPS remain unverified**. On the 4.2 release pass, the cloud browser could be opened but could not connect to the isolated localhost test server (`ERR_CONNECTION_REFUSED`). The API itself was reachable from the test process. No user PC/HPC/SSH session, Windows opener or Gaussian executable was available. Do not interpret mock CPU timings or native Mesa pixels as a browser frame-rate guarantee.

## Reproducible performance measurements

Before is commit `2b73badafbf938be0dcc5f8d236531c084ba3405` (4.1.0); after is 4.2.0 (the same optimized code was measured while staged as 4.1.1). Python timings use five samples after warmup on Python 3.12.14. Raw wall/CPU samples are in [web_20261106.json](benchmarks/web_20261106.json); shared-host timing varies. Edit response timing includes JSON encoding and the old synchronous save; the new save completes separately in the background. It measures time to return an edit, not total persistence work or browser/network latency.

| Case | 4.1.0 median | 4.2.0 median |
|---|---:|---:|
| Attach hexyl to a bare Sn12 atom, 252 poses | 474.127 ms | 76.036 ms |
| Attach phenyl to a bare Sn12 atom, 252 poses | 309.015 ms | 27.692 ms |
| Contact cleanup, 86-atom methyl example | 577.413 ms | 32.099 ms |
| Geometry table, 688 atoms / 3,120 rows | 192.612 ms | 61.148 ms |
| Atom-color edit, 86 atoms / bank 0 | 3.077 ms | 0.678 ms |
| Atom-color edit, 86 atoms / bank 20 | 71.233 ms | 0.726 ms |
| Atom-color edit, 86 atoms / bank 100 | 371.970 ms | 0.414 ms |
| Atom-color edit, 688 atoms / bank 20 | 535.137 ms | 2.873 ms |

For the 86-atom / 100-entry bank case, uncompressed edit JSON drops from **2,527,221 to 25,267 bytes** (about 99% smaller). With the new gzip support the response is about 4.5 KB. Full project downloads continue to include all bank graphs. The benchmark's final attachment coordinates differ by **0 Å**.

JavaScript CPU submission measurements use 10 warmup / 60 measured rotations. **GL and Canvas calls are mocked**; the timings exclude real GPU work, browser rendering, compositing and network. With labels off and interactive drawing, the 2,752-atom model changes from 42.394 to 0.014 ms median in this CPU-only fixture; the stable result is **120 geometry uploads → 0** across the 60 measured frames. New frames still submit two draw calls and the GPU still processes the atoms/bonds. Raw data: [viewer_web_20261106.json](benchmarks/viewer_web_20261106.json).

Re-run in an isolated development checkout:

```bash
python benchmarks/benchmark_web.py /path/to/4.1.0 --output /tmp/web.json --viewer-input /tmp/viewer-input.json
node benchmarks/benchmark_viewer.mjs /path/to/4.1.0 /tmp/viewer-input.json
node tests/test_viewer.mjs
```

For full tests use `python -m unittest discover -s tests -v`. Optional GUI tests require Tk 8.6 and a working local DISPLAY. DOM tests require an isolated local test server and jsdom 26; see tests/test_frontend.mjs. Never run mutating tests against a user's workspace.

# Earlier 4.1.0 validation record

- Full Python suite: **100 passing tests** on Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0 with a local X11 display for the optional legacy GUI. This comprises 72 existing regressions and 28 new HTTP/workspace/launcher tests. The browser server itself starts with DISPLAY unset and does not initialize Tk.
- New tests cover port prompting/default/explicit/automatic selection, occupied-port errors, browser opening with the actual bound port and token, and a real command-line subprocess serving the API without DISPLAY.
- HTTP/workspace checks cover authenticated state/config, static UI and fonts, traversal rejection, Origin enforcement, malformed requests, revision conflicts, failed-edit rollback, failed-persistence rollback, atomic recovery, project upload/download including CP949, invalid bundle rejection, explicit server-path saving, bank/favorites/settings, and history.
- Real RDKit/ASE checks exercise SVG atom indices, a non-first N attached to two hosts, slot edits and Sn–C adjustment, example/optimization jobs, cancellation, unchanged state after invalid tasks, bond/contact/measurement/resonance requests, and Gaussian default/mixed/custom GenECP output.
- **19 DOM integration scenarios** pass using jsdom 26 and the real Python HTTP API. They cover initial connection, token storage, core reset, selection, fixed camera scale, SVG atom picking through RDKit attachment, undo/redo, shared Gaussian settings and download, theme/font preview, library/favorites, bank, geometry CSV, bond editing, resonance, contacts, clipboard/project download, upload/XSS-safe titles, and synchronous form navigation prevention.
- The DOM suite mocks Canvas; it does not establish actual GPU correctness or browser appearance. The provided browser runtime was unavailable, so **real-browser visual and WebGL verification are not completed**. The local API and DOM checks must not be described as browser screenshot QA. No user HPC/SSH session, Windows browser opener, or Gaussian executable was available for end-to-end testing.
- JavaScript syntax checks pass. Runtime has no Node/npm, external CDN, browser-side RDKit or web-framework dependency; jsdom is used only for development tests. Existing font files and notices are preserved.

Run the server with `python TinOxoStudio.py --port 8888` and use the printed full URL. For the optional DOM tests, install jsdom 26 as a development-only dependency and provide an isolated test server via TINOXO_TEST_URL / TINOXO_TEST_TOKEN; see tests/test_frontend.mjs. Do not run mutating tests against a real user workspace.

## Earlier 4.0 validation record

- Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0, local Xorg X11 at 1364×1024: **72 tests passed**, comprising 56 headless-compatible and 16 GUI checks. The same suite is run from an extracted 4.0 source package before publication. GitHub publishes the final branch as a source ZIP, retaining the same program, fonts, examples and tests.
- New chemistry checks verify attachment through non-first C, N and O atoms; retained N–H bonds for coordination; replacement of one O–H for covalent attachment; capping the old dummy position when the anchor moves; aromatic bond and stereochemical graph preservation; rejected invalid/dummy/saturated anchors; explicit bridge donor ordering and group selection; and project round-trip, same-ligand re-edit and clearing of the stored index.
- GUI checks exercise clicking a rendered atom, cancel without changing the project, one selected nitrogen applied to two Sn hosts, asynchronous application and undo, the shared Gaussian method/basis values, fixed-width selectors after window resizing, custom per-element basis/ECP, restoring uniform bases, and custom GenECP input through the rebuilt tabs.
- Main UI, ligand picker, quick/custom Gaussian tabs and light theme were visually inspected. The original-index atom list and 2× 2D drawing were checked against the selected atom. Korean and English resolved to bundled NanumGothic/Carlito on the local Linux display.
- A separate 144-DPI X11 pass checked the quick/custom layouts and the visible generate/save/close actions. Gaussian action space is reserved before the notebook, and tree row heights use actual font metrics. A large-font regression covers the previously compressed action row.
- Process-local Fontconfig setup is exercised before Tk creation. It loads a full configuration, parses rendering overrides into that allocated configuration, builds fonts, installs it as current, then registers bundled fonts. Existing font/encoding and viewer regressions still pass.
- Windows DPI-awareness initialization is implemented but Windows was not available for runtime validation. The user's HPC/MobaXterm session and a Gaussian 16 executable were not available. The Tk 8.6 environment remains the recommended GUI configuration.

## Earlier 3.1 validation record

- Python 3.13 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0, local Xorg X11 at 1600×1000: **54 tests passed** (44 headless-compatible, 10 GUI integration).
- New regressions check fixed orthographic pixels per Angstrom under 23 rotations of an anisotropic model; linear wheel zoom; invariance under window resizing, panning and visibility toggles; unchanged molecular coordinates/graph; coalesced motion events; reuse of Canvas item IDs; and final detailed drawing after release.
- Font checks cover the four requested closed choices, exact installed-family matching, explicit safe fallback, legacy preference migration, Korean glyph coverage in the bundled face, mixed text tags, Fontconfig face lookup and PNG generation, UTF-8/BOM/CP949 read/write without replacement.
- Main dark/light UI and all 12 dialogs were exercised. Korean and English font samples, actual resolved faces and server-side font import controls were visually inspected.
- Existing chemistry/file checks and GUI workflows continue to pass. No Gaussian executable or user HPC/MobaXterm connection was available.

## Local renderer measurements

75 frames per case, first 5 discarded. Measurements include render work and `update_idletasks`; they do not add artificial network latency. The 86-atom model is the supplied Sn12 methyl example; the 688-atom model contains eight translated copies. Frame pacing was bypassed only for measurement.

| Model | 3.0 median / p95 ms | 3.1 detailed median / p95 ms | 3.1 interactive median / p95 ms |
|---|---|---|---|
| 86 atoms | 14.62 / 17.76 | 5.29 / 5.97 | 2.26 / 2.48 |
| 688 atoms | 90.45 / 111.16 | 78.02 / 102.66 | 29.14 / 43.87 |

For the 86-atom model, displayed primitive count during interaction drops from 820 to 302; for 688 atoms, from 6560 to 2416. All atoms, bonds and selection coordinates remain. Hidden detailed items are reused, not recreated per frame. Full shading/segment detail returns on release. Raw results and methodology are in `benchmarks/viewer_x11_20261106.json`.

These numbers do not establish end-to-end FPS for a remote SSH/X11 link. Network RTT, bandwidth, X server implementation and server load may still limit response. The configured 15/20/30/60 FPS is a pacing target, not a throughput guarantee.

## Earlier 3.0 validation record

3.0 checks

- Python 3.12.14 / RDKit 2026.09.1 / ASE 3.29.0: 30 chemistry and file-format checks passed; 5 GUI checks skipped without DISPLAY.
- Python 3.13 / Tk 8.6 / RDKit / ASE, local Xorg dummy X11 display at 1600×1000: 35 checks passed, including 5 GUI integration checks.
- All 12 dialogs opened: ligand library, attachment, slot editor, measurements, bond audit, resonance, contact settings, Gaussian setup, appearance, structure bank, export, help.
- GUI integration exercised common attachment through real entry widgets and buttons; asynchronous result application; undo/redo; project save; custom SMILES persistence; Gaussian preview; and global Sn–C bond-length adjustment.
- Dark and light screenshots inspected. Korean text rendered with system Tk 8.6 and Noto CJK fonts. The primary runtime's Tk 9 build did not render CJK correctly; the provided environment pins Tk 8.6.
- Every built-in ligand SMILES parsed, and all built-ins generated a 3D fragment using the default MMFF94 path; single-atom halogens have no internal coordinates and skip force-field minimization.
- Sn12 methyl example: 86 atoms, 108 explicit bonds, zero contacts under the default criterion; Gaussian input has 872 electrons at charge +2 and multiplicity 1.
- Sn3 blank core: exactly 3 Sn, 3 O, 6 ring bonds; no H or central cap O.
- Sn12 hydroxo preparation removes exactly the six original core H atoms, is repeatable, preserves Sn/O coordinates, and returns the six O attachment sites.
- Isolated acetate test: MMFF94 C–O distances approximately 1.263/1.262 Å; UFF with the documented equivalent-terminal-O restraints approximately 1.261/1.262 Å.
- Sn6 carboxylate bridge rigid-fit RMSD approximately 0.024–0.029 Å; Sn3 phosphinate approximately 0.063 Å for the included test fragments. No core coordinates were changed.
- Gaussian builder checks all exposed job types, mixed-basis/ECP sections, electron/multiplicity parity, final blank lines, incompatible Sn/Pople basis selection, and duplicate dispersion corrections.
- SDF V3000 explicit dative-bond round trip and project JSON/legacy HTML round trips passed.

These are local functional and regression checks. No connection to the user's HPC or MobaXterm was available. A Gaussian 16 executable was not run; energy accuracy, optimization stability, and Gaussian runtime compatibility were not established by these tests.

Official gaussian.com documentation requests returned HTTP 403/502 or timed out. Relevant official URLs are included; input syntax was cross-checked against the Gaussian 16 manual hosted by CON FLEX. Documentation access and scientific assumptions are described in README_KO.md.
