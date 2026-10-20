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
| 4.1 reading layout | 4 tests failed: the `DigestArticle` image test, two `DigestView` layout tests, and the `tokens.test.ts` CSS guard. The empty-list test passed before implementation by its nature: it checks that an image block is absent. A later all-figures-fail refinement asserted that the empty `.item-images` block disappears; the assertion fails against `4ac527a` and the fix was committed inside the docs commit `d42bde3`. | 37 focused tests, then 210 frontend tests and build passed. After the refinement, 6 component tests and the full 216-test frontend suite passed; no empty block remains. `DigestView.test.tsx`'s earlier no-`img` assertion now covers an item without images; its item-children case now asserts the nested `summary`, `item-images`, `also-read` order. `tokens.test.ts` guards flex wrapping, the 320 px bound and absence of new grid rules. |
| 4.2 startup preference | 4 Home/DigestView preference tests failed: images rendered when off, and no preference request. The two `DigestView` preference tests belong here, not to the 4.1 layout count. | 99 focused tests passed. A failed preference read falls back to showing images. |
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

## Fix round 1

| Task | Red check | Green check |
| --- | --- | --- |
| 6.1 figure margin | `npm test -- --run src/styles/tokens.test.ts`: 1 failed, figure rule had no `margin: 0`. Cause: the rule omitted a reset of the browser's default margin; override and selector mismatch did not explain it. | Same command: 13 passed. |
| 6.2 prompt quoting | `uv run pytest tests/test_digest_stages.py -q -k 'image_prompt_quotes or image_prompts_request or no_context_system_prompt'`: 2 failed (forged extra lines and missing language rule), 1 passed (no-image prompt bytes). | `uv run pytest tests/test_digest_stages.py -q`: 20 passed. Feed alt/caption now collapse whitespace before the 200-character cut, then serialize as JSON strings; both examples use neutral alt text. |
| 6.3 long transcript | New one-call check passed. Named temporary mutations **drop long prompt rules**, **omit its Images block**, and **pass no images to the single call** each failed the new check (1 failed, 9 deselected per run), then were reverted. The review found that this test also passed with the wrong (article) prompt, because it checked shared image rules rather than transcript-specific wording. Task 7.1 added those assertions and killed that mutation. | `uv run pytest tests/test_long_summaries.py -q`: 10 passed in round 1; task 7.1's strengthened suite: 10 passed. |
| 6.4 lazy HTML sources, dropped | `uv run pytest tests/test_discovery.py -q -k html_image_prefers_lazy_source_then_largest_srcset_width`: 4 failed, 1 passed before the attempted collector change. After adding `data-src`/`srcset` support to the collector, the same four cases still failed: feedparser sanitizes both attributes before the collector sees entry HTML. A probe with `feedparser.parse(..., sanitize_html=False)` retained the attributes but also retained a script the default sanitizer removes. Droid stopped rather than change text sanitization or add a second unsanitized parse; unfinished edits were removed. | The user chose to record this as a known limit instead. Commit `1c92dd1` amended D1 and marked 6.4 dropped; no parser behavior change was made. |
| 6.5 exact-URL duplicates | `uv run pytest tests/test_discovery.py -q -k test_image_query_identifies_distinct_images --tb=short`: 1 failed, `?id=2` omitted. After the fix the old cap test failed because it expected `?size=large` to be a duplicate; updated it to count as a separate image and to cap the remaining pictures at six. | `uv run pytest tests/test_discovery.py -q --tb=short`: 78 passed, including fragment deduplication. |
| 6.6 parser mutation guards | Each new check passed first. Eight named temporary mutations failed their respective focused `uv run pytest tests/test_discovery.py -q -k <test> --tb=short` commands (1 failed each): **allow ftp** (`test_ftp_media_image_is_dropped`); **remove /blavatar/** (`test_wordpress_entry_blavatar_is_dropped_even_without_channel_match`); **remove channel-image check** (`test_html_image_matching_channel_image_is_dropped`); **remove audio exclusion** (`test_audio_entry_ignores_html_and_media_images`); **remove media type check** (`test_video_media_content_is_not_an_image`); **remove enclosure type check** (`test_pdf_enclosure_is_not_an_image`); **ignore enclosures** (`test_jpeg_enclosure_keeps_image_and_origin`); **put media first** (`test_html_images_come_before_xml_media_regardless_of_element_order`). Each mutation was reverted before the next. | `uv run pytest tests/test_discovery.py -q --tb=short`: 86 passed; `feeds.py` unchanged by the mutations. |
| 6.7 source alt fallback | New run/API check passed first. Temporary mutation **runner passes no source name** made `test_run_uses_source_title_for_empty_image_alt_fallback` fail (1 failed, 45 deselected): returned `Image from ` instead of `Image from Source 0`. Reverted. | `uv run pytest tests/test_digest_runner.py -q --tb=short`: 46 passed. |
| 6.8 stored-off frontend preference | All three new checks passed first. Temporary mutations failed their respective focused `npm test -- --run src/pages/<file>.test.tsx -t '<name>'` commands (1 failed each): **ignore stored value on Settings load** (`loads stored images off` showed checked), **show saved digest before preference settles** (`DigestView: waits for the stored image preference` showed an image early), and **show latest digest before preference settles** (`Home: waits for the stored image preference` showed an image early). Each was reverted. Accessibility passed on pending and settled states. | `npm test -- --run src/pages/Settings.test.tsx src/pages/DigestView.test.tsx src/pages/Home.test.tsx`: 113 passed. |

### Named mutation table

Every mutation was applied temporarily and reverted after the focused check went red. No mutation was committed.

| Task | Mutation | Red check |
| --- | --- | --- |
| 6.3 | Drop long-transcript image rules | Single-call long-transcript test: 1 failed (missing rules) |
| 6.3 | Omit long-transcript `Images:` block | Same test: 1 failed (missing candidate line) |
| 6.3 | Pass no images to single call | Same test: 1 failed (missing rules and candidates) |
| 6.6 | Allow `ftp` | FTP media-image test: 1 failed (image retained) |
| 6.6 | Remove `/blavatar/` filter | Entry blavatar test: 1 failed (image retained) |
| 6.6 | Remove channel-image check | HTML channel-image test: 1 failed (image retained) |
| 6.6 | Remove audio exclusion | Audio entry test: 1 failed (HTML and media images retained) |
| 6.6 | Remove media image-type check | Video media test: 1 failed (video retained) |
| 6.6 | Remove enclosure image-type check | PDF enclosure test: 1 failed (PDF retained) |
| 6.6 | Ignore enclosures | JPEG enclosure test: 1 failed (image absent) |
| 6.6 | Put media candidates first | HTML-before-media test: 1 failed (reversed order) |
| 6.7 | Runner passes no source name | Run/API fallback-alt test: 1 failed (`Image from ` instead of source title) |
| 6.8 | Ignore stored `show_images` on Settings load | Stored-off save test: 1 failed (toggle checked) |
| 6.8 | Show saved digest before preference settles | DigestView pending-preference test: 1 failed (image rendered early) |
| 6.8 | Show latest digest before preference settles | Home pending-preference test: 1 failed (image rendered early) |

### Fix-round final checks

The README privacy-section placement assertion (`python3 -c` checking the section follows "Install as an app" and precedes "Run with Docker") failed before the 6.9 edit and passed afterwards. The final content assertion also checked the model-provider note, latest Home digest, source-site IP contact, no referrer, default-on setting, and failure-to-read fallback. Frontend build ran first, so backend coverage includes the built static assets.

| Command | Actual result |
| --- | --- |
| `cd frontend && npm run build` | Passed: TypeScript and Vite, 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **555 passed**, **96%** statement coverage (2,375 statements, 85 missed, 2,290 covered). `sources/feeds.py` 97%, `digest/runner.py` 99%, `llm/prompts.py` 100%, `api/digests.py` 100%, `api/settings.py` 94%. |
| `cd frontend && npm test -- --run` | **219 passed**, 13 test files. |
| `openspec validate add-item-images --strict` | Passed: change is valid. |

Docker build/runtime, a live provider or source, and the manual browser/layout checks listed above were not run in this fix round.

### Known limits (D1)

- The `/avatar/` path rule drops non-avatar content under that path and misses avatars at other paths (for example, GitHub's).
- A channel image with a different query string, such as `?v=2`, is not matched.
- An otherwise website-style entry with an audio enclosure has no image candidates.
- Sizes with units, such as `width="1px"`, do not count as 1×1 tracking pixels.
- Images whose URL exists only in `data-src` or `srcset` are missed because feedparser sanitizes those attributes.

## Fix round 2 (tests only)

Each test passed on the unmodified code, failed under its named temporary mutation (one focused failure per task), and passed again after the mutation was reverted. No source mutation was committed. Focused commands used `cd backend && uv run pytest tests/<file>.py -q -k <test_name> --tb=short`.

| Task | Named temporary mutation | Red check after passing baseline | Green check after reversion |
| --- | --- | --- | --- |
| 7.1 | Route long transcripts with images through `summary_messages` | Single-call test: 1 failed, missing "3–6 key points" (9 deselected). | `test_long_summaries.py`: 10 passed. |
| 7.2 | Omit images in `combine_messages`'s long-transcript branch | Split long-transcript test: 1 failed, missing image rules (10 deselected). | `test_long_summaries.py`: 11 passed. |
| 7.3 | Always add `IMAGE_RULES` to the long-transcript prompt | No-image prompt byte comparison against `0614066`: 1 failed (20 deselected). | `test_digest_stages.py`: 21 passed. |
| 7.4 | Set `ensure_ascii=True` in `_image_text` | Chinese alt/caption test: 1 failed, escaped text (21 deselected). | `test_digest_stages.py`: 22 passed. |
| 7.5 | Record `url` instead of the fragment-free `key` in `seen` | Fragment-first duplicate test: 1 failed, second image retained (86 deselected). | `test_discovery.py`: 87 passed. |
| 7.6 | Remove the `key in seen` duplicate check | Cap fixture with repeated `/one.png`: 1 failed, duplicate at index 1 (86 deselected). | `test_discovery.py`: 87 passed. |

The frontend build ran first so backend coverage includes built static assets.

| Command | Actual result |
| --- | --- |
| `cd frontend && npm run build` | Passed: TypeScript and Vite, 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **559 passed**, **96%** statement coverage (2,375 statements, 85 missed, 2,290 covered). `sources/feeds.py` 97%, `digest/summarize.py` 95%, `llm/prompts.py` 100%. |
| `cd frontend && npm test -- --run` | **219 passed**, 13 test files. |
| `openspec validate add-item-images --strict` | Passed: change is valid. |

Docker build/runtime, a live provider or source, and the manual browser/layout checks listed above were not run in this test-only round.
