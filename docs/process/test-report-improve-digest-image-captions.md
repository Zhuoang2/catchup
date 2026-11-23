# Test report: improve-digest-image-captions (#65)

## Implementation by Factory Droid

2026-11-22, GPT-6.1 Sol. Approved plan: `1bc7959`. Used `openspec-apply-change` and `tdd`, in task-group order, with invented offline fixtures. No feed, web page, or image was fetched. No model credentials were used.

### Environment and scope

- Backend: Python 3.12.13, pytest 9.1.1, every pytest invocation through `uv run --offline` from `backend/`. The first invocation created this worktree's environment from 60 locally cached, locked packages.
- Frontend and extension: each command used `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`; `node --version` returned `v22.17.1`.
- `npm ci --offline --no-audit --no-fund` passed in both directories (124 frontend packages, 120 extension packages). Both printed the existing, non-fatal `whatwg-encoding@3.1.1` deprecation warning.
- No package versions, manifests, locks, models, migrations, API shapes, or stored rows were changed. Only approved production/test files, task checkboxes, this report and the AI usage entry changed.
- The plan entry in the AI usage log records Claude Code's pre-run fresh-eyes prototype and library probes. This run used its approved seams and did not fetch the real feeds again.

### Test-first evidence

All expected reds were inspected before production edits. There were no unexpected red/green outcomes, surviving mutations, invalid mutation attempts, or implementation retries.

| Task | Command from the indicated directory | Observed result before implementation |
| --- | --- | --- |
| 1.1, backend | `uv run --offline pytest tests/test_feeds.py -q` | 18 failed, 9 passed: 13 import failures for missing `is_formula_image`, four newly excluded size rows, and the formula filter assertion. Existing 1×1/0×0 exclusions and kept size rows passed. |
| 1.2, backend | `uv run --offline pytest tests/test_discovery.py::test_formula_and_small_images_are_not_candidates tests/test_extension_api.py::test_capture_drops_formula_images -q --tb=short` | 2 failed: feed retained formulas/small images, capture retained the formula. |
| 2.1, backend | `uv run --offline pytest tests/test_feeds.py::test_stored_image_candidates_apply_the_rules_again tests/test_digest_runner.py::test_summary_call_is_not_offered_formula_candidates_stored_earlier tests/test_digest_history.py::test_saved_digest_never_returns_formula_images -q --tb=short` | 3 failed: missing helper, formula offered as I1/chart as I2, formula returned from history. |
| 3.1, backend | `uv run --offline pytest tests/test_digest_stages.py -k image -q --tb=short` | 2 failed, 6 passed, 45 deselected: new rules and changed example failed; all other selected image tests passed. |
| 4.1, frontend | `npx vitest run src/components/DigestArticle.test.tsx src/pages/DigestView.test.tsx src/pages/Home.test.tsx --reporter=dot` | 8 failed, 125 passed in 3 files: four new tests plus the changed component assertion, digest layout assertion, and shown-image preference cases on saved/latest views. |

The obsolete-role search used the required ripgrep equivalent of the plan's grep command, from the repository root: `rg -n "getByRole\('img'|findByRole\('img'" frontend/src`. It printed nothing and exited 1, as expected.

Green checks after implementation:

- Group 1: `uv run --offline pytest tests/test_feeds.py tests/test_discovery.py::test_formula_and_small_images_are_not_candidates tests/test_extension_api.py::test_capture_drops_formula_images -q`: **29 passed** before mutations and after all restores. Full `uv run --offline pytest`: **1108 passed in 34.56s**, including unchanged duplicate/pixel/eight-candidate test.
- Group 2: the three task-2.1 tests: **3 passed**. Full `uv run --offline pytest` after restores: **1111 passed in 101.12s**. History checks both detail and latest, and confirms stored `DigestItem.images` still has both entries.
- Group 3: `uv run --offline pytest tests/test_digest_stages.py tests/test_long_summaries.py -q`: **64 passed**. Full `uv run --offline pytest` after restores: **1112 passed in 58.27s**. Existing no-image prompt byte checks, three-image cap and fallback tests remain unchanged and passing.
- Group 4: `npx vitest run src/components/DigestArticle.test.tsx src/pages/DigestView.test.tsx src/pages/Home.test.tsx`: **133 passed in 3 files**. After restores, `npm test -- --run`: **318 passed in 14 files**; `npm run build`: **passed**, TypeScript plus Vite, 40 modules.

