# Test report: improve-small-icon-legibility (#43, part 2)

## Implementation by Factory Droid, 2026-11-22

Implemented task groups 1 and 2 from approved plan `fae68c8`, option A of D1, using `openspec-apply-change` and `tdd`. Group 1 is commit `0df57ec`; group 2 records the checks and evidence. Review by Claude Code is still pending.

### Environment and scope

- All commands ran inside this change's worktree. Frontend and extension commands used `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`; `node --version` returned `v22.17.1` in each directory.
- `npm ci --offline --no-audit --no-fund` passed in both directories: 124 locked frontend packages and 120 locked extension packages. Both emitted the non-fatal `whatwg-encoding@3.1.1` deprecation warning.
- Backend checks used only the requested `uv run --offline pytest`. That command created `.venv`, built the local project, and materialized 60 cached packages automatically. No separate dependency-install command, package addition/upgrade, dependency declaration change, lockfile change, or online install was performed.
- The five icon files were generated only by `python3 scripts/make-icons.py` from `frontend/`, including every mutation regeneration. The maskable box remains `0.21`. Only the icon link's `href` changed in `offline.html`.
- Before the group-1 commit, `git diff --stat` showed only the nine planned frontend files and checkbox updates in `tasks.md`. No existing test, manifest, `index.html` declaration, service worker, backend source, or extension source changed. The only type declaration addition is the agreed one-line `node:zlib` declaration.

### Test-first evidence

The two new tests in `frontend/src/install.test.ts` share the fixed 16 × 16 literal pattern from the design, not values calculated from the generator:

| New test | Seam and checks | Mutations killed |
| --- | --- | --- |
| `draws the tab icon on the 16 px grid` | Reads the real SVG; jsdom parses ordered rect/path shapes. Rejects path commands outside `M x y h length`, checks every edge modulo 64, and compares the last shape at every pixel center with the fixed two-color pattern. | G1, G2, G3, G4 |
| `keeps every app icon sharp at 16 px` | Reads all three non-maskable PNGs, checks signature and 8-bit non-interlaced RGB format, concatenates/inflates IDAT with `inflateSync`, requires filter 0 per row, and compares every pixel in each block with the fixed pattern in plain loops. Records at most eight wrong pixels, with one pixel-result assertion per image. | G5 |

1. **Red, before generator/artwork edits:** `npx vitest run src/install.test.ts` exited 1: **2 failed, 5 passed, 7 total**, 1.00 s.
   - SVG: `SVG edge 164 must align to the 16 px grid`, received remainder **36**, expected **0**.
   - PNG: first mismatch in **`icon-192.png`, block (2, 2), pixel (24, 24)**, light `[244, 240, 230]` instead of the pattern's dark color.
   - All five existing tests passed unchanged.
2. **Green, after D2 and the offline copy update:** the same command exited 0: **7 passed in 1 file**, 1.23 s, including the existing byte-identical regeneration and offline embedding checks.
3. **Green, after restoring G6:** the same command exited 0: **7 passed in 1 file**, 2.16 s.

### Named mutations

Each mutation was applied alone. Its test result was inspected before the next mutation. Generator changes were followed by a successful `python3 scripts/make-icons.py` run, so both script and public artwork contained the mutation. Each edit was then reversed by editing, with regeneration again where needed. After every restore, `git diff -- frontend/scripts/make-icons.py frontend/public` showed the identical intended D2/offline diff, including the same generated binary object ids, and no mutation residue.

All selected runs exited **1**, with **1 failed, 6 skipped, 7 total**. These are intentional assertion failures, not generator errors or timeouts.

