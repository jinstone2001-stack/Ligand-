# Validation — version 4.0.0, 2026-11-06

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
