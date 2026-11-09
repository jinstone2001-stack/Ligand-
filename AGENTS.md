# Ligand / Tin Oxo Studio

This repository contains the local Python chemistry engine, localhost browser
editor and optional Tk editor. Keep chemistry and existing project files
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

- A normal launch opens the selected localhost URL in the default browser,
  including when `SSH_CONNECTION` or `SSH_CLIENT` is present.
- Only explicit `--no-browser` disables automatic opening. Keep `--open-browser`
  accepted for compatibility with 4.2 commands.
- Always print the actual bound URL with its token. If the OS browser opener
  fails, keep the server available and give the complete URL to open manually.
- For HPC port forwarding, document explicit `--no-browser` and a PC browser.

## Validation

Run `python TinOxoStudio.py --check` and the relevant Python regressions before
publishing. Run the DOM and viewer-cache checks when web code changes. Optional
Tk GUI tests need a working display. Do not describe an OS opener mock, jsdom,
mock GL calls or native EGL pixels as a real user-browser or FPS check.
