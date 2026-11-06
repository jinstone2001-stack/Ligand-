# Validation — version 3.1.0, 2026-11-06

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
