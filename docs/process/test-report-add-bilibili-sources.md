# Bilibili uploader implementation test report

## Scope and environment

- Date: 2026-11-23 (UTC). Approved change: `add-bilibili-sources` (#40), U1–U7 recommendations.
- Starting plan commit: `9d6eb81`; main integration: `ec98682`. Implementation followed task groups 1–7 in order, with a commit per group.
- Backend: Python 3.12.13, pytest 9.1.1; commands run from `backend/` with `uv run --offline pytest`.
- Frontend and extension: Node 22.17.1, selected before every npm command with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.
- `npm ci --offline --no-audit --no-fund` succeeded in both packages (124 frontend packages, 120 extension packages). Both emitted the existing `whatwg-encoding@3.1.1` deprecation warning. No manifests, dependency versions, or lockfiles changed.
- Invented RSSHub/video/subtitle fixtures only. Existing socket blocking, mocked DNS, respx routes, fake models, and browser fetch mocks kept validation offline. No Bilibili, RSSHub, model-provider, or other real network requests were made.
- No Docker commands, smoke script, or live check were run. Port 8800, containers, and volumes were untouched. Nothing was pushed, tagged, merged, or published.

## Group-by-group red and green evidence

### 1. Host refusal and exact RSSHub private-origin exception

- New tests in the existing safe-fetch, context-links, and config files.
- Red: `uv run --offline pytest tests/test_safe_fetch.py tests/test_context_links.py tests/test_config.py -k "bilibili or private_origin or rsshub" -q`: **28 failed, 123 deselected**, for the missing host module/guard, field, and argument.
- Green: `uv run --offline pytest tests/test_safe_fetch.py tests/test_context_links.py tests/test_config.py`: **151 passed**.
- Full backend: **1110 passed in 59.37s**.
- H1–H3 and E1–E3 killed separately; restored focused suite: **151 passed**.

### 2. RSSHub uploader reader and inline SRT

- Added the invented `rsshub-uploader.json` fixture and `test_bilibili.py`.
- Red: **1 collection error**, missing `catchup.sources.bilibili`.
- Green: `uv run --offline pytest tests/test_bilibili.py tests/test_feeds.py tests/test_feed_transcripts.py`: **50 passed**.
- Full backend: **1145 passed in 52.92s**.
- R1, R2, P1, P2, and P3 killed separately and restored.

### 3. Uploader preview and confirmation

- Added `test_bilibili_sources_api.py`.
- Red: **11 failed**, with the expected blocked uploader/route URLs and invalid stable confirm URL.
- First green attempt: **1 failed, 81 passed in 12.18s**. Implementation stopped immediately for diagnosis, as requested.
- Ranked hypotheses:
  1. The new test incorrectly expected `+00:00` instead of the API's existing `Z` timestamp spelling.
  2. The new feed parser changed timezone normalization.
  3. Response encoding changed the datetime representation.
- Confirmed cause: hypothesis 1. Claude Code confirmed existing feed and X previews also use Pydantic's `Z` UTC spelling. The plan did not require a different spelling.
- On explicit user authorization, changed only the new expected timestamps to `.isoformat().replace("+00:00", "Z")`. API serialization was not changed.
- Green: `uv run --offline pytest tests/test_bilibili_sources_api.py tests/test_sources_api.py tests/test_x_sources_api.py`: **82 passed in 7.52s**.
- Full backend: **1156 passed in 43.31s**.
- C3 killed at the explicit `AssertionError("Bilibili entries must never call article_text")`; restored new API tests: **11 passed**.
- Followed the task file's mutation placement: C3 in group 3, C1/C2 in group 4.

### 4. Collection, late subtitles, and Creator updates

- Added `test_bilibili_collection.py` and a new creator-updates scenario.
- Red: `uv run --offline pytest tests/test_bilibili_collection.py tests/test_creator_updates.py -k "bilibili or subtitle" -q --tb=short`: **7 failed, 13 deselected**, for the invalid stable source URL and non-expiring wait.
- Green: `uv run --offline pytest tests/test_bilibili_collection.py tests/test_creator_updates.py tests/test_collection.py tests/test_podcast_collection.py tests/test_caption_pass.py tests/test_digest_runner.py`: **160 passed in 14.96s**.
- Full backend: **1163 passed in 111.78s**.
- C1/C2 killed separately; restored `test_bilibili_collection.py` and `test_creator_updates.py`: **20 passed in 5.32s**.

### 5. Frontend and extension popup

- Added five frontend scenarios and one extension popup scenario; no existing tests were changed.
- Red frontend: `npm test -- --run src/components/ui.test.tsx src/pages/Sources.test.tsx src/pages/Home.test.tsx -t "Bilibili"`: **5 failed, 159 skipped**, for missing labels, method/risk text, public addresses, rail copy, and counts.
- Red extension: `npm test -- --run src/test/popup.test.ts -t "labels a bilibili preview"`: **1 failed, 89 skipped**, for the missing label (the displayed address was also internal).
- Green focused: **5 passed, 159 skipped** frontend; **1 passed, 89 skipped** extension.
- Complete frontend: **321 passed, 14 files**, build passed (40 modules).
- Complete extension: **169 passed, 7 files**, build and bundled-output check passed (10 modules).
- New badge/reason, source preview, and saved-row accessibility checks passed; popup axe passed with the existing color-contrast exclusion.
- Popup confirmation still sends the stable internal address while displaying the public space address.
- U1 and X1 killed separately; both targeted scenarios passed after restoration.

### 6. Optional Compose deployment and documentation

- Added three tests in `test_rsshub_docs.py`, using the existing installation-document helpers.
- Red: `uv run --offline pytest tests/test_rsshub_docs.py -q --tb=short`: **3 failed in 0.55s**, for missing override, environment example, and README section. Existing ignore-file assertions passed before the environment-example assertion.
- Green: `uv run --offline pytest tests/test_rsshub_docs.py tests/test_install_docs.py tests/test_readme_context.py -q`: **30 passed in 0.31s**.
- Full backend: **1166 passed in 51.51s**.
- Extension after README changes: **169 passed, 7 files in 4.39s**.
- D1 killed separately; restored documentation tests: **3 passed in 0.18s**.
- The default Compose file and ignore files stayed unchanged. The new override is checked byte-for-byte, including its final newline. Documentation covers both install types, cookie/account and public-instance risks, both RSSHub images, and health-waiting start commands. Documentation snippets were not executed.

## Named mutations

Every mutation was applied alone, its named test failure inspected, then restored exactly by editing. Each restoration was inspected with `git diff`. All **17** mutations were killed; none survived.

| ID | Mutation | Observed failure |
| --- | --- | --- |
| H1 | Match only bare Bilibili domains | Host-refusal subdomain cases: **4 failed, 2 passed, 80 deselected** |
| H2 | Remove Bilibili guard from `_check_address` | Host refusal and redirect refusal: **7 failed, 79 deselected** |
| H3 | Keep Bilibili related links | `test_related_links_skip_bilibili_hosts`: **1 failed, 10 deselected** |
| E1 | Apply private exception on every hop | Same-origin redirect: **1 failed, 1 passed, 84 deselected** |
| E2 | Ignore origin port | `test_private_origin_is_exact[other-port]`: **1 failed** |
| E3 | Skip connection checks for every host with an exception | `test_private_origin_connect_check_is_exact`, rebinding case b: **1 failed** |
| R1 | Remove mobile uploader form | `test_uploader_addresses[mobile]`: **1 failed** |
| R2 | Accept video page as uploader | `test_other_bilibili_addresses_are_refused[video]`: **1 failed** |
| P1 | Convert subtitles using data URL's `text/plain` type | `test_subtitles_from_data_attachment`: **1 failed**, timing lines leaked |
| P2 | Fetch external SRT attachments | `test_web_attachments_are_never_requested`: **1 failed, 1 passed**; the public subtitle route detects the fetch, while the Bilibili route remains blocked |
| P3 | Keep feed-title suffix | Title/parser tests: **2 failed, 3 passed, 30 deselected** |
| C3 | Pass missing-subtitle videos to article fallback | `test_bilibili_entries_never_request_their_video_page`: **1 failed**, explicit article-text assertion |
| C1 | Do not re-resolve pending subtitle waits | `test_subtitles_that_appear_later_are_used`: **1 failed**, old wait/content/summary retained |
| C2 | Never expire subtitle waits | `test_subtitle_wait_ends_in_creator_updates` and `test_whole_run_never_requests_bilibili`: **2 failed** |
| U1 | Display internal feed address in Sources row | `shows a Bilibili uploader by its space address`: **1 failed, 55 skipped** |
| X1 | Display internal feed address in popup | `labels a bilibili preview as Bilibili uploader and shows its space address`: **1 failed, 89 skipped** |
| D1 | Remove README's agreement section reference | `test_readme_explains_bilibili_uploaders`: **1 failed** on missing `section 5.6(3)` |

## Final checks (task 7.1)

All commands exited **0**. npm commands used the Node selection above. Output excerpts omit routine pytest per-file progress.

| Directory | Command | Result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1166 passed in 51.24s**, 1166 collected |
| `frontend/` | `npm test -- --run` | **321 passed**, **14 files**, 8.98s |
| `frontend/` | `npm run build` | TypeScript and Vite passed, **40 modules**, 470ms |
| `extension/` | `npm test -- --run` | **169 passed**, **7 files**, 6.02s |
| `extension/` | `npm run build` | TypeScript, Vite, and `check-build.mjs` passed, **10 modules**, 233ms |
| root | `DO_NOT_TRACK=1 openspec validate add-bilibili-sources --strict` | `Change 'add-bilibili-sources' is valid` |
| root | `git diff 9d6eb81 --check` | No output, exit 0 |

```text
collected 1166 items
============================ 1166 passed in 51.24s =============================

Frontend:
 Test Files  14 passed (14)
      Tests  321 passed (321)
   Duration  8.98s

Extension:
 Test Files  7 passed (7)
      Tests  169 passed (169)
   Duration  6.02s
```

Final frontend build output:

```text
> tsc --noEmit && vite build
vite v8.3.5 building client environment for production...
transforming...
✓ 40 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.82 kB │ gzip:  0.41 kB
dist/assets/index-2FHpjrn6.css   20.50 kB │ gzip:  5.24 kB
dist/assets/index-DUWzTsOo.js   318.91 kB │ gzip: 97.74 kB
✓ built in 470ms
```

Final extension build output:

```text
> tsc --noEmit && vite build && node scripts/check-build.mjs
vite v8.3.5 building client environment for production...
transforming...
✓ 10 modules transformed.
rendering chunks...
computing gzip size...
dist/popup.html                    0.45 kB │ gzip: 0.29 kB
dist/icon-192.png                  0.52 kB
dist/readability-LICENSE.md        0.55 kB
dist/options.html                  0.76 kB │ gzip: 0.42 kB
dist/readability.js               89.98 kB
dist/assets/options-CUZyiacw.css   1.48 kB │ gzip: 0.72 kB
dist/assets/popup-DKe_ziKL.css     2.03 kB │ gzip: 0.86 kB
dist/assets/options-0axhCIRv.js    2.06 kB │ gzip: 0.98 kB
dist/assets/popup-DUKAg8vm.js     14.21 kB │ gzip: 5.29 kB
✓ built in 233ms
```

## Test provenance and review handoff

- Added 84 collected backend cases, five frontend scenarios, and one extension scenario. Existing suites, browser accessibility helpers, fake models, DNS/respx fixtures, and documentation helpers were reused, not replaced. Existing tests were left unchanged.
- Implementation commits for groups 1–6: `6576325`, `84b0915`, `6c1671b`, `a118c7a`, `1d9d4b5`, `49248ce`. Group 7 records checks and process evidence.
- No coverage measurement was requested or run; passing test counts are not a coverage percentage.
- Claude Code runs the independent code/spec review, Docker smoke, and live check with a local RSSHub at review, on fresh review resources and ports other than 8800. These checks remain unperformed by Droid by explicit instruction.
- The AI usage log leaves the session id, turns, and minutes for Claude Code to fill in from the completed run.

## Fix round 1

### Scope and setup

- Group 8 only, based on `8d8464a` and the fresh-eyes corrections in `3aeca4c`, in Claude Code's review worktree.
- Re-derived the duplicate rule from the invariant that a validated uploader's stable identity is already known locally. Preview must report an existing source before any RSSHub request; confirmation must do so before touching the feed cache or RSSHub. The shared post-parse confirmation check remains for other feed types.
- Added the two tests exactly as specified and only the two permitted phrases to the existing README test. No other groups 1–7 tests were changed.
- Python 3.12.13 and pytest 9.1.1; all backend commands used `uv run --offline pytest` from `backend/`. The first run created this worktree's virtual environment from locally cached locked packages; no dependency declarations or lockfiles changed.
- Node 22.17.1 was selected for every npm command. `npm ci --offline --no-audit --no-fund` passed in `frontend/` (124 packages) and `extension/` (120 packages), with the existing `whatwg-encoding@3.1.1` deprecation warning only.

### Tasks 8.1 and 8.2: red and green

The initial command was:

```sh
uv run --offline pytest tests/test_bilibili_sources_api.py::test_duplicate_is_reported_without_asking_rsshub tests/test_bilibili.py::test_fetch_uploader_uses_feed_limit_and_spacing tests/test_rsshub_docs.py::test_readme_explains_bilibili_uploaders -q --tb=short
```

It produced **2 failed, 1 passed in 3.02s**, exactly as planned:

- The duplicate test failed because preview reported `rsshub_failed` instead of `duplicate` after the mocked RSSHub answer changed to 503.
- The README test failed on missing `third-party download`.
- The feed-limit/spacing guard passed before implementation. M2 and M3 below separately demonstrate its sensitivity to both requirements.

After moving duplicate checks ahead of RSSHub/cache access and adding the specified README paragraphs:

- The same three targeted checks: **3 passed in 3.92s**.
- `uv run --offline pytest tests/test_bilibili.py tests/test_bilibili_sources_api.py tests/test_sources_api.py tests/test_x_sources_api.py tests/test_rsshub_docs.py tests/test_install_docs.py tests/test_readme_context.py`: **149 passed in 5.28s**.
- Full `uv run --offline pytest`: **1168 passed in 33.63s**.
- Extension `npm test -- --run`: **169 passed, 7 files, 2.38s**.

All expected initial and post-fix results held. No diagnosis stop or change to the approved plan was needed.

### Task 8.3: named mutations

Saved the complete uncommitted `git diff --no-ext-diff` before the mutations. Applied each mutation alone, ran its named test, inspected the failure, then restored by editing. After every restoration, `cmp` confirmed the current diff matched the saved pre-mutation diff **byte-for-byte**, exit 0. The temporary comparison files were removed afterward.

| Mutation | Named test | Observed result |
| --- | --- | --- |
| M1: preview duplicate check moved back after parsing | `test_duplicate_is_reported_without_asking_rsshub` | **Killed: 1 failed in 1.58s**; preview returned `rsshub_failed`, not `duplicate` |
| M2: remove `max_bytes=settings.max_feed_bytes` | `test_fetch_uploader_uses_feed_limit_and_spacing` | **Killed: 1 failed in 3.14s**; the response exceeded the default 5 MB limit |
| M3: remove `spacer=spacer` | `test_fetch_uploader_uses_feed_limit_and_spacing` | **Killed: 1 failed in 0.47s**; recorded waits were `[]`, not `[ROUTE]` |
| M4: remove the third-party download sentence | `test_readme_explains_bilibili_uploaders` | **Killed: 1 failed in 2.31s**; missing `third-party download` |
| M5: remove the early confirmation duplicate check | `test_duplicate_is_reported_without_asking_rsshub` | **Killed: 1 failed in 1.62s**; confirmation returned 422, not 409 |
| M6: remove the CatchUp-version warning sentence | `test_readme_explains_bilibili_uploaders` | **Killed: 1 failed in 0.04s**; missing the version-warning phrase |

All six mutations were killed and restored. Restored targeted checks: **3 passed in 1.63s**. `sources/bilibili.py` has no lasting change.

### Task 8.4: final checks

All seven commands exited **0**. npm commands used `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` first.

| Directory | Command | Actual output/result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1168 collected, 1168 passed in 43.97s** |
| `frontend/` | `npm test -- --run` | **14 files passed, 321 tests passed**, 9.20s |
| `frontend/` | `npm run build` | `tsc --noEmit && vite build`; **40 modules transformed**, `built in 689ms` |
| `extension/` | `npm test -- --run` | **7 files passed, 169 tests passed**, 5.57s |
| `extension/` | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`; **10 modules transformed**, `built in 330ms` |
| root | `DO_NOT_TRACK=1 openspec validate add-bilibili-sources --strict` | `Change 'add-bilibili-sources' is valid` |
| root | `git diff 9d6eb81 --check` | No output, exit 0 |

Final suite output excerpts:

```text
collected 1168 items
============================ 1168 passed in 43.97s =============================

Frontend:
 Test Files  14 passed (14)
      Tests  321 passed (321)
   Duration  9.20s

Extension:
 Test Files  7 passed (7)
      Tests  169 passed (169)
   Duration  5.57s
```

Both production builds passed TypeScript checking and Vite bundling; the extension's bundled-output check also passed. No frontend or extension source changed in this round. The additional backend cases use existing invented fixtures and offline DNS/respx seams; the existing suites were reused.

No network request, Docker command, live check, or protected-instance operation was performed. Port 8800, containers, and volumes were untouched. No packages were upgraded and no secrets were read, written, printed, or committed. Claude Code runs Docker smoke and the live checks at review. The session line remains for Claude Code to add.

## Review by Claude Code

Reviewed in worktree `review40` on the branch. Droid's runs started at `ec98682` (the plan, merged with `main`; groups 1–7) and at `8d8464a` (fix round 1, with fixes from a fresh-eyes check in `3aeca4c`).

### Checks

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1166 passed on `2e42f2d`; 1168 after fix round 1 |
| Frontend `npm test -- --run`, `npm run build` | 321 passed; build passed |
| Extension `npm test -- --run`, `npm run build` | 169 passed; build passed |
| `DO_NOT_TRACK=1 openspec validate add-bilibili-sources --strict` | valid |
| `git diff --check` | clean |
| `scripts/docker-smoke.sh catchup:fix40-local` (built from `2e42f2d`, then from `44f2183`) | 12 of 12 both times |

### Live check

No real RSSHub was run and nothing was requested from Bilibili. A local stand-in on the host served the repository's invented fixture (`backend/tests/fixtures/rsshub-uploader.json`, with its dates moved to the last few hours) for `/bilibili/user/video/<mid>?format=json`, and logged every request. A scratch container from `catchup:fix40-local` ran on its own volume with `CATCHUP_RSSHUB_URL=http://host.docker.internal:18766`, and a local OpenAI-compatible stub model answered the summaries.

- **Before the fix round** (image from `2e42f2d`, port 8840):
  - Preview of `https://space.bilibili.com/2267573`: kind `bilibili`, `feed_url` `bilibili:uploader:2267573`, title "Sample Uploader", the three videos (the article entry left out). A video page address answered 422 `not_a_bilibili_uploader`. The same uploader again answered "Already following Sample Uploader."
  - After following, one run succeeded: "Video with subtitles" was summarized from its subtitles (stored text "Hello / / world", origin `transcript`), and the two videos without subtitles stayed pending in `subtitle_wait`, with their descriptions kept but not summarized.
  - The stand-in saw exactly two requests: the preview and the run's check (confirm used the cached preview).
  - Sources page: the row showed the "Bilibili uploader" badge and the space address, and the supported-sources list names Bilibili uploaders. The preview showed the method line and the terms notice. The home page showing the latest digest has no source-count rail, as before this change; `Home.test.tsx` checks the count text.
- **After the fix round** (image from `44f2183`, port 8841): after one uploader was followed, the stand-in was switched to answer 503. A preview of `https://m.bilibili.com/space/2267573` answered 422 `duplicate` and a confirm of `bilibili:uploader:2267573` answered 409 `duplicate`, with no RSSHub request; a new uploader answered 422 `rsshub_failed` ("RSSHub could not read this uploader (HTTP 503).").

The containers, volumes, and stubs were removed afterwards.

A live check against a real RSSHub was not run: it would download the third-party image and make requests to Bilibili from this machine. The user chose to skip it (2026-11-24); the stand-in checks cover CatchUp's side.

### Findings

- **`/code-review` (high) on `ec98682..2e42f2d`:** no findings. On fix round 1: one nit, a rewrapped README line about 81 columns wide; fixed in Claude's review commit.
- **Spec sub-agent** (independent, detached worktree; it re-ran all 17 named mutations, and each failed its named test; it found no path by which CatchUp requests a Bilibili host):
  - **Fixed in fix round 1:** a followed uploader was not reported as a duplicate while RSSHub failed; the README did not say that the RSSHub image is a third-party download, nor that an older published image lacks this change; no test covered the uploader request's size limit and spacing.
  - **Decided by the user (2026-11-24), spec delta and design.md only:** the not-configured message applies to uploader addresses, and other Bilibili addresses are not uploaders; RSSHub's rate limiting is reported as rate limiting; the connect-time exception applies to every connection of one fetch, so only DNS rebinding of the operator's own RSSHub host could reach a private address on a redirect, and design D4 now says so; Bilibili images offered by other sources stay out of this change.
  - **Recorded, not fixed:** the connect-time check compares host and port but no test changes the port there (the pre-check's port comparison is tested by E2); the collection path has no test of its own that Bilibili items skip `article_text` (the host rule tested by H2 refuses the request anyway); several spec scenarios are checked at `safe_fetch` or by reading the code, not through the API.