| Mutation | Applied change | Named test and observed failure |
| --- | --- | --- |
| G1 | SVG `stroke-width="64"` → `"38"` in the generator; regenerated public icons. | `draws the tab icon on the 16 px grid`: grid check failed at edge **397**, remainder **13** instead of 0. **Killed.** |
| G2 | First SVG bar `M320 416h384` → `M320 430h384` in the generator; regenerated. | Same SVG test: grid check failed at edge **398**, remainder **14** instead of 0. **Killed.** |
| G3 | SVG square `128/128/768/768` → `164/164/696/696` in the generator; regenerated. | Same SVG test: grid check failed at edge **164**, remainder **36** instead of 0. **Killed.** |
| G4 | First SVG bar `M320 416h384` → `M320 352h384` in the generator; regenerated. | Same SVG test: all edge checks passed; the **pattern comparison** failed because the first light bar moved from row 6 to row 5. **Killed for the required reason.** |
| G5 | `pixel()` bar height `int(unit)` → `max(1, int((right - left) * .055))`; regenerated successfully. | `keeps every app icon sharp at 16 px`: first mismatch at **`icon-192.png`, block (5, 6), pixel (60, 79)**, dark `[21, 20, 18]` instead of light. **Killed.** |
| G6 | Replaced only the offline page's inline SVG with the old artwork. | Existing `embeds the CatchUp tab icon in the offline page without another icon request`: decoded inline SVG differed from the current public SVG. **Killed.** |

Commands, from `frontend/` with the Node export above:

```sh
# G1, G2, G3, G4, each run separately after its own edit/regeneration/restore cycle:
npx vitest run src/install.test.ts -t "draws the tab icon on the 16 px grid"
# G5:
npx vitest run src/install.test.ts -t "keeps every app icon sharp at 16 px"
# G6:
npx vitest run src/install.test.ts -t "embeds the CatchUp tab icon in the offline page without another icon request"
```

### Group-1 verification

After all restores, all four required commands exited 0:

| Directory | Command | Actual result |
| --- | --- | --- |
| `frontend/` | `npm test -- --run` | **316 passed, 14 files**, 11.64 s |
| `frontend/` | `npm run build` | TypeScript and Vite passed, **40 modules**, built in 876 ms |
| `extension/` | `npm test -- --run` | **168 passed, 7 files**, 6.77 s |
| `extension/` | `npm run build` | TypeScript, Vite and `scripts/check-build.mjs` passed, **10 modules**, built in 1.30 s |

The suites and existing builds were already in the repository; only the two asset tests above were added.

### Task 2.1 final checks

All seven commands exited **0**. Output summaries below are from the repeated final checks, not the earlier group-1 runs. No unexpected red/green or invalid mutation attempt occurred.

Backend, `uv run --offline pytest` in `backend/`:

```text
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
collected 1082 items
======================= 1082 passed in 124.73s (0:02:04) =======================
```

Frontend, `npm test -- --run`:

```text
> catchup-frontend@0.2.0 test
> vitest --run
 Test Files  14 passed (14)
      Tests  316 passed (316)
   Duration  21.81s
```

Frontend, `npm run build`:

```text
> catchup-frontend@0.2.0 build
> tsc --noEmit && vite build
vite v8.3.5 building client environment for production...
✓ 40 modules transformed.
dist/index.html                   0.82 kB │ gzip:  0.41 kB
dist/assets/index-2FHpjrn6.css   20.50 kB │ gzip:  5.24 kB
dist/assets/index-CsE0Xhfv.js   318.09 kB │ gzip: 97.54 kB
✓ built in 932ms
```

Extension, `npm test -- --run`:

```text
> catchup-extension@0.2.0 test
> vitest --run
 Test Files  7 passed (7)
      Tests  168 passed (168)
   Duration  11.96s
```

Extension, `npm run build`:

```text
> catchup-extension@0.2.0 build
> tsc --noEmit && vite build && node scripts/check-build.mjs
vite v8.3.5 building client environment for production...
✓ 10 modules transformed.
dist/popup.html                    0.45 kB │ gzip: 0.29 kB
dist/icon-192.png                  0.52 kB
dist/readability-LICENSE.md        0.55 kB
dist/options.html                  0.76 kB │ gzip: 0.42 kB
dist/readability.js               89.98 kB
dist/assets/options-CUZyiacw.css   1.48 kB │ gzip: 0.72 kB
dist/assets/popup-DKe_ziKL.css     2.03 kB │ gzip: 0.86 kB
dist/assets/options-0axhCIRv.js    2.06 kB │ gzip: 0.98 kB
dist/assets/popup-CudKrUKx.js     14.15 kB │ gzip: 5.26 kB
✓ built in 366ms
```