### New and changed tests

These are additions unless marked changed. Named mutation kills below are observed runs, not hypothetical coverage.

| File / test | Behavior verified | Named mutations killed in targeted runs |
| --- | --- | --- |
| `backend/tests/test_feeds.py`: `test_is_formula_image` (13 cases) | Formula renderer addresses, case, proxies, non-formula names and malformed URL | C1–C5 |
| Same: `test_filter_image_urls_drops_small_stated_sizes` (10 cases) | Either stated side under 100, boundary 100, missing sides | S1–S4 |
| Same: `test_filter_image_urls_drops_formula_images` | Direct filter drops formula, preserves chart | Not selected during mutation runs; C1/C6 were exercised through callers |
| Same: `test_stored_image_candidates_apply_the_rules_again` | Refilter old candidates, skip malformed entries, retain chart metadata, accept None | R2 |
| `backend/tests/test_discovery.py`: `test_formula_and_small_images_are_not_candidates` | Invented mathematics feed drops formulas, thin/small HTML and media images; retains diagram and unit-bearing unknown size | C1, C6 |
| `backend/tests/test_extension_api.py`: `test_capture_drops_formula_images` | Capture stores only the photo | C1, C6 |
| `backend/tests/test_digest_runner.py`: `test_summary_call_is_not_offered_formula_candidates_stored_earlier` | Chart renumbered to I1, formula text and I2 absent, chart choice saved and served | R1 |
| `backend/tests/test_digest_history.py`: `test_saved_digest_never_returns_formula_images` | Detail/latest omit saved formula without rewriting snapshot | H1 |
| `backend/tests/test_digest_stages.py`: `test_image_rules_ask_for_self_explaining_images_with_captions` | Both summary variants request fewer standalone images, distinct extra images and meaningful captions | P1–P4 |
| Same, changed: `test_image_prompts_request_summary_language_alt_and_share_neutral_example` | Both examples describe what the image shows and why it matters | P5 |
| `frontend/src/components/DigestArticle.test.tsx`: `shows each image's text once, as its figure's caption` | Empty img alt, adjacent figcaption, digest language, no duplicate image role, axe accessibility | U1–U3 |
| Same: `does not show an image without text` | Empty/whitespace text excluded, no empty image block | U4 |
| Same: `hides a failed image together with its caption` | Failed caption removed, other caption retained | U5 |
| Same: `shows no caption when images are turned off` | Caption appears by default, none when disabled | No named mutation |
| Same, changed: `renders chosen images in order between the summary and Also read, and hides a failed figure` | Existing order, loading/referrer protections, failure cleanup and accessibility, now with captions and empty alt | Not selected during mutation runs |
| `frontend/src/pages/DigestView.test.tsx`, changed: `keeps the images inside the summary cell and before Also read`; `uses the image preference when %s on a saved digest` | Stored reading layout and preference assertions now find captions | Not selected during mutation runs |
| `frontend/src/pages/Home.test.tsx`, changed: `respects image preference on Latest when %s` | Latest view's shown-image preference assertion now finds caption | Not selected during mutation runs |

### Named mutations

Each of the 23 mutations was applied alone. Its test result was inspected before the next mutation. Production code was edited back after each, then `git diff -- <file>` was compared exactly with the pre-mutation diff. All 23 restores matched; no mutation remains.

Backend mutation command form (from `backend/`): `uv run --offline pytest <selectors below> -q --tb=short`.

