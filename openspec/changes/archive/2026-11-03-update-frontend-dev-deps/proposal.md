# Proposal

## Why

`npm audit` in `frontend/` reports 3 vulnerabilities, all in development dependencies (#75, found in the system review of `add-x-accounts` on 2026-11-01). Rechecked on 2026-11-03 at `8faaed6`:
- **High:** `vite` 8.3.0–8.3.2, the dev server. The lockfile pins 8.3.2. The advisories are:
  - GHSA-9jrq-w75r-8gcw, cross-origin script execution through Vite custom middleware;
  - GHSA-rq7h-c2jc-7f22 and GHSA-vfpm-58rq-9qcg, files outside `server.fs` that can be served or partly exposed;
  - three `launch-editor` advisories, GHSA-698v-4r3x-3vcv, GHSA-r825-w8mm-5pxw, and GHSA-587h-7wmj-h5pm.
- **Moderate:** `@vitest/mocker` ≤ 4.1.11, and `vitest` through it. The lockfile pins 4.1.11. The advisories are GHSA-qxg6-89mg-rqv8 and GHSA-xp26-3454-mjgp.
- **Not affected:** `npm audit --omit=dev` reports 0. The Docker image runs only `vite build` (`Dockerfile:2-7`), and ships the built files, not `node_modules`.

The extension already resolves `vite` 8.3.5 and `vitest` 4.1.12, and its `npm audit` reports 0. On 2026-11-03, the registry's newest 8.x `vite` was 8.3.5 (`latest`), and the newest 4.x `vitest` was 4.1.12 (the `V4` tag; `latest` is 5.1.0).

## What Changes

- **Raise the two floors** in `frontend/package.json`, keeping its caret style:
  - `vite` from `^8.3.2` to `^8.3.5`;
  - `vitest` from `^4.1.11` to `^4.1.12`.
- **Update `frontend/package-lock.json`** with `npm install` for those two packages only. This brings `vitest`'s `@vitest/*` packages to 4.1.12, and those of `vite`'s dependencies that 8.3.5 requires: `rolldown` and its platform bindings, `@oxc-project/types`, and `postcss`, with `nanoid` possibly. No other direct dependency changes version.
- **Out of scope:**
  - `vitest` 5, a major upgrade;
  - `@vitejs/plugin-react` (6.1.1, no advisory, and its `vite ^8.0.0` peer range covers 8.3.5);
  - the extension's `package.json` floors, which still read `^8.3.2` and `^4.1.11` while its lockfile resolves the fixed versions;
  - adding `npm audit` to CI.
- **No change** to runtime code, behavior, or specs, so `skip_specs: true` is set.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. Development dependencies only; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- `frontend/package.json` (two lines) and `frontend/package-lock.json`.
- The frontend build, the frontend tests, and the dev server run on the new versions. The Docker image's frontend stage runs `npm ci` from the new lockfile.
- In `docs/process/`: a test report, a coverage-summary line, and AI usage log entries.
