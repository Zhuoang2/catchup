# Update frontend dev dependencies: implementation checks

2026-11-03, branch `update-frontend-dev-deps`, from `aec273c` (plan). Node 20.19.0, npm 10.8.2, public npm registry (`https://registry.npmjs.org/`). Commands ran from `frontend/` unless a directory is given. The implementer was Claude Code (a Claude Opus 5.5 sub-agent), in place of Factory Droid, whose login had expired.

## 1.1 Red baseline (before any change)

| Check | Actual result |
| --- | --- |
| `npm ci` | Added 124 packages, audited 125; reported 3 vulnerabilities (2 moderate, 1 high). |
| `npm audit` | Expected red: **exit 1**, **3 vulnerabilities (2 moderate, 1 high)**, for `vite` and `@vitest/mocker` (with `vitest` through it). Output below. |
| `npm audit --omit=dev` | Exit 0, `found 0 vulnerabilities`. |
| `npm ls vite vitest @vitest/mocker` | Exit 0: `vite@8.3.2`, `vitest@4.1.11`, `@vitest/mocker@4.1.11`. |
| `npm test -- --run` | Baseline: **259 passed** in **14 files** (vitest 4.1.11). |

Red `npm audit` output:

```
# npm audit report

@vitest/mocker  <=4.1.11
Severity: moderate
Vitest: Code injection via unauthenticated manual mock registration - https://github.com/advisories/GHSA-qxg6-89mg-rqv8
Vitest: Windows backslash traversal bypasses the @vitest/mocker redirect allowlist fix - https://github.com/advisories/GHSA-xp26-3454-mjgp
fix available via `npm audit fix`
node_modules/@vitest/mocker
  vitest  2.1.0-beta.1 - 4.1.11
  Depends on vulnerable versions of @vitest/mocker
  node_modules/vitest

vite  8.3.0 - 8.3.2
Severity: high
launch-editor: escapeCmdArgs() omits % escaping on Windows - https://github.com/advisories/GHSA-698v-4r3x-3vcv
launch-editor: Editor CLI flag misinterpretation causing arbitrary command execution for some editors - https://github.com/advisories/GHSA-r825-w8mm-5pxw
launch-editor: `fs.existsSync()` existence check can be bypassed on Windows - https://github.com/advisories/GHSA-587h-7wmj-h5pm
Vite: Cross origin script execution through Vite custom middleware - https://github.com/advisories/GHSA-9jrq-w75r-8gcw
Vite: Files outside `server.fs.allow` could be served when project paths match system paths on non-Windows machine - https://github.com/advisories/GHSA-rq7h-c2jc-7f22
Vite: First 4 bytes of files outside of `server.fs` setting is exposed by `?vite-wasm-instance` - https://github.com/advisories/GHSA-vfpm-58rq-9qcg
fix available via `npm audit fix`
node_modules/vite

3 vulnerabilities (2 moderate, 1 high)

To address all issues, run:
  npm audit fix
```

## 1.2 Update

`npm install --save-dev vite@^8.3.5 vitest@^4.1.12`: exit 0, `changed 15 packages, and audited 125 packages`, `found 0 vulnerabilities`. On 2026-11-03 the registry's `vite` `latest` tag was 8.3.5 and the `vitest` `V4` tag was 4.1.12, so the floors resolved to those exact versions.

| Check | Actual result |
| --- | --- |
| 1. `git diff frontend/package.json` | Exactly two changed lines: `"vite": "^8.3.5"` and `"vitest": "^4.1.12"`. |
| 2. `npm audit` | **Exit 0**, `found 0 vulnerabilities`. |
| 3. `npm ls vite vitest @vitest/mocker @vitejs/plugin-react` | Exit 0: `vite@8.3.5`, `vitest@4.1.12`, `@vitest/mocker@4.1.12`, `@vitejs/plugin-react@6.1.1` with `vite@8.3.5 deduped`. |
| 4. Lockfile comparison against `git show 8faaed6:frontend/package-lock.json` (a short `python3 -I` script comparing `packages` versions) | **29 entries changed, 0 added, 0 removed**; the list is below. Apart from versions, the only other changed field is the root entry's two `devDependencies` floors. `npm explain` showed only paths through `vite` or `vitest` for all 15 changed packages installed on this machine. The 14 bindings for other platforms are covered by the lockfile check described below. `frontend/` and `extension/` were identical at `8faaed6` and `aec273c`, so the baseline lockfile is the one that 1.1 installed. |
| 5. `rm -rf node_modules && npm ci` | Exit 0: added 124 packages, audited 125, `found 0 vulnerabilities`. The lockfile stayed unchanged afterwards. |
| 6. `npm run build`; `npm test -- --run` | Build passed (`tsc --noEmit`, then `vite v8.3.5`, 40 modules). Tests: **259 passed** in **14 files** (vitest 4.1.12), the same as the baseline. Neither test run printed a warning. |
| 7. Dev server: `npx vite --port 5199 --strictPort` in the background, then `curl -sf http://localhost:5199/` retried every 0.5 s for up to 10 s | `VITE v8.3.5 ready in 381 ms`. The third attempt (about 1 s) returned HTTP 200, and the page contains `<div id="root">`. The server was then stopped: no process was left, and port 5199 refused connections. |

