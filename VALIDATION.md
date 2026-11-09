# Validation — version 5.2.0, 2026-11-09

Default launch remains the native Tk/X11 editor. This release adds a geometric exterior-placement rule before the existing contact score is used.

- **169 Python tests pass without skips** on the existing Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0 / NumPy 2.2.4 / SciPy 1.15.3 environment. This adds twelve geometry/attachment/API regressions and one native GUI regression to v5.1's 156 tests.
- Core centers use mass-weighted core atoms only, including explicit isotopes. Tests verify that a distant heavy ligand cannot shift the center, that a second disconnected core cannot shift the selected host's frame, and that translated/rotated planar envelopes behave consistently.
- Atom and analytic bond/convex-envelope intersection tests reject an empty-cavity crossing even when both bond endpoints are outside. Organic-parent attachment bonds are checked too. A 0.05 Å interior tolerance handles face touches; planar cores use +/-0.75 Å thickness and line/point cores a finite box. The reduced SVD avoids a quadratic-size matrix for large core atom lists.
- Every R site of Sn3/Sn6/Sn12 is tested with hexyl, along with generic Sn attachment and all six prepared Sn12 OH sites. New atoms/bonds remain outside the envelope, attachment vectors point outward, the requested 2.15 Å Sn-C length is preserved and core coordinates remain exact. L/P long-chain bridges preserve internal pair distances to 1e-10 Å and retain donor fits below 0.1 Å in the fixtures.
- Saved inward slot directions are corrected during automatic reattachment. Explicit inward manual vectors are rejected. An impossible pose search or cancellation restores old ligands and core H, not just coordinates. No-core organic attachment retains the local-valence path. HTTP job failure preserves revision/history and a successful native twelve-ligand example can be undone in one step.
- A comparison fixture with a hollow cubic core and exterior crowding reproduces the v5.1 problem: the anchor's radial projection was already outward (+0.636 Å), but part of the folded hexyl ligand entered the envelope. v5.2 rejects those poses and selects an exterior body (+0.817 Å anchor projection). This is a constructed geometric regression, not the user's unavailable project. A separate 63-case set of ordinary bare-template Sn attachments was already exterior in both versions.
- Exterior validity is checked before contact scoring. Contact counts can therefore be higher than an invalid inward candidate's count; exterior placement does not guarantee zero contacts. The dense/sparse contact score equivalence tests still pass, and the reference full-pose search agrees with the optimized scorer after invalid candidates are excluded.
- **29 DOM integration scenarios pass** with the real Python API and jsdom 26. The 100-rotation viewer-cache regression, JavaScript syntax checks, `--check` and `--help` pass. Native GUI checks include the exterior example, progress and undo. The X11 exterior example and direction help were visually inspected; browser Canvas remains mocked.
- Extracted source dependencies and all SHA-256 manifest entries are checked before publication. The new `TinOxoPlacement.py` must ship with the rest of the program.

The envelope is a conservative geometric model built from nonH core atom centers, not an electron-density surface or an additional force-field term. Initial generation and legacy automatic rigid rotation use it. Separate force-field/scoped optimizations retain their existing models and constraints. Bridge donor coordinates are retained from the initial rigid fit; the chosen donor/center RMSD is recomputed. New placement metadata records the core mass center, core IDs, envelope method and accepted/rejected pose counts.

The user's actual failing project, HPC/X11 session and PC clipboard bridge were unavailable. No remote FPS, browser appearance/WebGL or Gaussian execution claim is made. Re-run using the commands in the earlier records below.

# Earlier 5.1.0 validation record — 2026-11-09

Default UI remains Python/Tk/X11. This release fixes the reproduced UFF model-preparation error and makes the native calculation panel compact.

