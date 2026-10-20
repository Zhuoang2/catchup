# Test report: add-linked-pages-and-author-replies

2026-10-19. All automated fixtures use invented feeds/pages, mocked network and DNS, and fake model responses. No live feed or model was called.

## Red-first checks

| Group | Initial failing check, before implementation | Green verification |
| --- | --- | --- |
| 1, parsing and persistence | Three parser tests failed with missing `FeedEntry` fields; four DB tests failed before migration `0004`; both collection/confirmation tests failed with `entry_links=None`. | `test_discovery.py`: 71 passed. Full backend suite after migration: 449 passed. Both storage tests passed. |
| 2, link rules and robots | `test_context_links.py` and `test_context_robots.py` failed to import the not-yet-created modules. | 8 tests passed. The first robots green run revealed an unused `respx` route in the zero-budget test; its fixture now permits that deliberately unused route. |
| 3, author replies | `test_context_comments.py` failed to import the not-yet-created module. | 5 tests passed. An initial name-match attempt selected the parent comment because it saw a nested `.fn`; restricting matches to the nearest comment fixed it. |
| 4, settings and run context | Seven config tests failed (missing fields or accepted invalid limits); gather tests failed on missing routes, `TypeError`, or `KeyError`. The 16,000-character test passed before implementation and was not red. A subsequent zero-budget regression failed because a robots request exhausted the budget and marked the item `none`. | 40 config tests, 7 gather tests, 2 focused runner tests, and 480 backend tests passed. Fixed the zero-budget status to leave the item eligible for the next run. A comment fixture initially had invalid nested `<li>` markup and was corrected before green. |
| 5, summaries and used flags | Two contextual-summary tests failed on unsupported context arguments; used-ref recording failed (`L1` was still false). | 22 focused summary/runner tests passed. |
| 6, snapshot and UI | Both history tests failed without `also_read`; two frontend citation tests failed before rendering. The collecting progress test failed before the new label. | 15 history tests; 32 focused citation/layout tests; 205 frontend tests and build passed. The first full frontend check found a test asserting `aria-valuenow` on a native `<progress>` element; the fixture assertion was corrected to its `value`/`max` attributes. The CSS structure guard was extended for `.item-body`. |
| 7, docs | The README defaults check failed before documentation. | The README check passed. |

## Final checks

The frontend was built **before** running backend coverage, so static-asset branches were measured with `frontend/dist` present.

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, TypeScript and Vite build. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **485 passed**, **96%** statement coverage (2,218 statements, 93 missed, 2,125 covered). New modules: comments 80%, gather 88%, links 93%, robots 100%; feeds 97%, runner 99%, summarize 95%. |
| `cd frontend && npm test -- --run` | **205 passed**, 13 test files. |
| `openspec validate add-linked-pages-and-author-replies --strict` | Passed: change is valid. |
| `docker build -t catchup:item-context-local .` | Passed. Local image only; not pushed. |

## Manual checks not performed

- A real run on the Simon Willison and Terry Tao feeds.
- A real-model token comparison with and without context.
- A live browser visual check of the reading layout and a runtime Docker smoke check. The Docker image was built, not started.

## Fix round 1

Offline fixtures, fake model replies, and mocked DNS/network were used throughout. Tasks 8.1–8.7 were each verified and committed separately. No live source or model was called.

### Red-first findings

| Task | Observed failing check before fix | Confirmed cause and green result |
| --- | --- | --- |
| 8.1 | `/archives/10000` and `/search-engines-explained` were discarded; excluded hosts remained; a `/login/` redirect stored a row. | Prefix-based taxonomy checks, incomplete host rules and no final-URL check. `test_context_links.py` and `test_context_gather.py` passed after filtering fixes. |
| 8.2 | Comment/redirect exhaustion marked items `none`; source deletion failed the run; a second session saw `context_done=0` at the next fetch. | Exhaustion was mistaken for an ordinary failure, stale items were dereferenced, and progress was not committed until the item transaction. Five focused cases, including rollback of a first linked row, passed. |
| 8.3 | The first sibling fixture had a reply link and passed; removing that link reproduced missing parent text. A self-link prefixed the author's own text, and double-spaced author names did not match. | Parent lookup missed preceding sibling comments, self-links were accepted, and name matching did not collapse spaces. Eleven comment tests passed. |
| 8.4 | A cached summary with a newly extracted link skipped the summary model response and the run failed; an initial short-page fixture extracted nothing and was expanded before this reproduction. | Newly stored context did not invalidate the language-matched cached summary. The contextual model call and saved Also read link now pass. |
| 8.5 | The context prompt omitted the data-only rule and limited the no-substance condition to the item. | Conditional rules added; the prompt with no context matches the stored `main` wording byte for byte. Fifteen focused stage tests passed. |
| 8.6 | Already-correct behavior passed before each mutation; checks listed below failed under their corresponding temporary mutations. | All production-code mutations were reverted; only tests were changed in the 8.6 commit. |
| 8.7 | The CJK assertions were inside the context-combine test. | Moved them to the separator/sentence test; both tests passed. |

### Mutation checks

All rows below mean **green before mutation, red with named mutation, green after revert**. Intentional red runs used focused pytest/Vitest commands; these are not unresolved suite failures.