`npm audit` output after the update:

```
found 0 vulnerabilities
```

### Versions before and after

| Package | Before | After |
| --- | --- | --- |
| `vite` | 8.3.2 | 8.3.5 |
| `vitest` | 4.1.11 | 4.1.12 |
| `@vitest/mocker` | 4.1.11 | 4.1.12 |

### Changed lockfile packages (check 4)

All of these are in the plan's dry-run list. No package outside the `vite` and `vitest` trees changed.

- `vite` 8.3.2 → 8.3.5; `vitest` 4.1.11 → 4.1.12.
- Seven `@vitest/*` packages, 4.1.11 → 4.1.12: `expect`, `mocker`, `pretty-format`, `runner`, `snapshot`, `spy`, `utils`.
- `rolldown` 1.2.12 → 1.2.16, and its 15 `@rolldown/binding-*` packages 1.2.12 → 1.2.16: `android-arm-eabi`, `android-arm64`, `darwin-arm64`, `darwin-x64`, `freebsd-x64`, `linux-arm-gnueabihf`, `linux-arm64-gnu`, `linux-arm64-musl`, `linux-ppc64-gnu`, `linux-s390x-gnu`, `linux-x64-gnu`, `linux-x64-musl`, `openharmony-arm64`, `win32-arm64-msvc`, `win32-x64-msvc`.
- `@oxc-project/types` 0.152.0 → 0.156.0.
- `postcss` 8.5.28 → 8.5.32; `nanoid` 3.3.19 → 3.3.20.
- `@types/estree` 1.0.9 → 1.0.10.

Here is what `npm explain` showed for each of them:
- `vite` comes from the root project, as a peer of `@vitejs/plugin-react`, and through `vitest` and `@vitest/mocker`.
- `vitest` comes from the root project and as a peer of `vitest-axe`.
- Each `@vitest/*` package comes only through `vitest`.
- `rolldown`, `postcss`, and `@oxc-project/types` (through `rolldown`) come only through `vite`.
- `nanoid` comes only through `postcss`, and so through `vite`.
- `@types/estree` comes only through `estree-walker`, from `@vitest/mocker`.
- `@rolldown/binding-darwin-arm64`, the only binding installed on this machine, comes only through `rolldown`.

The other 14 bindings are optional packages for other platforms, so they are not installed here, and for each of them `npm explain` reports `No dependencies found` and exits 1. Instead, the new lockfile was checked for every entry that lists each binding in its `dependencies`, `optionalDependencies`, `peerDependencies`, or `devDependencies`. All 15 bindings are listed only in `node_modules/rolldown`'s `optionalDependencies`.

## 2.1 Full checks

| Check | Actual result |
| --- | --- |
| `npm run build` | Passed; `vite v8.3.5`, 40 modules. `frontend/dist` present. |
| `npm test -- --run` | **259 passed** in **14 files**. |
| `cd backend && uv run --python 3.12 pytest` (with `frontend/dist` present) | **776 passed**. |
| `cd extension && npm test -- --run` | **112 passed** in **8 files**; `git status` was clean afterwards. |
| `docker build -t catchup:update-frontend-dev-deps-local .` (repository root, Docker 29.8.0) | Passed. The frontend stage ran `npm ci` without the cache (added 125 packages, audited 126, `found 0 vulnerabilities`), then built with `vite v8.3.5`. |
| `scripts/docker-smoke.sh catchup:update-frontend-dev-deps-local` | **11 PASS lines**, exit 0: healthy container, `/api/health`, HTML at `/`, manifest, service worker, offline page, saved preference, non-root process, database on the volume, no `.env` or backend source in the image, and the preference survives a restart. The script removed its container and volume, and the image was removed afterwards. |
| `DO_NOT_TRACK=1 openspec validate update-frontend-dev-deps --strict` | `Change 'update-frontend-dev-deps' is valid` (`skip_specs` set, zero deltas accepted). |

Backend coverage was not remeasured, because no backend file changed. This change touched only `frontend/package.json`, `frontend/package-lock.json`, this change's `tasks.md`, and the docs under `docs/process/`.

**Manual check not performed:** running the dev server together with the backend (`npm run dev`, with `/api` proxied to port 8000) and using the app in a browser. The check above only confirms that the new `vite` dev server starts and serves `index.html`.
