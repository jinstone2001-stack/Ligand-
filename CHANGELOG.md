# Changes

## Unreleased

- Check ligand atoms and bond crossings against every disconnected core's own envelope while keeping the host core's mass center for direction. Leave the space between separate cores available for placement.
- Fail legacy rigid cleanup when no exterior pose exists and restore the entire input project on failure or cancellation, including ligands rotated earlier in the same operation.

## 5.2.0 — 2026-11-09

- Generate core-bound ligands in an exterior cone based on the mass-weighted center of the connected core, excluding existing ligands and respecting explicit isotope masses. Do not reuse saved inward directions during automatic reattachment.
- Reject poses with new ligand atoms or internal bond segments inside a geometric convex core envelope, including empty cavity crossings. Check organic-parent attachment bonds too. Keep local valence placement for structures without a core.
- Preserve bridge donor positions while searching rigid exterior orientations; retain internal molecular shape and report the selected fit RMSD. Explicit inward manual vectors are rejected with guidance.
- Restore the complete input structure, including old slots and removed H, when placement fails or is cancelled. Apply the interior check to legacy automatic rigid rotation as well. Store placement diagnostics with the slot.
- Retain native X11 defaults and the compact 5.1 UI; explain the direction policy through `(?)` help. Add mass/frame, cavity/bond, all core-site, bridge, rollback, HTTP and native GUI regressions.

## 5.1.0 — 2026-11-09

- Replace long native calculation explanations with `(?)` hover help, including click and keyboard access. Use compact controls so the default X11 calculation panel fits one 1600×1000 screen. Keep scrolling for smaller screens or larger fonts.
- Move progress, percentage, elapsed time, cancellation and result summary directly above the structure viewer. Clear stale results when a new job starts and show the actual force field during calculation and in results.
- Explain R/L/P/U site types and current Sn host IDs through the same help controls. Selecting a site row highlights its host atoms and attached ligand.
- Fix the reproduced UFF failure: high-coordinate Sn was rejected by ordinary valence checking before UFF was built. Use a calculation copy with strict nonSn validation and unchanged charges/radicals/connectivity, allowing RDKit's existing Sn3 UFF type to run on Sn3/Sn6/Sn12. No new fitted metal parameters are introduced.
- MMFF94 lacks Sn atom types. Add an explicit, default-on GUI/API option to use UFF when full-structure MMFF94 parameters are unavailable. Record requested/actual force field and fallback; the direct engine API remains strict by default. Supported MMFF models and ligand-only calculations retain the selected force field.
- Keep optional web mode consistent with compact help, progress placement, fallback control and result labelling. Extend real Sn chemistry, X11 hover/layout/site/optimization and DOM regressions.

## 5.0.0 — 2026-11-09

- Make Python/Tk/X11 the default GUI again, as explicitly requested for v5.0. `--native` remains an alias; `--web` is required for browser mode and web-only options. Update native title, help, Conda Tk dependency and launch regressions.
- Share four scope plans between full-structure MMFF/UFF and contact cleanup: core fixed, all free, core only, and exact rigid ligand bodies with the core as reference. Expose actual fixed/moving counts, selection buttons and an optional per-atom fixed override (off by default in the UI).
- Preserve internal shape through rigid transforms, not stiff force-field penalties. Connected nested ligands and bridging ligands form whole bodies. Report unsupported force fields; retain H-capped fragment optimization as an explicitly separate legacy action.
- Separate force-field energy from geometric contact cleanup and show convergence/score summaries, maximum iterations, stage/iteration progress percentages, elapsed time and cancellation. Only successful native jobs add undo entries.
- Show and validate only active radii/minimum contact settings; retain the inactive method's values.
- Refresh X11 clipboard reads on every paste, replace selected text consistently and separate PRIMARY selections from CLIPBOARD. Refresh XYZ on every copy. Optional web copy also awaits edits and refreshes server state, with denied-permission fallbacks.
- Supply seven built-in carboxylic/phosphinic acids in neutral protonated form. Retain L/P deprotonation chemistry, nitro formal charges and user-entered structures.
- Add real X11, separate-client clipboard, constraint/gradient/rigidity, async progress and DOM regressions. Keep prior renderer caching and launcher behavior within explicit web mode.