Repository root, `DO_NOT_TRACK=1 openspec validate improve-small-icon-legibility --strict`:

```text
Change 'improve-small-icon-legibility' is valid
```

Repository root, `git diff --check`: **exit 0, no output**. The staged group-1 diff also passed `git diff --cached --check`.

### Not performed, reserved for Claude Code review

- Docker build and `scripts/docker-smoke.sh`: **not performed**, explicitly forbidden for this Droid run.
- Live check on a spare port and fresh volume: **not performed**. Review should fetch `/icon.svg`, `/icon-192.png`, and `/offline.html` from the built container; render SVG at 16 px and 32 px in headless Chrome and check two colors and the design pattern; and verify the built extension's copied PNG is the new file.
- No Docker command, container/volume operation, port 8800 use, browser/live check, push, merge, tag, or PR action was taken. No claim is made about the browser toolbar's scaling filter, installed-app refresh timing, or real-tab rendering.

## Review by Claude Code

Reviewed in worktree `review43` on the branch. Droid's run started at the plan commit `fae68c8` and ended at `f4b7f16`.

### Checks on `f4b7f16`

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1082 passed |
| Frontend `npm test -- --run`, `npm run build` | 316 passed; build passed |
| Extension `npm test -- --run`, `npm run build` | 168 passed; build passed; `dist/icon-192.png` is byte-identical to the new `frontend/public/icon-192.png` |
| `DO_NOT_TRACK=1 openspec validate improve-small-icon-legibility --strict` | valid |
| `git diff --check fae68c8 HEAD` | clean |
| `scripts/docker-smoke.sh catchup:fix43-local` | 12 of 12 |

### Live check

A scratch container from `catchup:fix43-local` ran on its own volume and port 8843.

- `/icon.svg`, the four PNG icons, and `/offline.html` as served were byte-identical to the files in `frontend/public/`. The page still declares the SVG and the 192 px PNG.
- Claude rendered the served `/icon.svg` with headless Chrome 157 (a temporary profile) at 16 px and 32 px, at device scale 1 and 2, and decoded the screenshots. Each had exactly the two mark colors, and the 16 px render matched the pattern in design "Testing" pixel for pixel. `main`'s icon rendered the same way at 16 px had 12 colors.
- The container and its volume were removed afterwards.

### Findings

- **`/code-review` (high) on `fae68c8..f4b7f16`:** one nit. In the maskable icon, both bar ends are measured from the left edge, and its unit (24.83 px at 512 px) is not whole, so the bars sit 1 px left of center (74 px of mark on the left, 75 px on the right). Before this change they were symmetric. Not fixed: it is a 1 px difference inside a masked, scaled app icon, and changing it would be a behavior change by Claude. The user chose not to fix it (2026-11-22).
- **Spec sub-agent** (independent, detached worktree; it decoded the generated files with Python's standard library, re-ran G1–G6, and reproduced the red results): no behavior defect. Three notes:
  - **F1, test gap, fixed in Claude's review commit.** `draws the tab icon on the 16 px grid` read only `rect` and `path` geometry, so an SVG with `stroke-linecap="square"` (bars on half pixels), an extra `line` in a third color, or a `transform` on the square still passed. The test now first requires that the SVG has only `svg`, `rect`, and `path`, with only the attributes it models. Proof in a `git archive` export of the branch, editing `public/icon.svg` and running only that test:

    | Mutation | Without the new assertion | With it |
    | --- | --- | --- |
    | E1 `stroke-linecap="square"` on the path | passed | failed |
    | E2 an extra `<line stroke="#888888">` | passed | failed |
    | E3 `transform="translate(10 10)"` on the square | passed | failed |

    On the real icon, `install.test.ts` has 7 passed, and `npm run build` passes.
  - **F2, not fixed.** No test pins the maskable icon's box (`0.21`); tasks.md puts it out of scope.
  - **F3, not fixed.** The comment at `make-icons.py:19` says the maskable mark stays within the 80% safe zone, but its corners are about 41% of the size from the center. design.md lists this as a non-goal; it predates this change.
