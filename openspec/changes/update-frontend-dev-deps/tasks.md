# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`. There are no spec deltas and no design document. If something looks wrong, stop and report.
- **Test-first** (D-016). This change has no new test. Its failing check is `npm audit`, which reports 3 vulnerabilities on the current lockfile. Record that red result before changing anything, then make it pass.
- **Run every npm command from `frontend/`,** unless a task says otherwise. Do not edit `package-lock.json` by hand.
- **OpenSpec commands** always run with the `DO_NOT_TRACK=1` prefix, for example `DO_NOT_TRACK=1 openspec validate update-frontend-dev-deps --strict`.
- **Out of scope:** `vitest` 5; `@vitejs/plugin-react` and every other direct dependency; the extension's `package.json`; CI changes; any source or test file.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Update vite and vitest

- [ ] 1.1 **Red baseline,** before any change:
  - `npm ci`;
  - `npm audit`: it exits non-zero, and reports 3 vulnerabilities (2 moderate, 1 high), for `vite` and `@vitest/mocker` (with `vitest` through it);
  - `npm audit --omit=dev`: it reports 0;
  - `npm ls vite vitest @vitest/mocker`: it shows `vite` 8.3.2, and `vitest` and `@vitest/mocker` 4.1.11;
  - `npm test -- --run`: record the number of tests and files, as the baseline for 1.2.

  Verify: the results match the above. If `npm audit` already reports 0, or other packages, stop and report.
- [ ] 1.2 **Update the two packages:** `npm install --save-dev vite@^8.3.5 vitest@^4.1.12`.

  Verify:
  1. `git diff frontend/package.json` shows only two changed lines: `"vite": "^8.3.5"` and `"vitest": "^4.1.12"`.
  2. `npm audit` reports `found 0 vulnerabilities`, and exits 0.
  3. `npm ls vite vitest @vitest/mocker @vitejs/plugin-react` exits 0. It shows `vite` 8.3.5 or a later 8.x, `vitest` and `@vitest/mocker` 4.1.12 or a later 4.x, and `@vitejs/plugin-react` 6.1.1 with `vite` deduped.
  4. **Only the vite and vitest trees changed.** Compare the `packages` versions of `git show 8faaed6:frontend/package-lock.json` with the new `package-lock.json`, for example with a short `python3` script. Every package whose version changed must appear under `vite` or `vitest` in `npm ls --all vite vitest`. A dry run in planning on 2026-11-03 changed:
     - `vite` and `vitest`;
     - the seven `@vitest/*` packages;
     - `rolldown`, its `@rolldown/binding-*` packages, and `@oxc-project/types`;
     - `postcss` and `nanoid`;
     - `@types/estree`, through `@vitest/mocker`.

     List the actual changes in the report. If a package outside those two trees changed, stop and report.
  5. `rm -rf node_modules && npm ci` succeeds from the new lockfile.
  6. `npm run build` passes, and `npm test -- --run` passes with the same number of tests and files as the 1.1 baseline.
  7. **The dev server still serves.**
     - Start `npx vite --port 5199 --strictPort` in the background.
     - `curl -sf http://localhost:5199/` returns the page, and the page contains `<div id="root">`.
     - Stop the server.

## 2. Checks and report

- [ ] 2.1 Run the full checks:
  - in `frontend/`: `npm run build`, then `npm test -- --run`;
  - in `backend/`: `uv run --python 3.12 pytest`, with `frontend/dist` present;
  - in `extension/`: `npm test -- --run`. The extension does not change; this checks that nothing else did;
  - from the repository root: `docker build -t catchup:update-frontend-dev-deps-local .`, then `scripts/docker-smoke.sh catchup:update-frontend-dev-deps-local`. The image's frontend stage runs `npm ci` and `npm run build` from the new lockfile;
  - `DO_NOT_TRACK=1 openspec validate update-frontend-dev-deps --strict`.

  Write `docs/process/test-report-update-frontend-dev-deps.md`, a new file, with:
  - the commands and their real results;
  - the red `npm audit` output of 1.1, and the `npm audit` output of 1.2;
  - the before and after versions of `vite`, `vitest`, and `@vitest/mocker`;
  - the list of changed lockfile packages from 1.2, check 4;
  - the manual check that was not performed: using the dev server with the backend (`npm run dev`, with `/api` proxied to port 8000) in a browser.

  Add this change's line to `docs/process/coverage-summary.md`, in the style of the existing lines. The backend is not remeasured.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