## 4.3.0 — 2026-11-09

- Restore 4.1's default browser-opening behavior. In 4.2, `SSH_CONNECTION` or `SSH_CLIENT` silently suppressed the opener while the server still printed its URL. Only explicit `--no-browser` now disables automatic opening. Keep `--open-browser` accepted for compatibility.
- Announce the automatic-open request and print the full URL if the OS opener returns false or raises a browser/OS error. Keep the Python server available for manual access.
- Reproduce the 4.2 SSH path (URL printed, zero opener calls), cover both SSH variables and opt-out combinations, and exercise the real CLI/Timer/HTTP server with an opener recorder. The recorder verifies the request, not a visible desktop window.
- Publish the release on `ver-4.3` and advance `main` to the same commit. Record the standing release rule in `AGENTS.md`; point the latest download at `main` and retain version-specific ZIP links.
- Preserve the 4.2 rendering, chemistry, transport, history and asynchronous-save optimizations.

## 4.2.0 — 2026-11-07

- Upload molecular world geometry once; rotate, pan and zoom using GPU uniforms. Cache attribute locations, selection buffers and projected picking points. Reduce interactive rendering detail/pixels, restore after release, add quality/frame controls and recover WebGL contexts. Keep UI text at browser resolution.
- Reuse exact placement scoring graphs, radii, thresholds and static environments for all 252 candidate poses; cache fragment generation within a batch. Preserve cancellation, donor indices and existing chemistry criteria. Reuse atom lookups for geometry tables.
- Replace whole-bank history copies with immutable copy-on-write snapshots. Send versioned changed sections and bank summaries; keep full graphs in explicit project exports. Serialize rapid edits and preserve unchanged DOM/model references.
- Coalesce automatic saves in a background writer; expose pending/saved/error state, flush on normal shutdown and reject new edits after closing. Read-only calculation/export work and socket writes release the workspace lock.
- Add HTTP keep-alive, gzip responses and conditional static asset caches. Page long inspection/library tables, debounce search and avoid updates to closed dialogs.
- Detect SSH and avoid launching a remote/X11 browser automatically; print local port-forwarding instructions. Preserve explicit --no-browser and add --open-browser for an intentional override.
- Add scientific equivalence, history/save/transport, native GLES pixel, DOM reuse/rapid-edit/pagination and GPU-buffer cache regressions. Include reproducible before/after benchmarks and their browser/GPU limitations.
- Publish the performance work previously staged as 4.1.1 on the separate `ver-4.2` branch. Include the complete Korean project history in `04.ligand.md` and align reported timing values with the saved raw benchmark samples.

## 4.1.0 — 2026-11-06

- Make the local browser UI the default. Prompt for a port when run interactively; support `--port`, automatic free port `0`, browser auto-open, `--no-browser`, `--fresh`, and isolated `--config-dir` workspaces. Keep `--native` for the Tk editor.
- Add a dependency-free Python HTTP adapter that reuses the original RDKit/ASE chemistry and Gaussian builder. No Tk, X11, Node.js, third-party web framework or CDN is required for web runtime.
- Move the editor UI to HTML/CSS, with browser font rendering, an orthographic WebGL molecular view (Canvas 2D fallback), SVG atom picking, and browser-local camera/selection operations.
- Connect core/example/hydroxo operations, shared/per-atom ligand plans, R/L/P/additional slots, atom/bond/contact/geometry/resonance controls, MMFF/UFF tasks and cancellation, structure bank, undo/redo, settings, and Gaussian quick/custom/export workflows.
- Add atomic web workspace recovery, browser file uploads/downloads, explicit server-path saves, and PNG/SVG exports of the current molecular view. Previous project files and the original legacy HTML compatibility export remain supported.
- Bind to loopback by default, protect editing APIs with a per-run token and same-origin checks, reject stale revisions, and serve only shipped UI/font assets. A failed edit/task leaves the previous molecular project intact.
- Add HTTP/workspace/launcher and DOM integration regressions. DOM checks use a mocked Canvas against the real Python API; actual browser appearance and GPU execution could not be verified because the browser runtime was unavailable.