- **156 Python tests pass without skips** on Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0 / NumPy 2.2.4 / SciPy 1.15.3. This adds seven force-field/API tests and four native GUI tests to v5.0's 145 checks.
- The old `project_to_rdkit(..., sanitize=True)` failure is reproduced on Sn12: a high-coordinate neutral Sn exceeds RDKit's ordinary allowed valence. UFF itself already supplies a standard Sn3 atom type. The new calculation model relaxes that check only for Sn, keeps strict checks on other atoms, skips inferred radicals, and preserves input graph/coordinates/charges/radicals. A carbon with five H bonds is still rejected.
- Bare and completed Sn3/Sn6/Sn12 models all build actual UFF energy/gradient objects with finite values. Completed models are minimized in all four scopes: energies decrease or remain unchanged, permitted atoms move, fixed coordinates are exact and rigid pair distances remain unchanged to 1e-10 Å. The original project and stored bonds are unchanged. These tests use standard RDKit parameters, not mocked force fields.
- With fallback disabled, a whole Sn model requested as MMFF94 gives a precise missing-Sn-type error and preserves the project. With fallback enabled, UFF runs using the requested scope, stores requested/actual fields, and agrees exactly with a direct UFF run. Unsupported organic MMFF types (boron fixture) also use UFF; a supported organic fixture stays MMFF94. The HTTP worker reports the actual UFF result and respects fallback opt-out.
- New native tests use real X11 pointer movement to open/close `(?)` help, and check keyboard opening/dismissal. They verify current R/L/P host descriptions, site-row selection highlighting and a real Sn primary optimization action with MMFF-to-UFF result text, fixed core and undo.
- At the default 1540×940 window on a 1600×1000 Xorg display, calculation controls require 736 px inside an 824 px viewport, including the final Gaussian button. The banner is above the viewer pane. Smaller windows or larger fonts retain scrolling; this is not a guarantee that all settings fit every display.
- **29 DOM scenarios pass** against the real API using jsdom 26, including focusable help, scope help content, progress placement, enabled Sn fallback and actual-force-field result text. Canvas is mocked. The 100-rotation viewer-cache regression and JavaScript syntax checks also pass.
- Native dark calculation/results, hover scope help and light R/L/P help layouts were visually inspected on local X11. Existing clipboard, cancellation/history, launchers, science, font, Gaussian input and native EGL/GLES checks remain in the full suite. `--check`, `--help` and an extracted source archive plus SHA-256 manifest are verified before publication.

RDKit's Sn typing may print `hybridization set to SP3` warnings for higher coordination: its UFF typer maps Sn to the standard Sn3 label. Those warnings do not stop the tested calculations. Generic UFF is not a fitted Sn oxo cluster potential, and lower force-field energy is not proof of physical accuracy. MMFF94 does not gain Sn parameters through fallback: the actual calculation is explicitly UFF. The separate ligand-only action continues to use the selected force field.

