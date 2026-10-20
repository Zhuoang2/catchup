# Test report: add-item-images

2026-10-19. Tests used invented feed fixtures, mocked DNS/HTTP and fetch, and fake model replies. They made no live image or model requests.

## Red-first results

| Task | Failing check before implementation | Green check |
| --- | --- | --- |
| 1.1–1.2 parser | 5 image parse/discovery tests failed: `FeedEntry.images` missing. | `test_discovery.py`: 76 passed; respx saw only the feed request. |
| 1.3 storage | 5 migration/collection/confirmation tests failed: missing `0005`, old migration head, and missing `Item.image_candidates`. | Full backend suite: 533 passed; upgrade from `0004` and downgrade verified. |
| 2.1 model choice | 4 prompt/summary/split tests failed on missing `images` arguments. | 27 stage/long-summary tests passed. |
| 2.2 reuse | Runner test failed because `summary_images` was null after a failed grouping call. | 71 stage/long-summary/runner tests passed, including retry without a second summary call. |
| 3.1 snapshot | 2 history tests failed: no `images` API key, including the exact older-item dict. | 16 history tests passed, including source deletion. |
| 3.2 API preference | 3 settings tests failed without `show_images`. | Full backend suite: 540 passed. |
| 4.1 reading layout | 3 tests failed: no image block/DOM image and no image CSS. A later refinement failed when all figures errored but left an empty `.item-images` block. | 37 focused tests, then 210 frontend tests and build passed. After the refinement, 6 component tests and the full 216-test frontend suite passed; no empty block remains. `DigestView.test.tsx`'s earlier no-`img` assertion now covers an item without images; its item-children case now asserts the nested `summary`, `item-images`, `also-read` order. `tokens.test.ts` guards flex wrapping, the 320 px bound and absence of new grid rules. |
| 4.2 startup preference | 4 Home/DigestView tests failed: images rendered when off, and no preference request. | 99 focused tests passed. A failed preference read falls back to showing images. |
| 4.3 Settings | 2 tests failed because the toggle did not exist. | Full frontend suite: 216 passed; build passed. Note remains outside the clickable label and is linked by `aria-describedby`; axe passed on new rendered states. |
| 5.1 README | The privacy note was absent. | `rg` found the setting's name, default, no-referrer behavior and source-site contact. |

After the documentation commit, a snapshot regression reproduced stale images when new context invalidated an old summary and the replacement model call failed: the API returned the old image beside `summary_unavailable: true`. The runner snapshot was copying stored images without checking the summary result. It now snapshots images only when that summary succeeded; the focused regression passed (2 tests), followed by the full checks below. Ranked hypotheses were unconditional snapshot copy (confirmed), API fallback (rejected), and cached-summary reuse (rejected).

## Final checks

The frontend build ran before backend coverage so the static-asset branches were included.

| Command | Actual result |
| --- | --- |
| `cd frontend && npm run build` | Passed: TypeScript and Vite, 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **541 passed**, **96%** statement coverage (2,372 statements, 87 missed, 2,285 covered). `sources/feeds.py` 96%, `digest/summarize.py` 95%, `llm/prompts.py` 100%, `digest/runner.py` 99%, `api/digests.py` 100%, `api/settings.py` 94%. |
| `cd frontend && npm test -- --run` | **216 passed**, 13 files. |
| `openspec validate add-item-images --strict` | Passed: change is valid. |
| `docker build .` | Passed: local image built, not pushed. Docker runtime/smoke not checked. |

## Manual checks not performed

- A real run on Simon Willison and The Verge.
- The reading layout at 1440, 900, and 420 px in both themes.
- A live browser/network check of image loading or a real model's image choices.

## Fix round 1 (in progress)

| Task | Red check | Green check |
| --- | --- | --- |
| 6.1 figure margin | `npm test -- --run src/styles/tokens.test.ts`: 1 failed, figure rule had no `margin: 0`. Cause: the rule omitted a reset of the browser's default margin; override and selector mismatch did not explain it. | Same command: 13 passed. |
| 6.2 prompt quoting | `uv run pytest tests/test_digest_stages.py -q -k 'image_prompt_quotes or image_prompts_request or no_context_system_prompt'`: 2 failed (forged extra lines and missing language rule), 1 passed (no-image prompt bytes). | `uv run pytest tests/test_digest_stages.py -q`: 20 passed. Feed alt/caption now collapse whitespace before the 200-character cut, then serialize as JSON strings; both examples use neutral alt text. |
| 6.3 long transcript | New one-call check passed. Named temporary mutations **drop long prompt rules**, **omit its Images block**, and **pass no images to the single call** each failed the new check (1 failed, 9 deselected per run), then were reverted. | `uv run pytest tests/test_long_summaries.py -q`: 10 passed. |