## 4.0.0 — 2026-11-06

- Add a clickable, 2× rasterized RDKit 2D ligand popup with the original SMILES atom numbers, a selectable atom list, and explicit confirmation/cancellation. Library selection opens the popup; manual SMILES are checked before adding/applying a plan.
- Pass the chosen original atom index to fragment generation and attachment without rewriting or canonicalizing SMILES. Keep stereochemical graph indices, apply one selection to multiple hosts, persist `attachmentIndex`, and reuse it when editing the same ligand.
- Replace one H at the selected covalent anchor; preserve H for coordination. When an existing dummy is moved, cap its former position with H. For L/P bridges, select the donor group and donor-to-host order explicitly.
- Configure process-local Fontconfig outline glyphs, grayscale antialiasing and full hinting before Tk creation. Use a complete private configuration, build fonts, then set it current. Set Windows DPI awareness before Tk initialization, and scale small explanation text with the chosen font size (minimum 10 pt).
- Rebuild Gaussian setup as shared **간편 설정 / 커스텀 설정 / 입력 미리보기** tabs. Combine method/XC and basis/ECP controls; preserve element-specific bases, external Gen/GenECP, XC composition and detailed SCF/property controls.
- Halve selector character widths (32→16, 52→26), remove expansion of those fields, and provide an explicit uniform-basis action that clears element overrides.
- Reserve Gaussian action-button space before the notebook and size table rows from font metrics so higher DPI or larger text cannot compress the save actions or clip table text.
- Extend regression coverage to 72 passing checks, including 16 GUI checks on local X11/Tk 8.6. Inspect dark/light layouts and ligand atom selection. Gaussian execution, Windows and the user's remote HPC session are not covered by these local checks.

## 3.1.0 — 2026-11-06

- Restrict Korean font preferences to 맑은고딕 / 굴림 and English preferences to Arial / Calibri. Migrate legacy font settings, show actual resolved faces, and separate Korean UI / English code and labels.
- Bundle unmodified OFL NanumGothic and Carlito fallbacks; register process-private Fontconfig faces. Add a server-side TTF/TTC/OTF import control without requiring administrator permissions.
- Read UTF-8 including BOM and legacy Korean CP949 text without replacement characters; save canonical UTF-8. Tag Hangul ranges separately in mixed text boxes.
- Replace delete-and-recreate rendering with retained Canvas items, static geometry/style caches, vectorized projection, and batched Tcl coordinates/depth updates.
- Coalesce camera events with configurable frame pacing. Use lightweight bicolor bonds and flat atoms during rotation/pan; restore detailed drawing on release. Geometry, atom visibility and selections are preserved.
- Keep orthographic pixels per Angstrom and rotation center fixed across rotation, pan, resizing and visibility changes. Wheel changes zoom; Fit explicitly resets zoom and fits the full structure.
- Preserve high-quality geometry in PNG/SVG exports and use the resolved English face for image labels.
- Cancel scheduled GUI callbacks on destruction. Add camera/font/encoding/GUI regressions, bringing the local X11 suite to 54 checks.

## 3.0.0 — 2026-11-06

Initial native Tk/X11 editor with RDKit/ASE ligand chemistry, geometry and bond checks, project management, and Gaussian 16 input generation. The original 3.0 archive remains available under `dist/`.