Frontend mutation command form (from `frontend/`, Node 22.17.1): `DEBUG_PRINT_LIMIT=0 npx vitest run src/components/DigestArticle.test.tsx -t "<title fragment below>"`. The environment variable only abbreviates Testing Library's DOM diagnostics.

| ID | Isolated mutation | Test selectors / title fragment | Actual result |
| --- | --- | --- | --- |
| C1 | Disable `latex.php` rule | `tests/test_feeds.py::test_is_formula_image` plus feed and capture tests above | **Killed: 6 failed, 9 passed** (four latex.php rows, feed, capture) |
| C2 | Disable codecogs host rule | `tests/test_feeds.py::test_is_formula_image` | **Killed: 2 failed, 11 passed** (both codecogs rows) |
| C3 | Disable QuickLaTeX filename rule | Same | **Killed: 1 failed, 12 passed** |
| C4 | Match `latex.php` anywhere in path | Same | **Killed: 2 failed, 11 passed** (chart subpath and `.png` suffix) |
| C5 | Do not lowercase filename | Same | **Killed: 1 failed, 12 passed** (uppercase LATEX.PHP) |
| C6 | Bypass formula check in candidate filter | Feed and capture tests above | **Killed: 2 failed** |
| S1 | Require both dimensions stated | `tests/test_feeds.py::test_filter_image_urls_drops_small_stated_sizes` | **Killed: 2 failed, 8 passed** (99-only and 64-only) |
| S2 | Require both dimensions under 100 | Same | **Killed: 4 failed, 6 passed** (includes 80×600 and 600×40) |
| S3 | Use `<= 100` | Same | **Killed: 1 failed, 9 passed** (100×100) |
| S4 | Treat missing size as small | Same | **Killed: 2 failed, 8 passed** (600-only and no size) |
| R1 | Runner passes unfiltered stored list | `tests/test_digest_runner.py::test_summary_call_is_not_offered_formula_candidates_stored_earlier` | **Killed: 1 failed**, chart was I2 |
| R2 | Remove dict/string-url guard | `tests/test_feeds.py::test_stored_image_candidates_apply_the_rules_again` | **Killed: 1 failed**, TypeError on malformed stored string |
| H1 | Bypass history formula check | `tests/test_digest_history.py::test_saved_digest_never_returns_formula_images` | **Killed: 1 failed**, formula returned |
| P1 | Remove "usually only one" | `tests/test_digest_stages.py::test_image_rules_ask_for_self_explaining_images_with_captions` | **Killed: 1 failed** |
| P2 | Remove standalone reader/caption clause | Same | **Killed: 1 failed** |
| P3 | Remove caption significance clause | Same | **Killed: 1 failed** |
| P4 | Remove "rendered formulas" | Same | **Killed: 1 failed** |
| P5 | Revert both example captions | `tests/test_digest_stages.py::test_image_prompts_request_summary_language_alt_and_share_neutral_example` | **Killed: 1 failed** |
| U1 | Restore `alt={image.alt}` | `shows each image` | **Killed: 1 failed, 12 skipped**, alt not empty |
| U2 | Replace figcaption with empty span | Same | **Killed: 1 failed, 12 skipped**, caption missing |
| U3 | Omit figcaption lang | Same | **Killed: 1 failed, 12 skipped**, language missing |
| U4 | Allow empty image text | `does not show an image without text` | **Killed: 1 failed, 12 skipped**, three figures instead of one |
| U5 | Hide only failed img, retain figure/caption | `hides a failed image together with its caption` | **Killed: 1 failed, 12 skipped**, Growth chart caption retained |

### Final checks (task 5.1)

All exited 0, after all mutations were restored. npm commands below used the Node PATH export above. Backend/JS suites are existing repository suites extended with the tests listed above; the extension tests were unchanged.

