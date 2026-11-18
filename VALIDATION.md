# HTML distribution validation — 5.2.0, 2026-11-18

Built from the current workspace's 5.2 implementation and disconnected-core placement fixes (base commit `4113a1c`). The published `html` branch contains only the standalone HTML, documentation and license files. No Python source or dependency binaries are included.

- The single-file artifact includes 43 built-in ligands and two example bridge variants. Its SHA-256 and the remaining distribution files are recorded in `SHA256SUMS.txt`.
- **Chrome 157 / Playwright offline-file regression passes.** Actual browser WebGL is used with a 390×844 mobile touch viewport and a 1440×900 desktop viewport. The test checks zero HTTP(S) requests and zero page JavaScript errors, responsive width, two-finger interaction, ligand atom picking/attachment, 5.2 exterior placement, undo/redo, JSON/Gaussian downloads and reload/recovery.
- All three completed core examples, rigid rotation cleanup with preserved core coordinates, JSON/XYZ/SDF/PDB/HTML round trips, executing an exported HTML with its saved structure, disconnected-core rejection, failure/cancellation rollback, invalid import rejection and Python-only operation rejection pass.
- JavaScript syntax and the existing 100-rotation viewer-cache regression pass. The cache test mocks GL calls; it is separate from the actual Chrome check. The mobile viewer layout was visually inspected from a Chrome screenshot.
- The source workspace's `--check`, 16 placement regressions and 7 force-field regressions pass. Its science tests pass 29/30 and Python server tests 30/31. Windows application-control policy blocks the `rdDetermineBonds` and `rdMolDraw2D` DLLs needed by the remaining two cases. The existing server DOM suite passes its first six scenarios and stops at the blocked Python SVG drawer. These are not represented as complete suite passes. The standalone HTML uses bundled coordinates/browser SVG and its picker passes in Chrome. No security policy was changed.

The mobile check is emulation, not a physical Android/iOS device test. Safari/Firefox, native Tk/X11/HPC clipboard bridging, remote FPS and actual Gaussian execution were not tested. Geometry placement/rigid rotation do not guarantee chemical validity, zero contacts or force-field convergence. Browser storage needs downloaded JSON backups.

Source checks and the HTML builder remain in the local workspace; they are not required to use this static distribution. Distribution source text uses LF line endings. Verify `SHA256SUMS.txt` against a downloaded ZIP or an LF checkout.
