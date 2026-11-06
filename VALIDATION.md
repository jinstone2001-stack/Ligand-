# Validation — 2026-11-06

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