| Directory | Command | Output / result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1112 passed in 67.35s (0:01:07)** |
| `frontend/` | `npm test -- --run` | **Test Files 14 passed (14); Tests 318 passed (318)**, duration 18.83s |
| `frontend/` | `npm run build` | **Passed:** `tsc --noEmit && vite build`; Vite 8.3.5, **40 modules**, built in 868ms |
| `extension/` | `npm test -- --run` | **Test Files 7 passed (7); Tests 168 passed (168)**, duration 12.45s |
| `extension/` | `npm run build` | **Passed:** `tsc --noEmit && vite build && node scripts/check-build.mjs`; Vite 8.3.5, **10 modules**, built in 928ms |
| Root | `DO_NOT_TRACK=1 openspec validate improve-digest-image-captions --strict` | **`Change 'improve-digest-image-captions' is valid`** |
| Root | `git diff --check` | **Passed, no output** |

### Not performed in this run

- **Docker smoke/build and all Docker commands:** not performed, explicitly reserved for Claude Code's review. No container, volume, or port 8800 was touched.
- **Design D5 step 1, same-bytes real-feed comparison:** not performed; Claude Code reads the two public feeds at review. This run used invented fixtures only.
- **Design D5 step 2, browser/live check:** not performed; Claude Code uses a stub model, fresh scratch volume, a port other than 8800, widths 1280/375, accessibility tree, failing image and images-off checks.
- **Design D5 step 3, real-model image choices:** the user's check after merge and their requested rebuild, using their own model. Offline prompt assertions do not prove real-model selection quality.

Implementation commits: group 1 `55834c4`, group 2 `babe238`, group 3 `c5807bb`, group 4 `6abefd2`. Group 5 commits this evidence and the final task checkbox separately. No push, merge, tag, PR, or archive was performed.

## Fix round 1

2026-11-22, Factory Droid, GPT-6.1 Sol. Implemented only task group 6 from `7757205`, with wording fixes in `80494ac`, in Claude Code's review worktree. Groups 1–5 and their evidence are preserved. Used `openspec-apply-change`, `tdd` and `diagnosing-bugs`.

### Reproduction and diagnosis (6.1)

Added exactly the two dotted-host rows to `test_is_formula_image`, the `test_small_media_thumbnails_are_not_candidates` guard, and `does not fail on a saved image without alt text`. No other existing test changed.

| Directory | Command before production edits | Actual result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest tests/test_feeds.py::test_is_formula_image tests/test_discovery.py::test_small_media_thumbnails_are_not_candidates -q --tb=short` | **2 failed, 14 passed in 1.53s**. Only the new lowercase/uppercase dotted codecogs rows failed (`False` instead of `True`). The thumbnail guard passed on the existing code. |
| `frontend/` | `DEBUG_PRINT_LIMIT=0 npx vitest run src/components/DigestArticle.test.tsx -t "does not fail on a saved image without alt text"` | **1 failed, 13 skipped**. `TypeError: Cannot read properties of undefined (reading 'trim')` at the image filter. |

Ranked hypotheses, stated before the fixes:

1. The literal hostname comparison retains the DNS trailing dot. Stripping it should fix both new formula rows while preserving the existing address table.
2. `ItemImages` trusts a compile-time string type for unchecked saved JSON. Checking the runtime type should skip the missing/null text and render only the valid chart.
3. An upstream parsing/rendering defect is less likely; if present, those two local fixes alone would not make the exact regressions pass.

The supplied fixtures already isolate the reported failures at the approved seams, so no additional instrumentation or throwaway probe was needed. The green regressions and M1/M2 confirmed hypotheses 1 and 2; hypothesis 3 was not supported. The invariant is that formula-host comparison ignores the trailing dot and that only nonempty string captions are eligible to render.

### Fixes and green checks (6.2)

Only two production lines changed: `is_formula_image` strips trailing dots after lowercasing the hostname; `ItemImages` checks `typeof image.alt === 'string'` before trimming. No other component logic, parsing rules, stored data, or API shape changed. Thumbnail dimensions already worked and were not changed.

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest tests/test_feeds.py::test_is_formula_image tests/test_discovery.py::test_small_media_thumbnails_are_not_candidates -q --tb=short` | **16 passed in 1.68s** |
| `frontend/` | `npx vitest run src/components/DigestArticle.test.tsx -t "does not fail on a saved image without alt text"` | **1 passed, 13 skipped** |
| `backend/` | `uv run --offline pytest tests/test_feeds.py tests/test_discovery.py -q` | **121 passed in 2.09s** |
| `frontend/` | `npx vitest run src/components/DigestArticle.test.tsx` | **14 passed in 1 file** |

