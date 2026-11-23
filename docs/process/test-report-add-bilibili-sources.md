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
