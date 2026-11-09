# Ligand / Tin Oxo Studio

This repository contains the local Python chemistry engine, default Tk/X11
editor and optional localhost browser editor. Keep chemistry and existing project files
compatible when fixing the launcher or UI.

## Release policy

The user requires **every new published version to become the latest `main`**.

- Publish a version branch named `ver-X.Y` and update `main` to the **same tested
  release commit**. Do both as part of a requested version release; this is the
  user's standing instruction, not a separate approval step.
- Read the current remote heads before writing. Preserve existing history and
  unrelated changes. Prefer a fast-forward update with the observed `main` SHA
  as an expected-head guard. Do not force-push over concurrent changes.
- Verify the version branch and `main` identify the same commit after publishing.
- Keep old version branches available. Use the `main` ZIP for the latest
  download and a version-branch ZIP for a pinned release.
- Update the app version, web title, README files, changelog, `04.ligand.md`,
  validation record and SHA-256 manifest in the same release.

## Launcher contract

- The user explicitly changed v5.x to a **native X11 GUI release**, like v4.0.
  A normal `python TinOxoStudio.py` launch must open Tk, never a browser/server.
- Keep `--native` as an alias for the default. Only `--web` opts into the browser
  interface. Reject web-specific flags without `--web` with clear guidance.
- Missing DISPLAY/Tk must produce an actionable X11 error, not silently fall
  back to a browser. Preserve SSH's DISPLAY and document X11 forwarding.
- In optional `--web` mode, preserve v4.3's browser-opening behavior, complete
  token URL, explicit `--no-browser` and `--open-browser` compatibility.
- Native v5 controls must expose the same chemistry constraints as the web API.
  Never label contact penalties as force-field energy or 100% as convergence.

## Validation

Run `python TinOxoStudio.py --check` and the relevant Python regressions before
publishing. Run the DOM and viewer-cache checks when web code changes. Optional
Tk GUI tests need a working display. Do not describe an OS opener mock, jsdom,
mock GL calls or native EGL pixels as a real user-browser or FPS check.

## Force-field model contract

- UFF provides a standard Sn3 type. Prepare high-coordinate Sn on a calculation copy without imposing the ordinary neutral Sn valence-four check; retain strict checks for other atoms and preserve the saved graph, charges and radicals.
- MMFF94 has no Sn type. GUI/API fallback to UFF must be controlled by an explicit option and record requested and actual force fields. The direct engine API stays strict unless fallback is enabled. Never call a UFF result MMFF94.
- Keep separate ligand-only optimization in the selected force field. General UFF parameters are not a fitted Sn oxo cluster model.

## Ligand placement contract

- Use core-only mass centers, not the whole ligand-bearing structure. Select the connected core belonging to the hosts and respect isotope masses.
- Automatic core-bound directions must face outward. Reject interior atoms/bond crossings before contact scoring, including organic-parent attachment bonds. Keep explicit core-to-donor boundaries distinct.
- Preserve molecular shape and bridge donor positions. Report inability to find a safe pose instead of bending bonds or inserting an inward fallback.
- Failed/cancelled attachment must restore the complete input project. Record placement diagnostics, and keep initial placement rules distinct from force-field constraints.
