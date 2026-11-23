# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (Context, D1–D3, and "Testing"), and the spec delta under `specs/local-deployment/`. The tasks implement option A of D1. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). Write the tests of task 1.1, run them, and watch them fail. Then change the code. The seams are named below, and they count as agreed:
  - `readFileSync` on `index.html`, `public/icon.svg`, `public/icon-192.png`, `public/icon-512.png`, `public/icon-1024.png`, and `public/offline.html`, as the tests in `frontend/src/install.test.ts` already do;
  - jsdom's `DOMParser` for the SVG;
  - `inflateSync` from `node:zlib` for the PNG data. The frontend has no `@types/node`: `npm run build` type-checks the tests against the hand-written declarations in `frontend/src/test/node-fs.d.ts`, which has no `node:zlib`. Add one line at the end of that file, `declare module 'node:zlib' { export function inflateSync(data: Uint8Array): Uint8Array }`, and change nothing else in it. That file types `readFileSync(path)` as `Uint8Array`, and `tsconfig.json` uses `lib` ES2022, so do not use `Buffer` methods or `Array.prototype.findLast` in the tests.
- **Test rules.**
  - Put the 16 × 16 pattern from design "Testing" in the test file as one constant, with `.` for `#f4f0e6` and `#` for `#151412`. Both new tests compare against it. Do not compute the pattern from `make-icons.py`.
  - Change no existing test.
  - For each named mutation, apply it alone, run the named test, record the result, and restore the code exactly. When a mutation changes `make-icons.py`, regenerate `public/` with it and again after restoring. Compare with `git diff` after restoring: only your intended changes remain.
- **Environment.**
  - Frontend and extension: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
  - Run the icon script from `frontend/` with `python3 scripts/make-icons.py`. It writes into `public/` and uses only the standard library.
  - Backend: run `uv run --offline pytest` in `backend/`, without installing packages.
- **Out of scope:**
  - `frontend/index.html`, `frontend/public/manifest.webmanifest`, `frontend/public/sw.js`, and every file outside `frontend/` except the test report and the AI usage log;
  - new icon files or sizes, and the maskable icon's box (`0.21`);
  - any extension file. The extension build copies the new `icon-192.png` by itself.
- **Do not edit** `proposal.md`, `design.md`, the spec delta, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-039 and the requirements row with the plan.
- **Docker.** Do not run `docker build`, `scripts/docker-smoke.sh`, or any Docker command. Do not use port 8800. Claude Code runs Docker at review.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. The mark on a 16 × 16 grid (D2)

- [x] 1.1 Write two failing tests in `frontend/src/install.test.ts`, inside `describe('install assets')`:
  - `draws the tab icon on the 16 px grid`.
    - Parse `public/icon.svg` with `DOMParser` (`image/svg+xml`).
    - Turn each `rect` into a rectangle (`x` and `y` default to 0) with its `fill`.
    - Turn the `path` into one rectangle per `M x y h length` segment: from `x` to `x + length`, and from `y - w / 2` to `y + w / 2`, where `w` is `stroke-width`, with its `stroke` as the color. If the `path` has any other command, fail the test.
    - Assert that every rectangle edge is a multiple of 64.
    - For each of the 16 × 16 pixel centers (`(i + 0.5) * 64`), take the color of the last rectangle that contains it, and assert that the result equals the pattern.
  - `keeps every app icon sharp at 16 px`. For `icon-192.png`, `icon-512.png`, and `icon-1024.png`:
    - Check the PNG signature. Read the chunks. Require `IHDR` bit depth 8, color type 2, and interlace method 0, and concatenate the `IDAT` data. Inflate it with `inflateSync`, and require filter type 0 at the start of every row. Any other format fails the test with a clear message.
    - Split the image into a 16 × 16 grid of square blocks (12 × 12 pixels at 192 px). Check that every pixel of a block is `#f4f0e6` where the pattern has `.`, and `#151412` where it has `#`. Compare in plain loops and call `expect` once per image, for example on a list of the first wrong pixels (file, block, pixel, color) that must equal `[]`. One `expect` per pixel takes about 5 s for the three images and hits Vitest's 5 s default timeout.

  Verify: both tests fail on the current icons. `draws the tab icon on the 16 px grid` fails on the grid check, because the square starts at 164. `keeps every app icon sharp at 16 px` fails at block (2, 2) of `icon-192.png`. The existing tests in `install.test.ts` still pass.
- [x] 1.2 Implement D2:
  - in `frontend/scripts/make-icons.py`, change `pixel()` to the grid rule in D2 (`0.125` for the square, `0.21` kept for the maskable icon, `unit = (right - left) / 12`), and change the SVG text to the one in D2, character for character;
  - run `python3 scripts/make-icons.py` in `frontend/` to regenerate `public/icon.svg`, `icon-192.png`, `icon-512.png`, `icon-1024.png`, and `icon-maskable-512.png`;
  - in `frontend/public/offline.html:7`, replace the `href` of the icon `<link>` with `data:image/svg+xml,` followed by the new `public/icon.svg` text, trimmed and percent-encoded as `encodeURIComponent` does. Change nothing else in that file.

  Verify:
  - `npx vitest run src/install.test.ts` passes in `frontend/`, including `regenerates byte-identical icons in a temporary directory` and `embeds the CatchUp tab icon in the offline page without another icon request`;
  - `git diff --stat` shows changes only in `make-icons.py`, the five icon files, `offline.html`, `install.test.ts`, and `src/test/node-fs.d.ts` (one added line);
  - mutations G1–G6 from design "Testing" each fail the test named there. For G5, write the mutated bar height as `max(1, int((right - left) * .055))`, because the new `pixel()` need not keep a `width` variable; if `make-icons.py` stops with an error, `public/` is not regenerated and the mutation has not been applied. Restore the code, and regenerate `public/` where needed, after each;
  - `npm test -- --run` and `npm run build` pass in `frontend/`, and `npm test -- --run` and `npm run build` pass in `extension/`.

## 2. Checks and report

- [x] 2.1 Run the full checks:
  - `uv run --offline pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate improve-small-icon-legibility --strict`;
  - `git diff --check`.

  Do not run `docker build` or `scripts/docker-smoke.sh`: Claude Code runs both at review.

  Write the commands and their real results to `docs/process/test-report-improve-small-icon-legibility.md`:
  - each new test, and the mutations it kills;
  - mutations G1–G6, with their results;
  - the Docker smoke and the live check from design "Testing", listed as not performed (Claude Code runs them at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