Primary references: [RDKit UFF atom typing](https://github.com/rdkit/rdkit/blob/master/Code/GraphMol/ForceFieldHelpers/UFF/AtomTyper.cpp), [RDKit Sn3 parameters](https://github.com/rdkit/rdkit/blob/master/Code/ForceField/UFF/Params.cpp), [RDKit force-field API](https://www.rdkit.org/docs/source/rdkit.Chem.rdForceFieldHelpers.html), [Open Babel MMFF94 implementation's supported elements](https://openbabel.org/docs/Forcefields/mmff94.html).

The user's HPC/MobaXterm/PuTTY display, PC-to-server clipboard bridge and a Gaussian executable were not available. Optional browser appearance/WebGL/FPS remain unverified. Reproduce with the commands in the earlier record below; GUI tests require DISPLAY or the developer-only `tests/run_x11.py` runner.

# Earlier 5.0.0 validation record — 2026-11-09

The v5.0 release defaults to the **Python/Tk/X11 GUI**, following the user's latest request. Browser mode requires explicit `--web`. Historical records below describe their original releases.

- **145 Python tests pass, no skips**, on Python 3.13.5 / Tk 8.6 / RDKit 2026.09.1 / ASE 3.29.0 / NumPy 2.2.4 / SciPy 1.15.3. This is the prior 122-test suite plus 14 chemistry/API regressions and 9 native/launcher regressions. The run includes the existing 16 GUI checks, 7 new real-X11 GUI checks, and native EGL/GLES pixel checks.
- Real MMFF94 and UFF calculations exercise all four scope modes on a parameterized organic fixture. Tests verify exact fixed coordinates, movement of permitted atoms, non-increasing force-field energy and unchanged input projects. Rigid transformations preserve all within-core and within-ligand pair distances to 1e-10 Å; nested branches and bridging ligands are grouped by connectivity. Numerical derivatives check the projected rigid gradient.
- All four geometric cleanup modes are tested on a Sn-core contact fixture. Their contact penalty agrees with the inspector for both radii/minimum modes; finite differences check the analytical gradient. Fixed coordinates and rigid shapes are preserved. Invalid scopes, missing cores, no movable atoms, invalid iteration budgets and cancellation fail without partial application.
- All 43 built-in SMILES parse and have zero net formal charge. The seven acid entries contain OH; L/P construction removes the donor proton and yields the intended anionic bridge. Nitro's necessary formal charges remain intact.
- Native tests use a temporary, authenticated Xorg display at 1600×1000. They verify default native dispatch, `--fresh`, the 5.0 window title, scope counts/atom selection, conditional contact fields, successful background cleanup, result/progress display and undo. A separate Tk/X11 process reads consecutive XYZ copies and receives updated coordinates. Entry/Text paste reads new clipboard contents, replaces selected text and preserves Korean. Cancellation at 50% keeps both the structure and undo history unchanged.
- A real no-DISPLAY CLI subprocess returns an actionable X11 error, without a URL or browser fallback. Web-only flags require `--web`. The previous real CLI/HTTP launcher regressions now explicitly select `--web` and retain v4.3's opening/opt-out behavior.
- **27 DOM integration scenarios pass** against the real Python API with jsdom 26. Added coverage includes all scope previews, manual fixed flags, active-only contact settings, clipboard refresh/fallback, cleanup scope and percentage/score/convergence rendering. Canvas remains mocked.
- The existing **100-rotation viewer-cache regression** passes. JavaScript syntax checks, `--check`, versioned `--help` and the SHA-256 manifest are checked. Main X11 calculation layout and contact dialogs were visually inspected locally; explanatory labels now wrap to their actual panel width.
- The recommended environment pins Tk below 9. A supplementary Python 3.12/Tk 9 run exposed an existing font-family fallback assertion in that Tk build; the supported Tk 8.6 run passes all font and GUI checks.

The user's HPC/MobaXterm/PuTTY session and PC-to-server clipboard bridge were not available. Local X11 validation is not a guarantee of remote latency, FPS or Windows clipboard forwarding. Optional browser appearance and browser WebGL/FPS remain unverified. No Gaussian executable was run.

Full-structure MMFF/UFF requires supported atom types and coordination environments; unsupported Sn environments explicitly stop rather than invent parameters. The separate H-capped ligand optimizer remains available. Geometric cleanup scores are arbitrary penalty units, not force-field energies. Progress is based on stages/completed items/iteration budget; 100% means the task finished, not necessarily that optimization converged.

Reproduce in an isolated development checkout:

```bash
python TinOxoStudio.py --check
python -m unittest discover -s tests -v  # Existing working X11 DISPLAY
# Or developer-only Xorg + dummy driver + xauth:
python tests/run_x11.py
# Development-only Node + jsdom 26:
python tests/run_frontend.py
node tests/test_viewer.mjs
node --check web/app.js
node --check web/viewer.js
sha256sum -c SHA256SUMS.txt
```

References for the added coordinate engine: [RDKit force-field energy/gradient API](https://www.rdkit.org/docs/source/rdkit.ForceField.rdForceField.html), [SciPy L-BFGS-B](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html). The new code does not supply a scientific parametrization for Sn oxo clusters.

# Earlier 4.3.0 validation record — 2026-11-09

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