The saved-image fixture includes missing `alt`, `alt: null`, and `alt: 'Chart'`; the green test confirms exactly one figure, the chart URL, and its visible caption.

### Named mutations (6.3)

Each mutation ran alone and its result was inspected before the next. Before each mutation, the complete uncommitted `git diff` was saved in memory. Each mutation was restored by editing the file back, and the complete subsequent `git diff` matched its saved baseline exactly. All three restore comparisons passed; no mutation remains.

| ID | Mutation and command | Actual result |
| --- | --- | --- |
| M1 | Remove `.rstrip(".")`; in `backend/`: `uv run --offline pytest tests/test_feeds.py::test_is_formula_image -q --tb=short` | **Killed: 2 failed, 13 passed in 0.05s**. Only the two new dotted-host rows failed. |
| M2 | Remove the runtime string check; in `frontend/`: `DEBUG_PRINT_LIMIT=0 npx vitest run src/components/DigestArticle.test.tsx -t "does not fail on a saved image without alt text"` | **Killed: 1 failed, 13 skipped**. The same `undefined.trim()` TypeError returned. |
| M3 | Set only `media_thumbnail` width/height to `None`; in `backend/`: `uv run --offline pytest tests/test_discovery.py::test_small_media_thumbnails_are_not_candidates -q --tb=short` | **Killed: 1 failed in 1.50s**. The small thumbnail was retained before the large one. |

M1 is killed by the added formula rows, M2 by the new saved-image regression, and M3 proves the already-green thumbnail guard can fail on its spec rule. No survivors, invalid attempts, unexpected red/green outcomes, or implementation retries occurred.

### Final checks (6.4, repeating task 5.1)

All commands below exited 0 after all mutation restores. Every backend pytest run used `uv run --offline` in `backend/`. Each npm/npx invocation used `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` in the corresponding directory; `node --version` returned `v22.17.1`.

`npm ci --offline --no-audit --no-fund` succeeded in both directories (124 frontend packages, 120 extension packages), with the existing non-fatal `whatwg-encoding@3.1.1` deprecation warning. No dependency manifests, lockfiles, or package versions changed.

| Directory | Command | Actual output / result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1115 passed in 33.59s** |
| `frontend/` | `npm test -- --run` | **Test Files 14 passed (14); Tests 319 passed (319)**, duration 8.01s |
| `frontend/` | `npm run build` | **Passed:** `tsc --noEmit && vite build`; Vite 8.3.5, **40 modules**, built in 583ms |
| `extension/` | `npm test -- --run` | **Test Files 7 passed (7); Tests 168 passed (168)**, duration 4.26s |
| `extension/` | `npm run build` | **Passed:** `tsc --noEmit && vite build && node scripts/check-build.mjs`; Vite 8.3.5, **10 modules**, built in 442ms |
| Root | `DO_NOT_TRACK=1 openspec validate improve-digest-image-captions --strict` | **`Change 'improve-digest-image-captions' is valid`** |
| Root | `git diff --check` | **Passed, no output** |

These are existing suites with this round's three added backend cases and one frontend regression; extension tests are unchanged. The full suites recheck the original regressions after the mutation restores.

No real feed, page, image, or model was fetched. No Docker command, smoke/build, live/browser check, port 8800, container/volume action, push, merge, tag, PR, or archive was performed. Docker and live checks remain for Claude Code's review; D5's real-model choice check remains the user's post-merge check. No temporary helper or debug instrumentation was created. This round's AI usage entry omits the session line for Claude Code to add at review.