| Task / temporary mutation | Red observation |
| --- | --- |
| 8.1 remove HTTP(S) scheme check | FTP link unexpectedly kept. |
| 8.3 reply limit 10 → 11; 10 → 20 | Each added an eleventh short reply. |
| 8.3 character limit 4,000 → 3,000 | Joined result was 3,000, not 4,000 characters. |
| 8.3 feed input limit 10 → 11 | Eleventh feed reply appeared with the independent output cap isolated. |
| 8.5 unconditional context rules; unconditional `used` example | Each changed the byte-for-byte no-context prompt. |
| 8.6 ignore `links_per_item=2` | `context_total` became 3 and the third route was requested. |
| 8.6 ignore `author_replies=False` | The first-run post route was requested (a reset-and-retry test alone did not expose this). |
| 8.6 ignore robots refusal | The refused route was requested once instead of zero times. |
| 8.6 remove comment-feed fallback | The explicitly mocked feed route had zero calls instead of one. |
| 8.6 omit fallback `context_total` increment | Progress was `(total=1, done=2)` instead of `(2, 2)`. |
| 8.6 omit planned comment fetch from `context_total` | Progress was `(0, 1)` instead of `(1, 1)`. |
| 8.6 replace A1 title | Title was `Replies` instead of `Author replies (1)`. |
| 8.6 remove anchor-title fallback | Untitled page stored an empty title. |
| 8.6 skip all podcast items | Text-post route was not requested. |
| 8.6 drop `comments_url` / `comment_feed_url` in `check_source` | Each pointer failed its stored-value assertion separately. |
| 8.6 drop `comments_url` / `comment_feed_url` on confirmation | Each pointer failed its stored-value assertion separately. |
| 8.6 reverse snapshot refs | Also read order changed from `L1, L2` to `L2, L1`. |
| 8.6 pass a new `HostSpacer` to context gathering | Collection-to-context timestamps shifted from `[11, 12]` to `[10, 11]`; the original intra-pass test alone did not detect this. |
| 8.6 remove robots.txt 512 KiB limit | `max_bytes` was missing from the captured safe-fetch call. |
| 8.6 render empty `also_read` | An empty Also read line appeared. |

### Full checks

The frontend build ran before backend coverage so static-asset branches were measured. All required commands passed:

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, TypeScript and Vite build. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **512 passed**, **96%** statement coverage (2,262 statements, 87 missed, 2,175 covered). Comments 88%, gather 93%, links 94%, robots 100%. |
| `cd frontend && npm test -- --run` | **206 passed**, 13 files. |
| `openspec validate add-linked-pages-and-author-replies --strict` | Passed. |

No fix-round Docker build/smoke or live feed/model/browser run was requested or performed. Known remaining limits: very large comment pages parse slowly; GitHub titles include `·`; redirect targets are not checked against robots.txt; context is not trimmed to fit small model windows.

## Fix round 2

Tasks 9.1–9.4 were verified and committed separately. The round-1 exhaustion rollback was a plan error: in a successful run, the item was summarized without the rolled-back context and delivered, so it could not be gathered on a later run. Round 2 keeps context already extracted when the budget cuts off an item. Only items the pass never reaches retain null status; an attempted item with no rows becomes `none`. Cache invalidation still happens only when a row was stored.

### Red-first results

| Task | Observed red result | Green result |
| --- | --- | --- |
| 9.1 | A first linked row disappeared on link-loop exhaustion. A second item's summary omitted `Context L1` and its saved digest lacked Also read; comment-page and comment-feed cutoffs also left stored links absent. Three old rollback assertions were replaced and failed on the expected `none` status. | Partial rows survive link, comment-page, and feed-fallback cutoffs. A successful two-item digest uses the second item's saved link. Robots-only and redirect-only exhausted items have `none`. `test_context_gather.py` plus `test_digest_runner.py`: 67 passed. |
| 9.2 | A top-level author's comment incorrectly prefixed an unrelated reader's text because its nested reply linked to that reader. | Only anchors belonging to the author comment itself are searched; 12 comment tests passed. |
| 9.3 | Two distinct links that redirected to the same final page stored `L1` and `L2` for one URL. | Both fetches still count; one context row is stored. 25 gathering tests passed. |
| 9.4 | Each named mutation below failed its focused check; restored code passed all 23 comments, links and deleted-item checks. | Only the intended test files changed in task 9.4. |

### Named mutation checks

Each check passed first, failed with the temporary mutation, and passed after it was reverted:

| Mutation | Red observation |
| --- | --- |
| Clear cached summary even when no row was stored (9.1) | The cached-only run failed after an unexpected summary call consumed the grouping response. |
| Remove step-3 anchor lookup | An author's explicit `#comment-9` reply lost its reader prefix. |
| Accept only `ul.children` | An `ol.children` reply lost its reader prefix. |
| Drop the `children` class check | A comment in an unrelated `ul.other` gained a false reader prefix. |
| Examine only the immediately preceding sibling | A thread separator blocked discovery of the reader comment. |
| Compare author names case-sensitively | A mixed-case `.fn` no longer matched the entry author. |
| Do not strip `m.` from YouTube hosts | `m.youtube.com/watch` was kept instead of excluded. |
| Remove the first deleted-item guard | A deleted comment item failed the run on `item.link`; its mocked post route remained unrequested. |

### Full checks

The frontend was built first so static-asset paths were present for coverage:

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, TypeScript and Vite build. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **525 passed**, **96%** statement coverage (2,263 statements, 82 missed, 2,181 covered). Comments 93%, gather 95%, links 94%, robots 100%. |
| `cd frontend && npm test -- --run` | **206 passed**, 13 files. |
| `openspec validate add-linked-pages-and-author-replies --strict` | Passed. |

All tests used invented fixtures, mock DNS/network and fake model responses. No live feed/model run, Docker build/smoke, or browser visual check was performed in this round. The remaining limits listed under fix round 1 are unchanged.
