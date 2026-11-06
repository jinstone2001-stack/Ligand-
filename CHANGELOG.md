# Changes

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
